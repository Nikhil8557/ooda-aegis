"""Benchmark: can a Meta model defend the service on its own, and how often?

For each of the three real vulnerabilities and each trial, this runs the same
four model calls the live agent makes (triage, virtual patch, red team, repair)
and judges every answer with the same verifier (validated regex, sandboxed
pytest with reproduction, fuzz variants and golden legitimate traffic).

The exploit record each trial starts from is produced by really attacking the
vulnerable service in a subprocess, not written by hand.

Models come from the environment exactly like the live agent
(see infrastructure/agent/aegis/llm.py):
  local Llama:   OLLAMA_BASE_URL=http://localhost:11434/v1
  Muse Glimmer:  GLIMMER_BASE_URL=http://127.0.0.1:8080/v1   (used for both tiers)

  python benchmark/run_benchmark.py --trials 3 --out benchmark/results/llama.jsonl
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "infrastructure" / "agent"))

from aegis import detect, prompts, verify  # noqa: E402
from aegis.llm import ModelError, chat_json, resolve_tiers  # noqa: E402

SCENARIOS = [
    {"id": "path_traversal", "expect": "path_traversal", "path": "/api/v1/documents/read",
     "param": "file", "fixed": {}, "value": "../../../../etc/passwd", "file": "service/routes/documents.py"},
    {"id": "sqli", "expect": "sql_injection", "path": "/api/v1/auth/customer-lookup",
     "param": "email", "fixed": {"tenant": "tenant-prod-99"}, "value": "x' OR '1'='1",
     "file": "service/routes/customers.py"},
    {"id": "redos", "expect": "redos", "path": "/api/v1/validator/email-or-domain",
     "param": "input", "fixed": {}, "value": "a" * 27 + "!", "file": "service/routes/validator.py"},
]

CANDIDATES = 6  # same as the live agent (MAX_REPAIR_CANDIDATES)

PROBE = r'''
import json, sys, time
from fastapi.testclient import TestClient
from service.main import app
path, params = sys.argv[1], json.loads(sys.argv[2])
c = TestClient(app)
t = time.perf_counter(); r = c.get(path, params=params); ms = (time.perf_counter() - t) * 1000
print(json.dumps({"status": r.status_code, "duration_ms": round(ms, 1), "sample": r.text[:600]}))
'''


def make_release(work: Path) -> Path:
    release = work / "release"
    if release.exists():
        shutil.rmtree(release)
    shutil.copytree(ROOT / "infrastructure" / "app", release,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "data"))
    (release / "data").mkdir()
    subprocess.run([sys.executable, str(release / "seed_db.py"), str(release / "data" / "customers.db")],
                   check=True, capture_output=True)
    shutil.copy(release / "fake_secrets.env", release / ".env")
    return release


def real_exploit(release: Path, sc: dict, stage: str) -> dict:
    """Attack the vulnerable code for real and build the telemetry record."""
    app = Path(stage).resolve()
    if app.exists():
        shutil.rmtree(app)
    shutil.copytree(release, app)
    (app / "probe.py").write_text(PROBE)
    params = {**sc["fixed"], sc["param"]: sc["value"]}
    env = {"PYTHONPATH": str(app), "REDIS_HOST": "127.0.0.1", "DOCS_DIR": str(app / "public_docs"),
           "CUSTOMER_DB": str(app / "data" / "customers.db"), "PATH": "/usr/bin:/bin"}
    out = subprocess.run([sys.executable, "probe.py", sc["path"], json.dumps(params)], cwd=app, env=env,
                         capture_output=True, text=True, timeout=120)
    resp = json.loads(out.stdout.strip().splitlines()[-1])
    raw = urllib.parse.urlencode(params, quote_via=urllib.parse.quote, safe="")
    return {"method": "GET", "path": sc["path"], "raw_query": raw, "query": params, "container": "benchmark",
            **resp}


def one_trial(sc: dict, trial: int, release: Path, tiers: dict, stage: str) -> dict:
    edge, repair = tiers["edge"], tiers["repair"]
    record = real_exploit(release, sc, stage)
    hits = detect.findings(record)
    row: dict = {"scenario": sc["id"], "trial": trial, "edge_model": edge.model, "repair_model": repair.model,
                 "exploit_status": record["status"], "exploit_ms": record["duration_ms"], "rules": hits}
    t0 = time.time()
    # 1. triage
    try:
        triage, m = chat_json(edge, prompts.TRIAGE_SYSTEM, prompts.triage_user(record, hits),
                              prompts.TRIAGE_SCHEMA, "triage", max_tokens=600)
        row.update(triage_class=triage.get("attack_class"), triage_cwe=triage.get("cwe"),
                   triage_correct=triage.get("attack_class") == sc["expect"], triage_ms=m["latency_ms"])
    except ModelError as exc:
        triage = {"attack_class": "other", "cwe": "", "summary": "", "malicious_fragment": ""}
        row.update(triage_correct=False, triage_error=str(exc)[:200])
    # 2. virtual patch
    shipped = json.loads((release / "tests" / "benign_traffic.json").read_text())
    benign = shipped[sc["path"]]
    benign_uris = [verify.build_uri(sc["path"], p) for p in benign]
    raw_uri = f"{sc['path']}?{record['raw_query']}"
    feedback, rule, vp_attempts, vp_ms = "", None, 0, []
    for attempt in range(1, 4):
        vp_attempts = attempt
        try:
            out, m = chat_json(edge, prompts.VPATCH_SYSTEM, prompts.vpatch_user(record, triage, benign_uris, feedback),
                               prompts.VPATCH_SCHEMA, "virtual_patch", max_tokens=500)
        except ModelError as exc:
            feedback = str(exc)
            continue
        vp_ms.append(m["latency_ms"])
        regex, why = verify.compile_rule(out)
        ok, reason = verify.validate_regex(regex, [raw_uri], benign_uris) if regex else (False, why)
        if ok:
            rule = regex
            row["vpatch_rule"] = verify.describe_rule(out)
            break
        feedback = f"rule ({verify.describe_rule(out)}): {reason}"
    row.update(vpatch_ok=bool(rule), vpatch_attempts=vp_attempts, vpatch_ms=vp_ms, vpatch_regex=rule,
               contain_s=round(time.time() - t0, 1) if rule else None)
    # 3. red team
    cases = [{"id": "original", "value": sc["value"]}]
    try:
        out, m = chat_json(edge, prompts.FUZZ_SYSTEM, prompts.fuzz_user(sc["param"], sc["value"], triage),
                           prompts.FUZZ_SCHEMA, "fuzz", max_tokens=900, temperature=0.7)
        model_cases = [x for x in out.get("mutations", []) if isinstance(x, dict) and x.get("value")][:6]
        row["fuzz_ms"] = m["latency_ms"]
    except ModelError:
        model_cases = []
    cases += [{"id": f"model-{i + 1}", "value": str(x["value"])[:200]} for i, x in enumerate(model_cases)]
    cases += [{"id": f"rule-{i + 1}", "value": x["value"]} for i, x in enumerate(verify.deterministic_mutations(sc["value"]))]
    uris = [verify.build_uri(sc["path"], {**sc["fixed"], sc["param"]: c["value"]}) for c in cases]
    covered = verify.regex_coverage(rule, uris) if rule else [False] * len(cases)
    row.update(fuzz_model_variants=len(model_cases), fuzz_total=len(cases), edge_covers=sum(covered))
    # 4. repair: best-of-6 with the verifier, feedback after each failure
    source = (release / sc["file"]).read_text()
    suite = {"path": sc["path"],
             "attacks": [{"id": c["id"], "params": {**sc["fixed"], sc["param"]: c["value"]}} for c in cases],
             "benign": [{"id": f"benign-{i + 1}", "params": p} for i, p in enumerate(benign)]}
    runner = verify.subprocess_runner(stage=stage)
    work = Path(stage + "_work")
    feedback, attempts, verified, reasons, repair_ms = "", 0, False, [], []
    for attempt in range(1, CANDIDATES + 1):
        attempts = attempt
        try:
            out, m = chat_json(repair, prompts.REPAIR_SYSTEM,
                               prompts.repair_user(sc["file"], source, record, triage, hits, feedback),
                               prompts.REPAIR_SCHEMA, "repair", max_tokens=3500,
                               temperature=(0.2, 0.8)[(attempt - 1) % 2])
            repair_ms.append(m["latency_ms"])
            patched = verify.clean_source(str(out.get("patched_source") or ""))
            if patched.strip() == source.strip():
                raise verify.PatchError("the patched file is identical to the vulnerable file")
            problem = verify.compile_check(patched)
            if problem:
                raise verify.PatchError(problem)
        except (ModelError, verify.PatchError, json.JSONDecodeError) as exc:
            reasons.append(f"pre-test: {str(exc)[:200]}")
            feedback = str(exc)
            continue
        report = verify.verify_repair(runner, work / f"a{attempt}", release, sc["file"], patched, suite,
                                      out.get("test_code") or "")
        reasons.append(report["reason"][:300])
        row["model_test_passed_last"] = report.get("model_test_passed")
        if report["ok"]:
            verified = True
            row.update(diff=verify.unified_diff(sc["file"], source, patched), invariant=out.get("invariant"),
                       tests_passed=report["v2"]["counts"]["passed"], root_cause=out.get("root_cause"))
            break
        feedback = report["reason"] + "\n" + report.get("v2", {}).get("output", "")[-1500:]
    row.update(repair_verified=verified, repair_attempts=attempts, repair_reasons=reasons, repair_ms=repair_ms,
               heal_s=round(time.time() - t0, 1) if verified else None)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--out", default=str(ROOT / "benchmark" / "results" / "results.jsonl"))
    ap.add_argument("--work", default="/tmp/aegis_bench")
    ap.add_argument("--parallel", type=int, default=3)
    args = ap.parse_args()
    tiers = resolve_tiers()
    print("models:", {k: v.public() for k, v in tiers.items()}, flush=True)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    release = make_release(work)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    jobs = [(sc, t) for t in range(1, args.trials + 1) for sc in SCENARIOS]

    def worker(slot: int) -> None:
        while True:
            with lock:
                if not jobs:
                    return
                sc, t = jobs.pop(0)
            started = time.time()
            try:
                row = one_trial(sc, t, release, tiers, f"/tmp/aegis_slot{slot}")
            except Exception as exc:  # a crash is a result too
                row = {"scenario": sc["id"], "trial": t, "crash": f"{type(exc).__name__}: {exc}"[:400]}
            row["wall_s"] = round(time.time() - started, 1)
            with lock:
                with open(out, "a") as handle:
                    handle.write(json.dumps(row) + "\n")
            print(json.dumps({k: row.get(k) for k in ("scenario", "trial", "triage_correct", "vpatch_ok",
                                                       "repair_verified", "repair_attempts", "wall_s", "crash")}),
                  flush=True)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(args.parallel)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()


if __name__ == "__main__":
    main()
