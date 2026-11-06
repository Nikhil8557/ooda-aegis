"""Verification that does not trust the model.

Nothing a model writes reaches production until it passes these checks:

* A virtual patch (regex) must compile, match the observed attack, and match
  none of the recorded legitimate requests.
* A code repair is a whole patched file, which must compile. The agent builds
  the gate itself: the exploit seen in production must still work on the old
  code and be handled safely on the new code, together with every red-team
  variant, the service's own tests, and every recorded legitimate request,
  which must get exactly the same answer as before (ignoring timing fields).
  The model's own reproduction test runs too, but it is advisory only.

This module has no Docker dependency, so the Kaggle Glimmer benchmark runs the
same checks with a plain subprocess runner.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- virtual patch


def validate_regex(regex: str, attack_uris: list[str], benign_uris: list[str]) -> tuple[bool, str]:
    if not regex or len(regex) > 300:
        return False, "regex is empty or longer than 300 characters"
    if any(ch in regex for ch in '"\n\r;') or regex.endswith("\\"):
        return False, "regex contains characters that are unsafe inside an nginx map (quote, semicolon, newline)"
    try:
        compiled = re.compile(regex, re.IGNORECASE)
    except re.error as exc:
        return False, f"regex does not compile: {exc}"
    missed = [u for u in attack_uris if not compiled.search(u)]
    if missed:
        return False, f"regex does not match the attack URI {missed[0]}"
    blocked = [u for u in benign_uris if compiled.search(u)]
    if blocked:
        return False, f"regex would block legitimate traffic: {blocked[0]}"
    return True, "ok"


_ENCODED = {".": "%2e", "/": "%2f", "\\": "%5c", "'": "%27", '"': "%22", " ": "(?:%20|\\+)",
            "=": "%3d", "<": "%3c", ">": "%3e", ";": "%3b", "-": "%2d", "(": "%28", ")": "%29",
            "|": "%7c", "&": "%26", "#": "%23", "*": "%2a", ":": "%3a", "@": "%40"}


def _char(ch: str) -> str:
    if ch in _ENCODED:
        enc = _ENCODED[ch]
        literal = re.escape(ch) if ch != " " else "\\s"
        return f"(?:{literal}|{enc})"
    return re.escape(ch)


def compile_rule(rule: dict) -> tuple[str | None, str]:
    """Turn the edge model's small rule into a PCRE regex for nginx. The model
    chooses what to block; this code decides how, so URL-encoded variants are
    covered and a weak model cannot produce a broken or catastrophic regex."""
    kind = rule.get("rule_type")
    param = re.sub(r"[^A-Za-z0-9_]", "", str(rule.get("param") or ""))
    if not param:
        return None, "rule names no query parameter"
    prefix = f"[?&]{param}=[^&]*"
    if kind == "contains":
        subs = [s for s in (rule.get("substrings") or []) if isinstance(s, str) and len(s.strip()) >= 2][:6]
        if not subs:
            return None, "contains rule has no substring of 2+ characters"
        body = "|".join("".join(_char(c) for c in sub.strip() if c) for sub in subs)
        return f"{prefix}(?:{body})", "ok"
    if kind == "max_length":
        limit = int(rule.get("max_length") or 0)
        if not 4 <= limit <= 4000:
            return None, "max_length must be between 4 and 4000"
        return f"[?&]{param}=[^&]{{{limit + 1},}}", "ok"
    if kind == "repeated_run":
        run = int(rule.get("min_run") or 0)
        if not 4 <= run <= 200:
            return None, "min_run must be between 4 and 200"
        return f"{prefix}([A-Za-z0-9])\\1{{{run - 1},}}", "ok"
    return None, f"unknown rule_type {kind!r}"


def describe_rule(rule: dict) -> str:
    kind = rule.get("rule_type")
    if kind == "contains":
        return f"{rule.get('param')} contains any of {rule.get('substrings')}"
    if kind == "max_length":
        return f"{rule.get('param')} longer than {rule.get('max_length')} chars"
    return f"{rule.get('param')} has a run of {rule.get('min_run')}+ identical chars"


def regex_coverage(regex: str, uris: list[str]) -> list[bool]:
    try:
        compiled = re.compile(regex, re.IGNORECASE)
    except re.error:
        return [False] * len(uris)
    return [bool(compiled.search(u)) for u in uris]


def build_uri(path: str, params: dict[str, str]) -> str:
    return path + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote, safe="")


def deterministic_mutations(value: str) -> list[dict[str, str]]:
    """Cheap, model-free variants that a naive string filter usually misses."""
    out = [
        {"technique": "upper case", "value": value.upper()},
        {"technique": "url-encoded inside the value", "value": urllib.parse.quote(value, safe="")},
        {"technique": "padded with whitespace", "value": f" {value} "},
    ]
    if "../" in value:
        out.append({"technique": "backslash separators", "value": value.replace("../", "..\\")})
        out.append({"technique": "nested dot-dot-slash", "value": value.replace("../", "....//")})
        out.append({"technique": "absolute path", "value": "/etc/passwd"})
    if "'" in value:
        out.append({"technique": "comment terminator", "value": value.split("'")[0] + "' OR 1=1 --"})
        out.append({"technique": "union select", "value": "x' UNION SELECT id, tenant_id, full_name, email, role FROM customers --"})
    if len(value) > 15 and len(set(value[:-1])) <= 2:
        out.append({"technique": "longer backtracking run", "value": value[0] * (len(value) + 4) + "!"})
        out.append({"technique": "dotted backtracking run", "value": "a." * 14 + "a!"})
    return out


# ---------------------------------------------------------------- code repair


class PatchError(ValueError):
    pass


def clean_source(text: str) -> str:
    """Strip markdown fences and copied line numbers from a model-written file."""
    text = (text or "").strip("\n")
    if text.lstrip().startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    lines = text.splitlines()
    numbered = re.compile(r"^\s*\d+\s*\|\s?")
    if lines and all(numbered.match(l) for l in lines if l.strip()):
        lines = [numbered.sub("", l) for l in lines]
    return "\n".join(lines).rstrip() + "\n"


def unified_diff(path: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        fromfile=f"a/{path}", tofile=f"b/{path}"))


HARNESS = r'''"""Written by OODA-Aegis. Replays the attack, its fuzz variants and recorded
legitimate traffic against the code in this folder."""
import json
import os
import re
import sys
import threading
import time

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aegis_detect import response_is_safe  # noqa: E402
from service.main import app  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = json.load(open(os.path.join(HERE, "aegis_cases.json")))
GOLDEN = os.path.join(HERE, "aegis_golden.json")
client = TestClient(app, raise_server_exceptions=False)
HANG_S = 2.5


def call(params):
    box = {}

    def run():
        started = time.perf_counter()
        try:
            box["r"] = client.get(CASES["path"], params=params)
        except Exception as exc:  # the patched code blew up outside FastAPI's handlers
            box["error"] = repr(exc)
        box["ms"] = (time.perf_counter() - started) * 1000

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(HANG_S)
    if worker.is_alive():
        return None, HANG_S * 1000
    assert "error" not in box, f"the service crashed: {box.get('error')}"
    return box["r"], box["ms"]


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if not re.search(r"(ms|elapsed|time)", k, re.I)}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def test_record_golden_responses():
    if os.path.exists(GOLDEN):
        pytest.skip("golden responses already recorded")
    golden = {}
    for case in CASES["benign"]:
        r, _ = call(case["params"])
        assert r is not None and r.status_code == 200, f"legitimate request failed on the original code: {case}"
        golden[case["id"]] = stable(r.json())
    json.dump(golden, open(GOLDEN, "w"), indent=1)


@pytest.mark.parametrize("case", CASES["attacks"], ids=[c["id"] for c in CASES["attacks"]])
def test_attack_is_neutralised(case):
    r, ms = call(case["params"])
    assert r is not None, f"request hung for more than {HANG_S}s (denial of service)"
    ok, hits = response_is_safe(r.status_code, r.text, ms, case["params"])
    assert ok, f"unsafe response (HTTP {r.status_code}): {', '.join(hits)}"


@pytest.mark.parametrize("case", CASES["benign"], ids=[c["id"] for c in CASES["benign"]])
def test_legitimate_traffic_unchanged(case):
    golden = json.load(open(GOLDEN))
    r, _ = call(case["params"])
    assert r is not None and r.status_code == 200, f"legitimate request broke: HTTP {getattr(r, 'status_code', 'hang')}"
    assert stable(r.json()) == golden[case["id"]], "legitimate response changed after the patch"
'''


@dataclass
class SandboxResult:
    passed: bool
    output: str
    counts: dict[str, int] = field(default_factory=dict)
    per_test: list[dict] = field(default_factory=list)


Runner = Callable[[Path, list[str], int], tuple[int, str]]
"""runner(folder, pytest_args, timeout_s) -> (exit_code, combined_output)"""


def prepare_sandbox(folder: Path, app_root: Path, rel_file: str, new_source: str | None,
                    cases: dict, model_test: str | None) -> None:
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(app_root, folder, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
    if new_source is not None:
        (folder / rel_file).write_text(new_source)
    (folder / "aegis_cases.json").write_text(json.dumps(cases, indent=1))
    (folder / "test_aegis_harness.py").write_text(HARNESS)
    shutil.copy(HERE / "detect.py", folder / "aegis_detect.py")
    if model_test:
        (folder / "test_model_repro.py").write_text(model_test)


def parse_junit(path: Path) -> tuple[dict[str, int], list[dict]]:
    import xml.etree.ElementTree as ET

    counts = {"passed": 0, "failed": 0, "skipped": 0}
    tests: list[dict] = []
    if not path.exists():
        return counts, tests
    for case in ET.parse(path).getroot().iter("testcase"):
        outcome, message = "passed", ""
        for child in case:
            if child.tag in ("failure", "error"):
                outcome, message = "failed", (child.get("message") or "")[:300]
            elif child.tag == "skipped":
                outcome = "skipped"
        counts[outcome] += 1
        tests.append({"name": f"{case.get('classname', '').split('.')[-1]}::{case.get('name')}",
                      "outcome": outcome, "message": message, "seconds": float(case.get("time") or 0)})
    return counts, tests


def run_phase(runner: Runner, folder: Path, targets: list[str], timeout_s: int) -> SandboxResult:
    junit = folder / "report.xml"
    if junit.exists():
        junit.unlink()
    args = ["-q", "-p", "no:cacheprovider", "--timeout=20", "--timeout-method=thread",
            "--junitxml=report.xml", *targets]
    code, output = runner(folder, args, timeout_s)
    counts, tests = parse_junit(junit)
    if not tests and code != 0:
        counts = {"passed": 0, "failed": 1, "skipped": 0}
        tests = [{"name": "pytest session", "outcome": "failed", "message": "timed out or crashed", "seconds": 0}]
    return SandboxResult(code == 0 and counts["failed"] == 0, output[-6000:], counts, tests)


def verify_repair(runner: Runner, work: Path, app_root: Path, rel_file: str, patched: str,
                  cases: dict, model_test: str) -> dict:
    """The closed loop. The gate is written by the agent, not the model:
    1. on the vulnerable code, the exploit observed in production must still work
       (proof that the harness really reproduces the attack);
    2. on the patched code, the exploit and every red-team variant must come back
       safe, recorded legitimate traffic must be byte-for-byte unchanged, and the
       service's own tests must pass.
    The model's own reproduction test is run too and reported, but it cannot
    approve or block a patch on its own."""
    v1 = work / "v1"
    v2 = work / "v2"
    prepare_sandbox(v1, app_root, rel_file, None, cases, model_test)
    record = run_phase(runner, v1, ["test_aegis_harness.py::test_record_golden_responses"], 60)
    if not record.passed:
        return {"ok": False, "stage": "record", "reason": "legitimate traffic fails on the original code",
                "v1": record.__dict__}
    repro = run_phase(runner, v1, ["test_aegis_harness.py::test_attack_is_neutralised[original]"], 45)
    reproduces = not repro.passed

    prepare_sandbox(v2, app_root, rel_file, patched, cases, model_test)
    shutil.copy(v1 / "aegis_golden.json", v2 / "aegis_golden.json")
    gate = run_phase(runner, v2, ["test_aegis_harness.py", "tests"], 120)
    advisory = run_phase(runner, v2, ["test_model_repro.py"], 45) if model_test.strip() else None

    ok = reproduces and gate.passed
    reason = "ok"
    if not reproduces:
        reason = "the observed exploit does not reproduce on the original code"
    elif not gate.passed:
        failed = [t for t in gate.per_test if t["outcome"] == "failed"]
        reason = "; ".join(f"{t['name']}: {t['message']}" for t in failed[:4]) or "tests failed"
    return {"ok": ok, "stage": "verify", "reason": reason, "reproduces_on_v1": reproduces,
            "model_test_passed": advisory.passed if advisory else None,
            "v1": repro.__dict__, "v2": gate.__dict__, "model_test": advisory.__dict__ if advisory else None}


def compile_check(source: str) -> str | None:
    try:
        compile(source, "patched.py", "exec")
        return None
    except SyntaxError as exc:
        return f"SyntaxError line {exc.lineno}: {exc.msg}"


RESULT_FILES = ("report.xml", "aegis_golden.json")


def subprocess_runner(extra_env: dict[str, str] | None = None, stage: str = "/tmp/aegis_app") -> Runner:
    """Runner for machines without Docker (the Kaggle benchmark). Like production,
    the code runs from a shallow folder so path tricks behave the same way."""
    import subprocess
    import sys

    def run(folder: Path, args: list[str], timeout_s: int) -> tuple[int, str]:
        app = Path(stage).resolve()
        if app.exists():
            shutil.rmtree(app)
        shutil.copytree(folder, app)
        env = {**os.environ, "REDIS_HOST": "127.0.0.1", "PYTHONPATH": str(app),
               "DOCS_DIR": str(app / "public_docs"), "CUSTOMER_DB": str(app / "data" / "customers.db"),
               **(extra_env or {})}
        try:
            proc = subprocess.run([sys.executable, "-m", "pytest", *args], cwd=app, env=env,
                                  capture_output=True, text=True, timeout=timeout_s)
            code, output = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as exc:
            code, output = 124, f"timed out after {timeout_s}s\n{exc.stdout or ''}"
        for name in RESULT_FILES:
            if (app / name).exists():
                shutil.copy(app / name, folder / name)
        return code, output

    return run
