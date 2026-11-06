"""Summarise benchmark result files into one table (Markdown and JSON).

  python benchmark/summarize.py benchmark/results/llama_local.jsonl benchmark/results/glimmer_kaggle.jsonl
Writes benchmark/results/summary.md and summary.json.
"""
import json
import statistics
import sys
from pathlib import Path

NAMES = {"path_traversal": "Path traversal (CWE-22)", "sqli": "SQL injection (CWE-89)", "redos": "ReDoS (CWE-1333)"}


def label(row):
    e, r = row.get("edge_model", "?"), row.get("repair_model", "?")
    pretty = {"llama3.2:3b": "Llama 3.2 3B", "llama3.1:8b": "Llama 3.1 8B", "muse-glimmer-30b": "Muse Glimmer 30B"}
    e, r = pretty.get(e, e), pretty.get(r, r)
    return e if e == r else f"{e} + {r}"


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def main(paths):
    rows = []
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if "crash" not in r:
                    rows.append(r)
                else:
                    rows.append({**r, "repair_verified": False, "vpatch_ok": False, "triage_correct": False})
    groups = {}
    for r in rows:
        groups.setdefault((label(r), r["scenario"]), []).append(r)
    out = []
    for (model, sc), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], list(NAMES).index(kv[0][1]))):
        n = len(rs)
        out.append({
            "models": model, "scenario": sc, "trials": n,
            "triage_correct": sum(bool(r.get("triage_correct")) for r in rs),
            "vpatch_ok": sum(bool(r.get("vpatch_ok")) for r in rs),
            "edge_coverage": round(100 * sum(r.get("edge_covers", 0) for r in rs) / max(1, sum(r.get("fuzz_total", 0) for r in rs))),
            "verified": sum(bool(r.get("repair_verified")) for r in rs),
            "median_candidates": med([r.get("repair_attempts") for r in rs if r.get("repair_verified")]),
            "median_contain_s": med([r.get("contain_s") for r in rs]),
            "median_heal_s": med([r.get("heal_s") for r in rs]),
            "crashes": sum("crash" in r for r in rs),
        })
    md = ["| Models (edge + repair) | Attack | Triage right | Virtual patch validated | Edge rule catches variants | **Verified fix** | Candidates needed (median) | Contain (median) | Heal (median) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for o in out:
        md.append(f"| {o['models']} | {NAMES[o['scenario']]} | {o['triage_correct']}/{o['trials']} | {o['vpatch_ok']}/{o['trials']} | "
                  f"{o['edge_coverage']}% | **{o['verified']}/{o['trials']}** | {o['median_candidates'] or '–'} | "
                  f"{str(o['median_contain_s']) + ' s' if o['median_contain_s'] else '–'} | {str(o['median_heal_s']) + ' s' if o['median_heal_s'] else '–'} |")
    res = Path(paths[0]).parent
    (res / "summary.md").write_text("\n".join(md) + "\n")
    (res / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print("\n".join(md))
    totals = {}
    for o in out:
        t = totals.setdefault(o["models"], [0, 0])
        t[0] += o["verified"]
        t[1] += o["trials"]
    print({k: f"{a}/{b}" for k, (a, b) in totals.items()})


if __name__ == "__main__":
    main(sys.argv[1:])
