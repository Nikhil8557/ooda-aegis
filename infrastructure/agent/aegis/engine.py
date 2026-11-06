"""The OODA loop: Observe -> Orient -> Decide -> Act, on two horizons.

Horizon 1 (seconds): the edge model writes a virtual patch; it is validated and
loaded into Nginx, then broadcast to peer nodes as a "vaccine".
Horizon 2 (about a minute): the repair model writes a code fix and a reproduction
test; the fix ships only after it is proven in a no-network sandbox, rolled out
by weighted traffic shifting with canary probes, and rolled back on any regression.
"""
from __future__ import annotations

import copy
import json
import os
import threading
import time
import traceback
import urllib.parse
from pathlib import Path
from typing import Any, Callable

import httpx

from . import detect, infra, prompts, verify
from .llm import ModelError, chat_json, resolve_tiers

# UI metadata only: which dashboard scenario an endpoint belongs to. The agent
# never uses this to decide how to fix anything.
ENDPOINTS = {
    "/api/v1/documents/read": {"scenario": "path_traversal", "param": "file", "fixed": {}},
    "/api/v1/auth/customer-lookup": {"scenario": "sqli", "param": "email", "fixed": {"tenant": "tenant-prod-99"}},
    "/api/v1/validator/email-or-domain": {"scenario": "redos", "param": "input", "fixed": {}},
}
PROXY_URL = os.getenv("PROXY_URL", "http://aegis_proxy")
# Best-of-N with a verifier: candidates alternate a careful and a more creative
# sample, and each failure is fed back to the next one.
MAX_REPAIR_ATTEMPTS = int(os.getenv("MAX_REPAIR_CANDIDATES", "6"))
REPAIR_TEMPERATURES = (0.2, 0.8)
MAX_VPATCH_ATTEMPTS = 3
FLEET = [
    {"id": "node-eu-west", "name": "edge-eu-west-1", "zone": "eu-west-1"},
    {"id": "node-ap-south", "name": "edge-ap-south-1", "zone": "ap-south-1"},
    {"id": "node-us-east", "name": "edge-us-east-2", "zone": "us-east-2"},
]
RUN_LOG = infra.WORK / "runs"


def now_label() -> str:
    return time.strftime("%H:%M:%S")


def fresh_state(tiers) -> dict[str, Any]:
    return {
        "mode": "live",
        "models": {k: v.public() for k, v in tiers.items()},
        "phase": "idle",
        "busy": False,
        "scenario": None,
        "incident": None,
        "virtualPatch": {"active": False, "regex": None, "ruleId": None, "model": None,
                         "modelLatencyMs": None, "reloadMs": None, "attempts": []},
        "container": {"active": infra.BLUE, "version": "v1.0.0-vulnerable", "previous": None},
        "trafficSplit": {"old": 100, "new": 0},
        "trace": [],
        "logs": [],
        "lastResult": None,
        "fuzz": [],
        "fleet": [{**n, "status": "vulnerable", "syncLatencyMs": 0} for n in FLEET],
        "canary": {"status": "idle", "probesOk": 0, "probesFailed": 0, "step": None, "p99LatencyMs": 0,
                   "circuitBreakerTripped": False},
        "repair": None,
        "sandbox": None,
        "metrics": {"requests": 0, "blocked": 0, "exploited": 0, "remediated": 0, "avgLatencyMs": 0,
                    "errorRatePercent": 0, "cpu": 0, "memoryMb": 0, "fuzzPassRate": None,
                    "fleetImmune": 0, "timeToContainS": None, "timeToHealS": None},
        "history": [],
    }


class Engine:
    def __init__(self) -> None:
        self.tiers = resolve_tiers()
        self.lock = threading.RLock()
        self.state = fresh_state(self.tiers)
        self.listeners: list[Callable[[dict], None]] = []
        self.version_counter = 1
        self.active_release = "v1.0.0"
        self.benign_seen: dict[str, list[dict]] = {}
        self.recent: list[dict] = []
        self.run_file: Path | None = None
        self.run_started = time.time()

    # ------------------------------------------------------------- state plumbing

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self.state)

    def emit(self) -> None:
        snap = self.snapshot()
        if self.run_file:
            with open(self.run_file, "a") as handle:
                handle.write(json.dumps({"t": round(time.time() - self.run_started, 3), "state": snap}) + "\n")
        for listener in list(self.listeners):
            try:
                listener(snap)
            except Exception:
                pass

    def update(self, **changes) -> None:
        with self.lock:
            self.state.update(changes)
        self.emit()

    def trace(self, horizon: str, phase: str, summary: str, details: str, tool: dict | None = None) -> None:
        step = {"id": f"t{len(self.state['trace']) + 1}", "timestamp": now_label(), "horizon": horizon,
                "phase": phase, "summary": summary, "details": details}
        if tool:
            step["toolCall"] = tool
        with self.lock:
            self.state["trace"].append(step)
        self.emit()

    def log_request(self, entry: dict) -> None:
        with self.lock:
            self.state["logs"] = [entry] + self.state["logs"][:39]
            m = self.state["metrics"]
            m["requests"] += 1
            self.recent = (self.recent + [entry])[-30:]
            m["avgLatencyMs"] = round(sum(e["durationMs"] for e in self.recent) / len(self.recent), 1)
            m["errorRatePercent"] = round(100 * sum(e["statusCode"] >= 500 or e["verdict"] == "exploited"
                                                    for e in self.recent) / len(self.recent), 1)
        self.emit()

    # ------------------------------------------------------------- lifecycle

    def boot(self) -> None:
        infra.wait_for_proxy()
        infra.init_base_release()
        self.reset(initial=True)

    def reset(self, initial: bool = False) -> None:
        with self.lock:
            if self.state.get("busy") and not initial:
                raise RuntimeError("a defense cycle is running; wait for it to finish")
        # Order matters: move traffic back to v1 first, so nginx never points at a
        # container that no longer exists, then remove the agent-built releases.
        infra.write_conf("upstream.conf", infra.upstream_conf({infra.BLUE: 1}))
        infra.write_conf("dynamic_rules.conf", infra.EMPTY_RULES)
        infra.nginx_reload_checked()
        infra.remove_managed()
        self.active_release = "v1.0.0"
        self.version_counter = 1
        self.benign_seen = {}
        self.recent = []
        with self.lock:
            self.state = fresh_state(self.tiers)
        RUN_LOG.mkdir(parents=True, exist_ok=True)
        self.run_started = time.time()
        self.run_file = RUN_LOG / f"run-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        self.emit()

    # ------------------------------------------------------------- traffic

    def send(self, scenario: str, value: str, malicious: bool) -> dict:
        """Send one request through the real proxy, as an outside client would."""
        path, meta = next((p, m) for p, m in ENDPOINTS.items() if m["scenario"] == scenario)
        params = {**meta["fixed"], meta["param"]: value}
        uri = verify.build_uri(path, params)
        started = time.perf_counter()
        try:
            r = httpx.get(PROXY_URL + uri, timeout=15)
            status, body = r.status_code, r.text
        except httpx.TimeoutException:
            status, body = 504, '{"error":"GatewayTimeout","message":"No response within 15s"}'
        ms = round((time.perf_counter() - started) * 1000, 1)
        safe, hits = detect.response_is_safe(status, body, ms, params)
        if status == 403 and "AEGIS-VPATCH" in body:
            verdict = "blocked_by_edge"
        elif not safe or status in (502, 504):
            verdict = "exploited"
        elif malicious and "vulnerable" not in self.state["container"]["version"]:
            verdict = "sanitized_by_v2"
        else:
            verdict = "benign"
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body[:1500]
        version = self.state["container"]["version"]
        entry = {"id": f"r{int(time.time() * 1000)}", "timestamp": now_label(), "method": "GET",
                 "endpoint": path, "payload": value[:60], "statusCode": status, "durationMs": ms,
                 "statusText": ", ".join(hits) if hits else ("blocked at proxy" if verdict == "blocked_by_edge" else "ok"),
                 "verdict": verdict, "containerVersion": "edge proxy" if verdict == "blocked_by_edge" else version}
        result = {"statusCode": status, "durationMs": ms, "statusText": entry["statusText"],
                  "responseBody": parsed, "verdict": verdict, "containerVersion": entry["containerVersion"],
                  "uri": uri}
        with self.lock:
            self.state["lastResult"] = result
            m = self.state["metrics"]
            if verdict == "blocked_by_edge":
                m["blocked"] += 1
            if verdict == "exploited":
                m["exploited"] += 1
        self.log_request(entry)
        return result

    # ------------------------------------------------------------- observe

    def on_telemetry(self, record: dict) -> None:
        path = record.get("path")
        if path not in ENDPOINTS:
            return
        hits = detect.findings(record)
        if not hits:
            if 200 <= (record.get("status") or 0) < 300:
                seen = self.benign_seen.setdefault(path, [])
                params = record.get("query") or {}
                if params and params not in seen:
                    seen.append(params)
                    del seen[:-12]
            return
        with self.lock:
            if self.state["busy"]:
                return
            self.state["busy"] = True
        threading.Thread(target=self._defend_safely, args=(record, hits), daemon=True).start()

    def _defend_safely(self, record: dict, hits: list[str]) -> None:
        try:
            self.defend(record, hits)
        except Exception as exc:
            traceback.print_exc()
            self.trace("Runtime Orchestrator", "Act", "Defense cycle stopped safely",
                       f"{type(exc).__name__}: {exc}. Any virtual patch already loaded stays active.")
            self.update(phase="degraded")
        finally:
            with self.lock:
                self.state["busy"] = False
            self.emit()

    def benign_cases(self, path: str) -> list[dict]:
        shipped = json.loads((infra.release_dir(self.active_release) / "tests" / "benign_traffic.json").read_text())
        params = list(shipped.get(path, []))
        for p in self.benign_seen.get(path, []):
            if p not in params:
                params.append(p)
        return params

    # ------------------------------------------------------------- the loop

    def defend(self, record: dict, hits: list[str]) -> None:
        t0 = time.time()
        path = record["path"]
        meta = ENDPOINTS[path]
        scenario = meta["scenario"]
        attack_params = record.get("query") or {}
        attack_value = attack_params.get(meta["param"], "")
        attack_uri = verify.build_uri(path, attack_params)
        raw_uri = f"{path}?{record.get('raw_query', '')}"
        incident = {"id": f"INC-{int(t0)}", "scenario": scenario, "startedAt": now_label(), "uri": raw_uri}
        with self.lock:
            self.state.update(scenario=scenario, incident=incident, phase="exploited", trace=[], fuzz=[],
                              repair=None, sandbox=None)
            self.state["fleet"] = [{**n, "status": "vulnerable", "syncLatencyMs": 0} for n in FLEET]
        self.emit()

        # OBSERVE
        self.trace("Runtime Orchestrator", "Observe", "Telemetry rules fired on a live response",
                   f"{record.get('method')} {raw_uri} returned HTTP {record.get('status')} in "
                   f"{record.get('duration_ms')} ms from {record.get('container')}. Rules: {', '.join(hits)}.",
                   {"name": "telemetry.findings", "input": {"uri": raw_uri}, "output": json.dumps(hits)})

        # ORIENT (edge tier)
        edge = self.tiers["edge"]
        triage, tmeta = chat_json(edge, prompts.TRIAGE_SYSTEM, prompts.triage_user(record, hits),
                                  prompts.TRIAGE_SCHEMA, "triage", max_tokens=600)
        self.trace("Horizon 1 (Edge Tier)", "Orient", f"Triage: {triage.get('attack_class')} ({triage.get('cwe')})",
                   f"{triage.get('summary')}",
                   {"name": f"{edge.model}.triage", "input": {"rules": hits},
                    "output": json.dumps({**triage, "latency_ms": tmeta["latency_ms"]})})

        # DECIDE + ACT, horizon 1: virtual patch
        self.update(phase="edge_containment")
        benign = self.benign_cases(path)
        benign_uris = [verify.build_uri(path, p) for p in benign]
        attack_uris = list({raw_uri, attack_uri})
        feedback, rule, vmeta, attempts = "", None, None, []
        for attempt in range(1, MAX_VPATCH_ATTEMPTS + 1):
            out, vmeta = chat_json(edge, prompts.VPATCH_SYSTEM,
                                   prompts.vpatch_user(record, triage, benign_uris, feedback),
                                   prompts.VPATCH_SCHEMA, "virtual_patch", max_tokens=500)
            regex, why = verify.compile_rule(out)
            ok, reason = (verify.validate_regex(regex, attack_uris, benign_uris) if regex else (False, why))
            attempts.append({"attempt": attempt, "rule": verify.describe_rule(out), "regex": regex, "ok": ok,
                             "reason": reason, "latencyMs": vmeta["latency_ms"]})
            if ok:
                rule = regex
                break
            feedback = f"rule ({verify.describe_rule(out)}): {reason}"
        with self.lock:
            self.state["virtualPatch"]["attempts"] = attempts
        if not rule:
            self.trace("Horizon 1 (Edge Tier)", "Decide", "No safe virtual patch; going straight to repair",
                       f"All {len(attempts)} candidate regexes failed validation (last: {feedback}). "
                       "OODA-Aegis never loads an unvalidated rule into the proxy.")
        else:
            rule_id = f"AEGIS-VPATCH-{len(self.state['history']) + 1:02d}"
            reload_ms = infra.nginx_apply("dynamic_rules.conf", infra.rules_conf(rule_id, rule))
            contained = time.time() - t0
            with self.lock:
                self.state["virtualPatch"].update(active=True, regex=rule, ruleId=rule_id, model=edge.label,
                                                  modelLatencyMs=vmeta["latency_ms"], reloadMs=round(reload_ms))
                self.state["metrics"]["timeToContainS"] = round(contained, 1)
            self.trace("Horizon 1 (Edge Tier)", "Act", f"Virtual patch {rule_id} live at the proxy",
                       f"Regex validated against the attack and {len(benign_uris)} legitimate requests "
                       f"(attempt {len(attempts)}), then loaded with nginx -t and a graceful reload in "
                       f"{reload_ms:.0f} ms. Attack contained {contained:.1f}s after detection.",
                       {"name": "nginx.apply_virtual_patch", "input": {"regex": rule, "action": "DROP_403"},
                        "output": json.dumps({"rule_id": rule_id, "reload_ms": round(reload_ms)})})
            self.vaccinate(rule_id, rule, triage)

        # HORIZON 2: fuzz + repair + verify
        self.update(phase="code_repair")
        fuzz_cases = self.fuzz(meta, attack_value, triage, path, rule)
        self.repair_and_ship(record, hits, triage, path, meta, attack_params, fuzz_cases, benign, t0, rule)

    def vaccinate(self, rule_id: str, rule: str, triage: dict) -> None:
        vaccine = {"vaccine_id": f"VAC-{rule_id}", "rule_id": rule_id, "regex": rule,
                   "cwe": triage.get("cwe"), "origin": "node-local"}
        acks = infra.broadcast_vaccine(vaccine, expect=len(FLEET))
        by_node = {a["node"]: a for a in acks}
        with self.lock:
            for node in self.state["fleet"]:
                ack = by_node.get(node["id"])
                if ack:
                    node.update(status="immune" if ack.get("self_test") else "vaccine_received",
                                syncLatencyMs=ack.get("latency_ms", 0))
            self.state["metrics"]["fleetImmune"] = sum(n["status"] == "immune" for n in self.state["fleet"])
        self.trace("Horizon 1 (Edge Tier)", "Act", f"Vaccine broadcast: {len(acks)}/{len(FLEET)} peer nodes acknowledged",
                   "The validated rule was published on the Redis fleet bus; each peer compiled it and "
                   "self-tested it before acknowledging.",
                   {"name": "redis.publish(aegis:vaccine)", "input": {"rule_id": rule_id},
                    "output": json.dumps([{k: a.get(k) for k in ("node", "latency_ms", "self_test")} for a in acks])})

    def fuzz(self, meta: dict, attack_value: str, triage: dict, path: str, rule: str | None) -> list[dict]:
        edge = self.tiers["edge"]
        cases = [{"id": "original", "technique": "original exploit", "value": attack_value}]
        try:
            out, fmeta = chat_json(edge, prompts.FUZZ_SYSTEM, prompts.fuzz_user(meta["param"], attack_value, triage),
                                   prompts.FUZZ_SCHEMA, "fuzz", max_tokens=900, temperature=0.7)
            model_cases = [m for m in out.get("mutations", []) if isinstance(m, dict) and m.get("value")][:6]
            source = f"{edge.model}"
        except ModelError:
            model_cases, source = [], "none"
        for i, m in enumerate(model_cases):
            cases.append({"id": f"model-{i + 1}", "technique": str(m.get("technique"))[:60],
                          "value": str(m["value"])[:200], "source": "model"})
        for i, m in enumerate(verify.deterministic_mutations(attack_value)):
            cases.append({"id": f"rule-{i + 1}", "technique": m["technique"], "value": m["value"], "source": "rules"})
        uris = [verify.build_uri(path, {**meta["fixed"], meta["param"]: c["value"]}) for c in cases]
        covered = verify.regex_coverage(rule, uris) if rule else [False] * len(cases)
        fuzz_view = [{"id": c["id"], "technique": c["technique"], "mutatedPayload": c["value"][:80],
                      "objective": "bypass the fix", "status": "pending",
                      "edgeCovered": cov, "durationMs": 0} for c, cov in zip(cases, covered)]
        with self.lock:
            self.state["fuzz"] = fuzz_view
        self.trace("Horizon 2 (Repair Tier)", "Orient", f"Red team: {len(cases)} attack variants generated",
                   f"{len(model_cases)} from {source}, {len(cases) - 1 - len(model_cases)} from mutation rules. "
                   f"The edge regex alone would catch {sum(covered)}/{len(cases)}, which is why the code "
                   "itself must be fixed.",
                   {"name": "red_team.mutate", "input": {"seed": attack_value[:60]},
                    "output": json.dumps([c["value"][:40] for c in cases[:6]])})
        return [{"id": c["id"], "params": {**meta["fixed"], meta["param"]: c["value"]}} for c in cases]

    def repair_and_ship(self, record, hits, triage, path, meta, attack_params, fuzz_cases, benign, t0, rule) -> None:
        repair_tier = self.tiers["repair"]
        release = infra.release_dir(self.active_release)
        rel_file = self.locate(release, path)
        source = (release / rel_file).read_text()
        self.trace("Horizon 2 (Repair Tier)", "Orient", f"Fault localised to {rel_file}",
                   f"Matched the route {path} to its handler by reading the service source "
                   f"(release {self.active_release}).",
                   {"name": "repo.locate_route", "input": {"route": path}, "output": rel_file})
        cases = {"path": path, "attacks": fuzz_cases,
                 "benign": [{"id": f"benign-{i + 1}", "params": p} for i, p in enumerate(benign)]}
        runner = infra.docker_runner(f"aegis-app:{self.active_release}" if self.active_release != "v1.0.0"
                                     else infra.BASE_IMAGE)
        feedback, attempts, report, patched, out = "", [], None, None, None
        work = infra.WORK / "incidents" / self.state["incident"]["id"]
        for attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
            self.update(phase="code_repair")
            try:
                out, rmeta = chat_json(repair_tier, prompts.REPAIR_SYSTEM,
                                       prompts.repair_user(rel_file, source, record, triage, hits, feedback),
                                       prompts.REPAIR_SCHEMA, "repair", max_tokens=3500,
                                       temperature=REPAIR_TEMPERATURES[(attempt - 1) % 2])
                patched = verify.clean_source(str(out.get("patched_source") or ""))
                if patched.strip() == source.strip():
                    raise verify.PatchError("the patched file is identical to the vulnerable file")
                problem = verify.compile_check(patched)
                if problem:
                    raise verify.PatchError(problem)
            except (ModelError, verify.PatchError, json.JSONDecodeError) as exc:
                attempts.append({"attempt": attempt, "ok": False, "reason": str(exc)[:300]})
                feedback = str(exc)
                self._set_repair(rel_file, source, None, out, attempts, repair_tier.label)
                self.trace("Horizon 2 (Repair Tier)", "Decide", f"Candidate fix {attempt}/{MAX_REPAIR_ATTEMPTS} rejected before testing",
                           str(exc)[:400])
                continue
            diff = verify.unified_diff(rel_file, source, patched)
            self._set_repair(rel_file, source, patched, out, attempts, repair_tier.label, diff, rmeta)
            self.trace("Horizon 2 (Repair Tier)", "Decide", f"Candidate fix {attempt}/{MAX_REPAIR_ATTEMPTS} written",
                       f"{out.get('root_cause', '')[:300]} Invariant: {out.get('invariant', '')[:200]}",
                       {"name": f"{repair_tier.model}.repair", "input": {"file": rel_file},
                        "output": json.dumps({"lines_changed": sum(1 for l in diff.splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---")), "latency_ms": rmeta["latency_ms"]})})
            self.update(phase="sandbox_testing")
            report = verify.verify_repair(runner, work / f"attempt-{attempt}", release, rel_file, patched,
                                          cases, out.get("test_code") or "")
            attempts.append({"attempt": attempt, "ok": report["ok"], "reason": report["reason"][:400]})
            self._set_sandbox(report, fuzz_cases)
            with self.lock:
                self.state["repair"]["attempts"] = attempts
            v2 = report.get("v2", {}).get("counts", {})
            self.trace("Horizon 2 (Repair Tier)", "Act",
                       "Sandbox verdict: PASS" if report["ok"] else f"Sandbox verdict: FAIL (candidate {attempt})",
                       ("The exploit seen in production still works on the old code and is neutralised on the patch, "
                        f"with every red-team variant and unchanged legitimate traffic: {v2.get('passed', 0)} checks passed, "
                        f"{v2.get('failed', 0)} failed, in a container with no network. Model-written test: "
                        f"{'passed' if report.get('model_test_passed') else 'did not pass (advisory only)'}.")
                       if report["ok"] else report["reason"][:500],
                       {"name": "sandbox.pytest", "input": {"network": "none", "attempt": attempt},
                        "output": json.dumps({"reproduces_on_v1": report.get("reproduces_on_v1"), **v2})})
            if report["ok"]:
                break
            feedback = report["reason"] + "\n" + report.get("v2", {}).get("output", "")[-1500:]
        if not report or not report["ok"]:
            self.trace("Runtime Orchestrator", "Decide", "No verified patch: production left untouched",
                       f"{MAX_REPAIR_ATTEMPTS} candidate fixes failed verification. The virtual patch stays on, "
                       "and the incident is escalated to a human with every attempt attached.")
            self.update(phase="escalated")
            return
        self.ship(rel_file, patched, release, t0, attack_params, path, benign, meta)

    def locate(self, release: Path, path: str) -> str:
        for f in sorted((release / "service" / "routes").glob("*.py")):
            if f'"{path}"' in f.read_text():
                return str(f.relative_to(release))
        return "service/main.py"

    def _set_repair(self, rel_file, before, after, out, attempts, label, diff=None, rmeta=None):
        with self.lock:
            self.state["repair"] = {"file": rel_file, "before": before, "after": after, "diff": diff,
                                    "rootCause": (out or {}).get("root_cause"), "cwe": (out or {}).get("cwe"),
                                    "testCode": (out or {}).get("test_code"), "attempts": list(attempts),
                                    "model": label, "latencyMs": (rmeta or {}).get("latency_ms")}
        self.emit()

    def _set_sandbox(self, report: dict, fuzz_cases: list[dict]) -> None:
        tests = report.get("v2", {}).get("per_test", [])
        outcome = {}
        for t in tests:
            if "test_attack_is_neutralised" in t["name"]:
                case_id = t["name"].split("[", 1)[-1].rstrip("]")
                outcome[case_id] = t["outcome"]
        with self.lock:
            self.state["sandbox"] = {"ok": report["ok"], "reason": report["reason"],
                                     "reproducesOnV1": report.get("reproduces_on_v1"),
                                     "modelTestPassed": report.get("model_test_passed"),
                                     "v1": report.get("v1"), "v2": report.get("v2")}
            for f in self.state["fuzz"]:
                if f["id"] in outcome:
                    f["status"] = "blocked" if outcome[f["id"]] == "passed" else "bypassed"
            judged = [f for f in self.state["fuzz"] if f["status"] in ("blocked", "bypassed")]
            if judged:
                self.state["metrics"]["fuzzPassRate"] = round(
                    100 * sum(f["status"] == "blocked" for f in judged) / len(judged))
        self.emit()

    # ------------------------------------------------------------- ship

    def ship(self, rel_file, patched, release, t0, attack_params, path, benign, meta) -> None:
        self.update(phase="hot_swapping")
        self.version_counter += 1
        version = f"v{self.version_counter}.0.0"
        new_dir = infra.release_dir(version)
        if new_dir.exists():
            import shutil
            shutil.rmtree(new_dir)
        import shutil
        shutil.copytree(release, new_dir)
        (new_dir / rel_file).write_text(patched)
        image = infra.build_image(version, new_dir)
        label = f"{version}-immune"
        new_name = infra.start_release(version, image, label)
        if not infra.wait_healthy(new_name):
            self.trace("Runtime Orchestrator", "Act", "New container never became healthy; aborted",
                       f"{new_name} failed its health check. Traffic never moved.")
            infra.remove_container(new_name)
            self.update(phase="escalated")
            return
        old_name = self.state["container"]["active"]
        self.trace("Runtime Orchestrator", "Act", f"Built and started {new_name} ({label})",
                   f"Image {image} built from release {version}; health check passed. Starting a weighted canary.",
                   {"name": "docker.build+run", "input": {"image": image}, "output": new_name})

        steps = [(90, 10), (50, 50), (0, 100)]
        probes = [verify.build_uri(path, p) for p in benign]
        with self.lock:
            self.state["canary"] = {"status": "probation_monitoring", "probesOk": 0, "probesFailed": 0,
                                    "step": None, "p99LatencyMs": 0, "circuitBreakerTripped": False}
        latencies: list[float] = []
        for old_w, new_w in steps:
            infra.nginx_apply("upstream.conf", infra.upstream_conf({old_name: old_w, new_name: new_w}))
            with self.lock:
                self.state["trafficSplit"] = {"old": old_w, "new": new_w}
                self.state["canary"]["step"] = f"{new_w}% to {label}"
            self.emit()
            failed = 0
            for _ in range(int(os.getenv("CANARY_PROBES_PER_STEP", "8"))):
                for uri in probes:
                    started = time.perf_counter()
                    try:
                        r = httpx.get(PROXY_URL + uri, timeout=4)
                        good = r.status_code == 200 and (time.perf_counter() - started) < 1.5
                    except Exception:
                        good = False
                    latencies.append((time.perf_counter() - started) * 1000)
                    with self.lock:
                        self.state["canary"]["probesOk" if good else "probesFailed"] += 1
                    failed += 0 if good else 1
                time.sleep(0.25)
            p99 = sorted(latencies)[int(len(latencies) * 0.99) - 1] if latencies else 0
            with self.lock:
                self.state["canary"]["p99LatencyMs"] = round(p99, 1)
            self.emit()
            if failed:
                self.rollback(old_name, new_name, f"{failed} canary probes failed at {new_w}% traffic")
                return
        with self.lock:
            prev_version = self.state["container"]["version"]
            self.state["container"] = {"active": new_name, "version": label, "previous": old_name}
            self.state["canary"]["status"] = "healthy_promoted"
        self.active_release = version
        # Code is now immune: the temporary edge rule is no longer needed.
        if self.state["virtualPatch"]["active"]:
            infra.nginx_apply("dynamic_rules.conf", infra.EMPTY_RULES)
            with self.lock:
                self.state["virtualPatch"]["active"] = False
        healed = time.time() - t0
        with self.lock:
            m = self.state["metrics"]
            m["remediated"] += 1
            m["timeToHealS"] = round(healed, 1)
            self.state["history"].append({"incident": self.state["incident"]["id"], "scenario": self.state["scenario"],
                                          "from": prev_version, "to": label, "healedS": round(healed, 1),
                                          "containS": m["timeToContainS"]})
        self.trace("Runtime Orchestrator", "Act", f"Promoted {label}: 100% of traffic, zero failed probes",
                   f"Traffic moved 10% -> 50% -> 100% with {self.state['canary']['probesOk']} legitimate probes and "
                   f"no failures (p99 {self.state['canary']['p99LatencyMs']} ms). {old_name} kept warm for instant "
                   f"rollback. Virtual patch retired. Healed {healed:.1f}s after detection.")
        self.update(phase="immune")
        # Prove it: replay the original exploit through the proxy.
        result = self.send(meta["scenario"], attack_params.get(meta["param"], ""), True)
        self.trace("Runtime Orchestrator", "Observe", f"Exploit replayed: HTTP {result['statusCode']} ({result['verdict']})",
                   "The original attack was sent again through the public proxy with no edge rule active; "
                   "the patched code handled it.")

    def rollback(self, old_name: str, new_name: str, why: str) -> None:
        infra.nginx_apply("upstream.conf", infra.upstream_conf({old_name: 1}))
        with self.lock:
            self.state["trafficSplit"] = {"old": 100, "new": 0}
            self.state["canary"].update(status="rollback_executed", circuitBreakerTripped=True)
        self.trace("Runtime Orchestrator", "Act", "Canary failed: automatic rollback",
                   f"{why}. All traffic returned to {old_name}; the virtual patch stays active. "
                   f"{new_name} is kept for inspection.")
        self.update(phase="rolled_back")

    def chaos_pause_new(self, seconds: float = 6.0) -> str:
        """Fault injection for the canary: freeze the newest container during rollout."""
        with self.lock:
            if self.state["phase"] != "hot_swapping":
                raise RuntimeError("chaos only works while a canary rollout is running")
        names = [c.name for c in infra.docker_client.containers.list(filters={"label": infra.MANAGED_LABEL + "=release"})]
        if not names:
            raise RuntimeError("no new container to pause")
        target = sorted(names)[-1]
        threading.Thread(target=infra.pause, args=(target, seconds), daemon=True).start()
        return target
