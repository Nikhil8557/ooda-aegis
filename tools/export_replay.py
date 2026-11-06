"""Turn a recorded live run into a replay for the website.

The agent writes every state change of a run to /work/runs/run-*.jsonl in the
aegis_work Docker volume. This copies one out, drops frames that only changed
the CPU gauge, trims long sandbox logs, and registers it in
public/replays/index.json.

  python tools/export_replay.py run-20261104-111500.jsonl path_traversal "Path traversal, healed by Llama 3.1 8B"
  python tools/export_replay.py latest ...   # newest run in the volume
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "replays"


def read_run(name: str) -> list[str]:
    if name == "latest":
        listing = subprocess.run(["docker", "exec", "aegis_agent", "sh", "-c", "ls -1t /work/runs/run-*.jsonl | head -1"],
                                 capture_output=True, text=True, check=True).stdout.strip()
        name = Path(listing).name
    text = subprocess.run(["docker", "exec", "aegis_agent", "cat", f"/work/runs/{name}"],
                          capture_output=True, text=True, check=True).stdout
    return [line for line in text.splitlines() if line.strip()]


def slim(state: dict) -> dict:
    for phase in ("v1", "v2"):
        sb = (state.get("sandbox") or {}).get(phase)
        if sb:
            sb["output"] = sb.get("output", "")[-1500:]
    return state


def main() -> None:
    run, slug, title = sys.argv[1], sys.argv[2], sys.argv[3]
    frames, last_key = [], None
    for line in read_run(run):
        frame = json.loads(line)
        state = slim(frame["state"])
        key = json.dumps({k: v for k, v in state.items() if k != "metrics"}, sort_keys=True)
        key += json.dumps({k: v for k, v in state["metrics"].items() if k not in ("cpu", "memoryMb")}, sort_keys=True)
        if key == last_key:
            continue
        last_key = key
        frames.append({"t": frame["t"], "state": state})
    # Start the clock at the first request so the replay opens on the attack.
    first = next((i for i, f in enumerate(frames) if f["state"]["logs"]), 0)
    frames = frames[max(0, first - 1):]
    t0 = frames[0]["t"]
    for f in frames:
        f["t"] = round(f["t"] - t0, 3)
    OUT.mkdir(parents=True, exist_ok=True)
    file = f"{slug}.jsonl"
    (OUT / file).write_text("\n".join(json.dumps(f, separators=(",", ":")) for f in frames) + "\n")
    index_path = OUT / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else []
    index = [i for i in index if i["file"] != file] + [{"name": slug, "title": title, "file": file}]
    index_path.write_text(json.dumps(index, indent=1) + "\n")
    size = (OUT / file).stat().st_size // 1024
    print(f"{file}: {len(frames)} frames, {frames[-1]['t']:.0f}s, {size} KB")


if __name__ == "__main__":
    main()
