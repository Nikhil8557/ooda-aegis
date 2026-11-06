"""HTTP API for the dashboard: live state over Server-Sent Events, plus a few
controls (send a request, reset, fault injection, download a recorded run)."""
from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from . import infra
from .engine import RUN_LOG, Engine

engine = Engine()
api = FastAPI(title="OODA-Aegis agent")
api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AttackBody(BaseModel):
    scenario: str
    value: str
    malicious: bool = True


def telemetry_loop() -> None:
    while True:
        try:
            sub = infra.bus.pubsub(ignore_subscribe_messages=True)
            sub.subscribe("aegis:telemetry")
            for msg in sub.listen():
                try:
                    engine.on_telemetry(json.loads(msg["data"]))
                except Exception as exc:
                    print("telemetry error:", exc, flush=True)
        except Exception as exc:
            print("telemetry bus reconnecting:", exc, flush=True)
            time.sleep(1)


def stats_loop() -> None:
    while True:
        name = engine.state["container"]["active"]
        stats = infra.container_stats(name)
        with engine.lock:
            engine.state["metrics"]["cpu"] = stats["cpu"]
            engine.state["metrics"]["memoryMb"] = stats["memory_mb"]
        engine.emit()
        time.sleep(3)


@api.on_event("startup")
def startup() -> None:
    engine.boot()
    threading.Thread(target=telemetry_loop, daemon=True).start()
    threading.Thread(target=stats_loop, daemon=True).start()
    print("OODA-Aegis agent ready. Models:", json.dumps(engine.state["models"]), flush=True)


@api.get("/api/state")
def state():
    return engine.snapshot()


@api.get("/api/events")
async def events():
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    loop = asyncio.get_running_loop()

    def push(snap):
        def put():
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(snap)
        loop.call_soon_threadsafe(put)

    engine.listeners.append(push)

    async def stream():
        try:
            yield f"data: {json.dumps(engine.snapshot())}\n\n"
            while True:
                try:
                    snap = await asyncio.wait_for(queue.get(), timeout=15)
                    while not queue.empty():  # only the newest state matters
                        snap = queue.get_nowait()
                    yield f"data: {json.dumps(snap)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            engine.listeners.remove(push)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@api.post("/api/attack")
async def attack(body: AttackBody):
    return await asyncio.to_thread(engine.send, body.scenario, body.value, body.malicious)


@api.post("/api/reset")
async def reset():
    try:
        await asyncio.to_thread(engine.reset)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    return {"ok": True}


@api.post("/api/chaos")
async def chaos():
    try:
        return {"paused": await asyncio.to_thread(engine.chaos_pause_new)}
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))


@api.get("/api/runs")
def runs():
    return sorted((p.name for p in RUN_LOG.glob("run-*.jsonl")), reverse=True)


@api.get("/api/runs/{name}")
def run_file(name: str):
    path = RUN_LOG / Path(name).name
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)
