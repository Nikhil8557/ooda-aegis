"""Observe: decide whether one telemetry record shows a successful attack.

These are plain, explainable rules (data-loss signatures, tenant isolation,
latency and server errors). They only raise the alarm; the models do the
reasoning about what the attack is and how to fix it.
"""
from __future__ import annotations

import json
import re
from typing import Any

SIGNATURES = [
    ("unix_passwd_leak", re.compile(r"root:[x*]:0:0:")),
    ("secret_file_leak", re.compile(r"(DB_PASSWORD|JWT_SECRET|AWS_SECRET_ACCESS_KEY|BEGIN [A-Z ]*PRIVATE KEY)")),
    ("python_traceback", re.compile(r"Traceback \(most recent call last\)")),
]
LATENCY_LIMIT_MS = 1000.0


def tenant_leak(record: dict[str, Any]) -> bool:
    """A lookup scoped to one tenant must never return rows of another tenant."""
    tenant = (record.get("query") or {}).get("tenant")
    if not tenant:
        return False
    found = re.findall(r'"tenant_id"\s*:\s*"([^"]+)"', record.get("sample") or "")
    return any(t != tenant for t in found)


def findings(record: dict[str, Any]) -> list[str]:
    """Return the list of rules this record breaks (empty = looks fine)."""
    hits: list[str] = []
    sample = record.get("sample") or ""
    for name, pattern in SIGNATURES:
        if pattern.search(sample):
            hits.append(name)
    if tenant_leak(record):
        hits.append("cross_tenant_rows")
    if (record.get("duration_ms") or 0) > LATENCY_LIMIT_MS:
        hits.append("latency_spike")
    if (record.get("status") or 0) >= 500:
        hits.append("server_error")
    return hits


def response_is_safe(status: int, body: str, duration_ms: float, query: dict[str, str]) -> tuple[bool, list[str]]:
    """Same rules, applied to a response the agent or a test produced itself."""
    record = {"status": status, "sample": body[:4000], "duration_ms": duration_ms, "query": query}
    hits = findings(record)
    return (not hits, hits)


def short(record: dict[str, Any]) -> str:
    return json.dumps({k: record.get(k) for k in ("method", "path", "raw_query", "status", "duration_ms")})
