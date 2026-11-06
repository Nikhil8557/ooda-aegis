"""Everything that touches real infrastructure: Docker, Nginx, Redis."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import io
import time
from pathlib import Path

import docker
import httpx
import redis

PROXY_CONF = Path(os.getenv("PROXY_CONF_DIR", "/shared/proxy"))
APP_SOURCE = Path(os.getenv("APP_SOURCE_DIR", "/app_source"))
WORK = Path(os.getenv("WORK_DIR", "/work"))
NETWORK = os.getenv("AEGIS_NETWORK", "aegis_net")
PROXY_CONTAINER = "aegis_proxy"
BLUE = "aegis_app_blue"
BASE_IMAGE = os.getenv("APP_IMAGE", "aegis-app:v1.0.0")
REDIS_HOST = os.getenv("REDIS_HOST", "redis_bus")
MANAGED_LABEL = "aegis.managed"

docker_client = docker.from_env()
bus = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

EMPTY_RULES = "# No virtual patch active.\nmap $request_uri $aegis_drop {\n    default 0;\n}\nmap $request_uri $aegis_rule {\n    default \"\";\n}\n"


def rules_conf(rule_id: str, regex: str) -> str:
    return (f"# Virtual patch {rule_id}, written by the OODA-Aegis edge tier and validated before reload.\n"
            "map $request_uri $aegis_drop {\n    default 0;\n"
            f"    \"~*{regex}\" 1;\n}}\n"
            "map $request_uri $aegis_rule {\n    default \"\";\n"
            f"    \"~*{regex}\" \"{rule_id}\";\n}}\n")


def upstream_conf(weights: dict[str, int]) -> str:
    lines = ["# Active backends and their traffic weights (written by OODA-Aegis)."]
    for name, weight in weights.items():
        if weight > 0:
            lines.append(f"server {name}:8000 weight={weight} max_fails=0;")
    return "\n".join(lines) + "\n"


class NginxError(RuntimeError):
    pass


def _proxy():
    return docker_client.containers.get(PROXY_CONTAINER)


def nginx_apply(filename: str, content: str) -> float:
    """Write one conf file, test the whole config, reload. Rolls back on failure.
    Returns the time taken in milliseconds."""
    started = time.perf_counter()
    path = PROXY_CONF / filename
    previous = path.read_text() if path.exists() else ""
    path.write_text(content)
    test = _proxy().exec_run("nginx -t")
    if test.exit_code != 0:
        path.write_text(previous)
        raise NginxError(test.output.decode(errors="replace")[-500:])
    reload = _proxy().exec_run("nginx -s reload")
    if reload.exit_code != 0:
        path.write_text(previous)
        _proxy().exec_run("nginx -s reload")
        raise NginxError(reload.output.decode(errors="replace")[-500:])
    elapsed = (time.perf_counter() - started) * 1000
    wait_reloaded()
    return elapsed


def wait_reloaded(timeout_s: float = 3.0) -> None:
    """A graceful reload starts new workers asynchronously; until the old ones
    retire, a new connection can still be served with the old config. Wait until
    only workers started after the reload remain."""
    deadline = time.time() + timeout_s
    time.sleep(0.15)
    while time.time() < deadline:
        out = _proxy().exec_run("sh -c \"ps -o args | grep -c '[n]ginx: worker process is shutting down' || true\"")
        if out.output.decode().strip() in ("0", ""):
            break
        time.sleep(0.1)
    time.sleep(0.25)


def write_conf(filename: str, content: str) -> None:
    (PROXY_CONF / filename).write_text(content)


def nginx_reload_checked() -> None:
    test = _proxy().exec_run("nginx -t")
    if test.exit_code != 0:
        raise NginxError(test.output.decode(errors="replace")[-500:])
    _proxy().exec_run("nginx -s reload")
    wait_reloaded()


def wait_for_proxy(timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if _proxy().status == "running":
                return
        except Exception:
            pass
        time.sleep(1)


# ------------------------------------------------------------------ releases


def release_dir(version: str) -> Path:
    return WORK / "releases" / version


def init_base_release() -> Path:
    """Copy the service source into the work volume as release v1.0.0."""
    base = release_dir("v1.0.0")
    if base.exists():
        shutil.rmtree(base)
    shutil.copytree(APP_SOURCE, base, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", "data"))
    (base / "data").mkdir(exist_ok=True)
    subprocess.run([sys.executable, str(base / "seed_db.py"), str(base / "data" / "customers.db")], check=True,
                   capture_output=True)
    if (base / "fake_secrets.env").exists():
        shutil.copy(base / "fake_secrets.env", base / ".env")
    return base


# ------------------------------------------------------------------ sandbox


def docker_runner(image: str):
    """pytest inside a throwaway container: no network, capped memory, wall-clock
    limit. The candidate code is copied to /app, exactly where it runs in production."""

    def run(folder: Path, args: list[str], timeout_s: int) -> tuple[int, str]:
        pytest_cmd = " ".join(["python", "-m", "pytest", *args])
        script = (f"rm -rf /app/* /app/.env && cp -a {folder}/. /app/ && cd /app && {pytest_cmd}; code=$?; "
                  f"for f in report.xml aegis_golden.json; do [ -f /app/$f ] && cp /app/$f {folder}/; done; exit $code")
        container = docker_client.containers.run(
            image, ["sh", "-c", script], detach=True, network_disabled=True, mem_limit="512m",
            environment={"PYTHONPATH": "/app", "REDIS_HOST": "127.0.0.1", "DOCS_DIR": "/app/public_docs",
                         "CUSTOMER_DB": "/app/data/customers.db"},
            volumes={"aegis_work": {"bind": str(WORK), "mode": "rw"}},
            labels={MANAGED_LABEL: "sandbox"},
        )
        try:
            result = container.wait(timeout=timeout_s)
            code = result.get("StatusCode", 1)
        except Exception:
            container.kill()
            code = 124
        output = container.logs().decode(errors="replace")
        container.remove(force=True)
        return code, output

    return run


# ------------------------------------------------------------------ containers


def build_image(version: str, folder: Path) -> str:
    tag = f"aegis-app:{version}"
    docker_client.images.build(path=str(folder), tag=tag, rm=True, labels={MANAGED_LABEL: "release"})
    return tag


def container_name(version: str) -> str:
    return "aegis_app_" + version.replace(".", "_").replace("-", "_")


def start_release(version: str, image: str, label: str) -> str:
    name = container_name(version)
    remove_container(name)
    docker_client.containers.run(
        image, detach=True, name=name, network=NETWORK,
        environment={"CONTAINER_VERSION": label, "CONTAINER_NAME": name, "REDIS_HOST": REDIS_HOST},
        labels={MANAGED_LABEL: "release"},
    )
    return name


def wait_healthy(name: str, timeout_s: int = 40) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if httpx.get(f"http://{name}:8000/health", timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def remove_container(name: str) -> None:
    try:
        docker_client.containers.get(name).remove(force=True)
    except docker.errors.NotFound:
        pass


def remove_managed(keep: set[str] | None = None) -> None:
    for c in docker_client.containers.list(all=True, filters={"label": MANAGED_LABEL}):
        if keep and c.name in keep:
            continue
        c.remove(force=True)


def pause(name: str, seconds: float) -> None:
    c = docker_client.containers.get(name)
    c.pause()
    time.sleep(seconds)
    c.unpause()


def container_stats(name: str) -> dict:
    try:
        s = docker_client.containers.get(name).stats(stream=False)
        cpu = s["cpu_stats"]["cpu_usage"]["total_usage"] - s["precpu_stats"]["cpu_usage"]["total_usage"]
        system = s["cpu_stats"].get("system_cpu_usage", 0) - s["precpu_stats"].get("system_cpu_usage", 0)
        cores = s["cpu_stats"].get("online_cpus", 1)
        return {"cpu": round(cpu / system * cores * 100, 1) if system > 0 else 0.0,
                "memory_mb": round(s["memory_stats"].get("usage", 0) / 1048576, 1)}
    except Exception:
        return {"cpu": 0.0, "memory_mb": 0.0}


# ------------------------------------------------------------------ fleet vaccine


def broadcast_vaccine(vaccine: dict, expect: int = 3, wait_s: float = 3.0) -> list[dict]:
    """Publish a validated rule to peer edge nodes and collect their acks."""
    sub = bus.pubsub(ignore_subscribe_messages=True)
    sub.subscribe("aegis:vaccine:ack")
    time.sleep(0.05)
    vaccine = {**vaccine, "sent_at": time.time()}
    bus.publish("aegis:vaccine", json.dumps(vaccine))
    acks: list[dict] = []
    deadline = time.time() + wait_s
    while time.time() < deadline and len(acks) < expect:
        msg = sub.get_message(timeout=0.2)
        if msg and msg.get("data"):
            ack = json.loads(msg["data"])
            if ack.get("vaccine_id") == vaccine["vaccine_id"]:
                acks.append(ack)
    sub.close()
    return acks
