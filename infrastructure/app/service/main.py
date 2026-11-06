"""DocVault: the target microservice that OODA-Aegis defends.

It ships three deliberately vulnerable endpoints (one per scenario) and a
small ASGI middleware that streams one telemetry record per request to Redis.
The agent watches that stream; the service itself knows nothing about the
agent and never decides whether a request was an attack.
"""
import json
import os
import time
import urllib.parse

from fastapi import FastAPI

from service.routes import customers, documents, validator

VERSION = os.getenv("CONTAINER_VERSION", "v1.0.0-vulnerable")
CONTAINER = os.getenv("CONTAINER_NAME", "aegis_app_blue")
TELEMETRY_CHANNEL = "aegis:telemetry"
SAMPLE_BYTES = 600

app = FastAPI(title="DocVault Microservice", version=VERSION)
app.include_router(documents.router)
app.include_router(customers.router)
app.include_router(validator.router)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "doc-vault", "version": VERSION, "container": CONTAINER}


_redis = None


def _publish(record: dict) -> None:
    """Best effort: telemetry must never break a request."""
    global _redis
    try:
        if _redis is None:
            import redis

            _redis = redis.Redis(host=os.getenv("REDIS_HOST", "redis_bus"), port=6379, socket_timeout=0.5)
        _redis.publish(TELEMETRY_CHANNEL, json.dumps(record))
    except Exception:
        _redis = None


class TelemetryMiddleware:
    """Pure ASGI middleware: records status, latency and a body sample."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == "/health":
            return await self.inner(scope, receive, send)

        started = time.perf_counter()
        status = {"code": 500}
        body = bytearray()
        size = {"n": 0}

        async def capture(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                size["n"] += len(chunk)
                if len(body) < SAMPLE_BYTES:
                    body.extend(chunk[: SAMPLE_BYTES - len(body)])
            await send(message)

        try:
            await self.inner(scope, receive, capture)
        finally:
            raw_query = scope.get("query_string", b"").decode("latin-1")
            _publish({
                "ts": time.time(),
                "container": CONTAINER,
                "version": VERSION,
                "method": scope["method"],
                "path": scope["path"],
                "raw_query": raw_query,
                "query": dict(urllib.parse.parse_qsl(raw_query, keep_blank_values=True)),
                "request_id": dict(scope.get("headers", [])).get(b"x-request-id", b"").decode() or None,
                "status": status["code"],
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "resp_bytes": size["n"],
                "sample": body.decode("utf-8", errors="replace"),
            })


app = TelemetryMiddleware(app)
