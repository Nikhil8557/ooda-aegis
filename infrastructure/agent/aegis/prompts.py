"""Prompts and JSON schemas for the four model calls in one defense cycle.

1. triage   (edge tier)   what is this attack?
2. vpatch   (edge tier)   a regex the proxy can drop on, right now
3. fuzz     (edge tier)   variants an attacker would try next
4. repair   (repair tier) the invariant, the whole patched file and a reproduction test
"""
from __future__ import annotations

TRIAGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["attack_class", "cwe", "malicious_fragment", "confidence", "summary"],
    "properties": {
        "attack_class": {"type": "string", "enum": ["path_traversal", "sql_injection", "redos", "other"]},
        "cwe": {"type": "string"},
        "malicious_fragment": {"type": "string"},
        "confidence": {"type": "number"},
        "summary": {"type": "string"},
    },
}

TRIAGE_SYSTEM = (
    "You are the edge triage model of OODA-Aegis, an autonomous defense agent for a web API. "
    "You get one HTTP request that the telemetry rules flagged, plus what the rules saw. "
    "Classify the attack, give the CWE id (e.g. CWE-22), quote the exact malicious part of the "
    "query string, and write a one-sentence summary for the on-call engineer.\n"
    "What the rules mean: unix_passwd_leak / secret_file_leak = server files were returned "
    "(usually path traversal, CWE-22); cross_tenant_rows = a lookup returned other tenants' rows "
    "(usually SQL injection, CWE-89); latency_spike with no leaked data = the input made the server "
    "burn CPU (usually regular-expression denial of service, CWE-1333); server_error = unhandled "
    "exception. Look at the input itself to confirm."
)

VPATCH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["rule_type", "param", "substrings", "max_length", "min_run", "rationale"],
    "properties": {
        "rule_type": {"type": "string", "enum": ["contains", "max_length", "repeated_run"]},
        "param": {"type": "string"},
        "substrings": {"type": "array", "items": {"type": "string"}},
        "max_length": {"type": "integer"},
        "min_run": {"type": "integer"},
        "rationale": {"type": "string"},
    },
}

VPATCH_SYSTEM = (
    "You write emergency virtual patches for a reverse proxy, in a tiny rule language. "
    "The proxy compiles your rule into an encoding-aware regex itself, so write values in plain, "
    "decoded form (write ../ not %2e%2e%2f). Pick ONE rule_type:\n"
    "- contains: block when the parameter value contains any of `substrings`. Use the shortest "
    "fragments that capture the attack technique (the syntax the attack depends on), not the "
    "whole payload, and that never appear in normal values.\n"
    "- max_length: block when the parameter value is longer than `max_length` characters.\n"
    "- repeated_run: block when one character repeats `min_run` or more times in a row "
    "(useful against inputs crafted to make a regex backtrack).\n"
    "`param` is the query parameter the attack uses. Fill unused fields with [] or 0. The rule "
    "must block the attack and must not block any of the normal requests shown."
)

FUZZ_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["mutations"],
    "properties": {
        "mutations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["technique", "value"],
                "properties": {"technique": {"type": "string"}, "value": {"type": "string"}},
            },
        }
    },
}

FUZZ_SYSTEM = (
    "You are the red team half of OODA-Aegis. A patch is about to ship. Given the original "
    "attack value for one query parameter, write 6 different variants a real attacker would try "
    "to slip past a naive fix (encodings, case changes, alternative syntax, different targets). "
    "Each value is the decoded parameter value, not a full URL. Keep each under 80 characters."
)

REPAIR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["root_cause", "invariant", "cwe", "patched_source", "test_code"],
    "properties": {
        "root_cause": {"type": "string"},
        "invariant": {"type": "string"},
        "cwe": {"type": "string"},
        "patched_source": {"type": "string"},
        "test_code": {"type": "string"},
    },
}

REPAIR_SYSTEM = (
    "You are the program-repair model of OODA-Aegis. A FastAPI service was just exploited in "
    "production. You get the file that serves the attacked endpoint, the request that worked, "
    "and what leaked. Return:\n"
    "- root_cause: one or two sentences on why the exploit works.\n"
    "- invariant: the safety rule the fixed code must enforce for EVERY input, stated as a check "
    "on the final value the code uses (for example: the resolved absolute path must stay inside "
    "the base folder; user input must never be part of the SQL text; validation must finish in "
    "linear time). Then write code that enforces exactly that rule. Blocklists of bad strings are "
    "not acceptable fixes.\n"
    "- patched_source: the COMPLETE corrected file (every line, no line numbers, no markdown). "
    "Change as little as possible. Close the hole for the whole class of input, not just this "
    "payload. Keep the route, the function name, and the normal behaviour and response shape for "
    "legitimate input exactly as they are. Reject bad input with fastapi.HTTPException (400 or "
    "403). Only use the Python standard library and FastAPI, and import every name you use.\n"
    "- test_code: a pytest file that reproduces the exploit. It must import `from "
    "fastapi.testclient import TestClient` and `from service.main import app`, create "
    "`client = TestClient(app)`, send the original attack and assert that nothing sensitive comes back (check the response "
    "body for the leaked data rather than one exact status code, since 400, 403 and 404 can all "
    "be correct), and assert that one legitimate request still returns 200."
)


def triage_user(record: dict, hits: list[str]) -> str:
    return (f"Request: {record.get('method')} {record.get('path')}?{record.get('raw_query')}\n"
            f"Status: {record.get('status')}, latency: {record.get('duration_ms')} ms\n"
            f"Rules that fired: {', '.join(hits)}\n"
            f"First bytes of the response: {(record.get('sample') or '')[:300]}")


def vpatch_user(record: dict, triage: dict, benign_uris: list[str], feedback: str = "") -> str:
    text = (f"Attack URI: {record.get('path')}?{record.get('raw_query')}\n"
            f"Decoded query parameters: {record.get('query')}\n"
            f"Attack class: {triage.get('attack_class')} ({triage.get('cwe')}), malicious part: "
            f"{triage.get('malicious_fragment')}\n"
            "Normal traffic that must NOT match:\n" + "\n".join(benign_uris[:8]))
    if feedback:
        text += f"\n\nYour previous regex was rejected: {feedback}\nWrite a better one."
    return text


def fuzz_user(param: str, value: str, triage: dict) -> str:
    return (f"Parameter: {param}\nOriginal attack value: {value}\n"
            f"Attack class: {triage.get('attack_class')} ({triage.get('cwe')})")


def repair_user(file_path: str, source: str, record: dict, triage: dict, hits: list[str],
                feedback: str = "") -> str:
    numbered = "\n".join(f"{i + 1:3d}| {line}" for i, line in enumerate(source.splitlines()))
    text = (f"File: {file_path} (line numbers are for reference only; never copy them into the patched file)\n"
            f"```\n{numbered}\n```\n"
            f"Exploit request: {record.get('method')} {record.get('path')}?{record.get('raw_query')}\n"
            f"Decoded parameters: {record.get('query')}\n"
            f"What the telemetry saw: {', '.join(hits)}; status {record.get('status')}, "
            f"{record.get('duration_ms')} ms\n"
            f"Response sample: {(record.get('sample') or '')[:300]}\n"
            f"Triage: {triage.get('summary')}")
    if feedback:
        text += ("\n\nYour previous attempt failed verification. Fix it. What went wrong:\n" + feedback[-2500:])
    return text
