<div align="center">

# OODA-Aegis

### When an exploit lands, contain it in seconds and ship a proven fix in about a minute.

An autonomous defense agent that watches a live web service, blocks an attack at the proxy the moment it works, then writes, tests and rolls out a code fix, all on Meta's open-weight models and with no human in the loop.

[![Llama 3.2 3B](https://img.shields.io/badge/Meta-Llama%203.2%203B-253745?style=flat-square&labelColor=06141B)](#how-metas-models-are-used)
[![Llama 3.1 8B](https://img.shields.io/badge/Meta-Llama%203.1%208B-253745?style=flat-square&labelColor=06141B)](#how-metas-models-are-used)
[![Muse Glimmer 30B](https://img.shields.io/badge/Meta-Muse%20Glimmer%2030B-4A5C6A?style=flat-square&labelColor=06141B)](#how-metas-models-are-used)
[![Track](https://img.shields.io/badge/Indie%20track-Build%20for%20Your%20World-9BA8AB?style=flat-square&labelColor=06141B)](#built-during-the-hackathon)
[![License: MIT](https://img.shields.io/badge/license-MIT-CCD0CF?style=flat-square&labelColor=06141B)](LICENSE)

**[Film](https://nikhil8557.github.io/ooda-aegis/#demo)** · **[Website and recorded runs](https://nikhil8557.github.io/ooda-aegis/)** · **[Benchmark](#results)** · **[Run it yourself](#run-it-yourself)**

</div>

---

## Built during the hackathon

OODA-Aegis was built by **Nikhil Kumar** for the **Meta Global AI Developer Hackathon 2026** (26 October to 4 November), **Indie track**, theme **Build for Your World**. The first version was a dashboard prototype; the working agent, the real vulnerable service, the sandbox, the rollout, the Glimmer benchmark and the website were built in the final days of the hackathon. The [commit history](https://github.com/Nikhil8557/ooda-aegis/commits/main) shows the dates.

## For judges: a short tour

| | What to open | What you will see |
|---|---|---|
| 0 | **[The film](https://nikhil8557.github.io/ooda-aegis/#demo)** | 2:50. A short ninja story explains the problem and the fix, and every demo shot is the real dashboard replaying a recorded live run |
| 1 | **[The website](https://nikhil8557.github.io/ooda-aegis/)** and its **[dashboard](https://nikhil8557.github.io/ooda-aegis/app/?replay)** | The real dashboard replaying three recorded live runs frame by frame: path traversal healed in 42.6 s, SQL injection healed in 46.3 s, and a ReDoS run where no candidate fix passed the gate, so the agent changed nothing and escalated. Press **Play** |
| 2 | **[Results](#results)** | How often each Meta model contains and heals each attack, judged by the same verifier |
| 3 | **[Run it yourself](#run-it-yourself)** | `ollama pull` two models, `docker compose up`, then attack it from the dashboard |

---

## The problem

Every on-call engineer knows the 3 a.m. page: an exploit is working in production, data is leaving, and the fix has to be written, reviewed, tested and deployed by a tired human. The industry average time to remediate a critical vulnerability is measured in days; even the emergency path (a WAF rule, a hotfix, a deploy) takes hours. During those hours the attack keeps working.

Two things make automation hard:

- **A blocking rule is not a fix.** Rules match strings; attackers change strings. A rule that stops `../../etc/passwd` usually misses `....//....//etc/passwd`.
- **A model-written fix cannot be trusted blindly.** Language models write plausible patches that miss variants, break legitimate users, or "fix" a test instead of the bug.

## What OODA-Aegis does

It runs an **Observe → Orient → Decide → Act** loop on two horizons, and never lets a model's output reach production without proof.

```
 attacker ──► Nginx proxy ──► DocVault service (v1, vulnerable)
                 ▲     │ telemetry (Redis)
   virtual patch │     ▼
          ┌──────┴──────────────────────────────────────────────┐
          │ OODA-Aegis agent                                     │
          │  Observe   rules flag leaked files, cross-tenant     │
          │            rows, stalls, crashes                     │
          │  Horizon 1 edge model: triage + rule in a safe       │
          │  (secs)    rule language → compiled, validated,      │
          │            nginx -t, graceful reload, fleet vaccine  │
          │  Red team  model + mutation rules invent bypasses    │
          │  Horizon 2 repair model: invariant + patched handler │
          │  (~1 min)  → no-network sandbox proof, up to 6 tries │
          │  Ship      docker build → 10% → 50% → 100% canary     │
          │            → auto rollback on any failed probe       │
          └──────────────────────────────────────────────────────┘
```

1. **Observe.** Every response from the service is streamed to the agent. Plain, explainable rules raise the alarm: `/etc/passwd` or secrets in a response, rows from another tenant, a request that took seconds, a crash.
2. **Horizon 1: contain in seconds.** The edge model classifies the attack and writes a virtual patch in a **small safe rule language** (`contains`, `max_length`, `repeated_run`). The agent compiles it into an encoding-aware regex (so `../` also matches `%2e%2e%2f`), proves it matches the attack and none of the recorded legitimate requests, runs `nginx -t` and reloads gracefully. A small model cannot produce a broken or catastrophic regex this way. The rule is then broadcast to three peer edge nodes over Redis; each compiles it, self-tests it and acknowledges.
3. **Red team.** The edge model invents bypass variants; deterministic mutation rules add more (encodings, nested `....//`, `UNION SELECT`, longer backtracking runs). The dashboard shows how many the edge rule would catch. It is never all of them, which is the reason to fix the code.
4. **Horizon 2: a proven fix.** The agent finds the handler for the attacked route and gives it to the repair model (with line numbers), along with the exploit and what leaked. The model first states the **invariant** the code must enforce (for example "only files inside the documents folder may be opened"), then returns the whole patched file, plus a reproduction test of its own. The agent then builds the gate itself and runs it in a throwaway Docker container with **no network**:
   - the **exploit seen in production must still work on the old code** (so the test really reproduces the bug),
   - and on the patched code that exploit, **every red-team variant** (each must come back safe within 2.5 s), the service's own tests and the **recorded legitimate requests** (which must return exactly what they did before) must all pass.
   The model's own test runs too, but it is advisory: it cannot approve a patch. Up to six candidates are tried (alternating temperature 0.2 and 0.8), and each failure is fed back. If nothing passes, production is left untouched, the virtual patch stays on and the incident is escalated.
5. **Ship without downtime.** The patched image is built and started, then weighted Nginx upstreams move traffic **10% → 50% → 100%** with legitimate canary probes at each step. One failed or slow probe rolls traffic back. After promotion the virtual patch is retired and the original exploit is replayed through the proxy to prove the code is now immune. The previous container stays warm for instant rollback. You can test this: the dashboard has a button that freezes the new container mid-rollout, and the agent rolls back on its own.

## How Meta's models are used

| Model | Role | Where it runs |
|---|---|---|
| **Llama 3.2 3B** | Edge tier: triage, virtual-patch rule, red-team variants. Small and fast enough to answer in about 2 seconds on a laptop | Meta open weights via Ollama, on the laptop |
| **Llama 3.1 8B** | Repair tier in the live demo: root cause, minimal patch and reproduction test | Meta open weights via Ollama, on the laptop |
| **Muse Glimmer 30B** | Both tiers in the benchmark, judged by the same verifier. Plug-in for the live agent with `GLIMMER_BASE_URL` | Meta's official 4-bit GGUF in llama.cpp on **two free Kaggle T4 GPUs** ([`benchmark/kaggle/`](benchmark/kaggle/)) |
| **Muse Spark 1.3** | Repair tier when `MODEL_API_KEY` is set | Meta Model API (`https://api.meta.ai/v1`) |

**Why Meta's open weights matter here.** A defense agent reads your source code, your traffic and your leaked data. Sending that to a third-party API in the middle of an incident is often not allowed. With open weights, the whole loop runs inside the operator's own network, on a laptop or a single GPU node, with no keys and no data leaving.

**Why two tiers.** Containment has to be fast and cannot be allowed to break the proxy, so a small model fills in a constrained rule. Repair needs to read code and reason about a whole class of inputs, so it gets a larger model, more time and a strict proof.

## Results

Every number below comes from [`benchmark/results/`](benchmark/results/) and can be re-run. Each trial really attacks the vulnerable code first, then runs the same four model calls as the live agent (triage, virtual patch, red team, repair) and judges the answers with the same sandbox gate. Three trials per attack per setup.

| Models (edge + repair) | Attack | Triage right | Virtual patch validated | Edge rule catches variants | **Verified fix** | Candidates needed (median) | Contain (median) | Heal (median) |
|---|---|---|---|---|---|---|---|---|
| Llama 3.2 3B + Llama 3.1 8B | Path traversal (CWE-22) | 3/3 | 3/3 | 77% | **3/3** | 3 | 8.7 s | 269.4 s |
| Llama 3.2 3B + Llama 3.1 8B | SQL injection (CWE-89) | 3/3 | 2/3 | 29% | **3/3** | 1 | 9.7 s | 79.9 s |
| Llama 3.2 3B + Llama 3.1 8B | ReDoS (CWE-1333) | 0/3 | 2/3 | 32% | **3/3** | 1 | 7.2 s | 125.0 s |
| Muse Glimmer 30B | Path traversal (CWE-22) | 3/3 | 3/3 | 59% | **3/3** | 1 | 68.2 s | 339.1 s |
| Muse Glimmer 30B | SQL injection (CWE-89) | 3/3 | 3/3 | 53% | **3/3** | 1 | 66.1 s | 321.0 s |
| Muse Glimmer 30B | ReDoS (CWE-1333) | 3/3 | 3/3 | 81% | **3/3** | 1 | 68.2 s | 394.0 s |

**What this shows**

1. **Both Meta setups healed all 9 attacks with a verified fix.** Muse Glimmer 30B got every one on the first candidate. Llama 3.1 8B needed 17 candidates for 9 fixes (6 on the first try, up to 5 on the hardest): the verifier loop is what makes an 8B model on a laptop usable.
2. **The model never grades its own work, and that matters.** Llama's own reproduction test passed on **0 of its 9** verified fixes (for example, it asserted status 400 where the correct fix returned 403, or a safe 200 with no rows). Had the model's test been the gate, Llama would score 0/9. In one development run it did the opposite: its test passed while `/etc/passwd` still leaked. Glimmer's tests were right 8 times out of 9.
3. **Blocking rules buy time but are not fixes.** The validated edge rules caught only 29 to 81% of the red-team variants. The code fix had to neutralise all of them.
4. **Speed versus judgement.** On the laptop, Llama 3.2 3B contains an attack in about 7 to 10 s, while Glimmer on two free T4 GPUs takes about a minute (it reasons first). But the 3B model misread the ReDoS attack in every trial, and its rule failed validation twice; Glimmer was right 9/9 on both. With a faster Glimmer host, the same agent gets both.
5. **Live runs on the laptop.** With Llama 3.1 8B, path traversal and SQL injection healed on the first candidate in every live run. ReDoS, the hardest bug (the fix must stay fast and accept exactly the same emails), healed in one of three live runs and escalated safely in the other two; Glimmer healed it 3/3 in the benchmark.
6. **A single live run is faster.** The benchmark runs three trials at once on one laptop GPU. A single live run on the same laptop contained the path-traversal leak in **5.3 s** and shipped the verified fix in **42.6 s**, with zero failed canary probes.

**How it was run.** Llama: Ollama on a 16 GB MacBook (Apple M5), `python benchmark/run_benchmark.py --trials 3`. Glimmer: Meta's official `Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf` in llama.cpp on two Kaggle T4 GPUs (about 13 tokens/s), built by [`benchmark/kaggle/make_kernel.py`](benchmark/kaggle/make_kernel.py), with `Reasoning strength: low` for the edge tier and `medium` for repair. Every fix, rule and failure reason is in the JSONL files.

## Run it yourself

Needs Docker Desktop and [Ollama](https://ollama.com). About 7 GB of models. Tested on a 16 GB MacBook (Apple M5).

```bash
ollama pull llama3.2:3b
ollama pull llama3.1:8b
ollama serve                      # if it is not already running
cd infrastructure
docker compose up --build -d
```

Open **http://localhost:3030**, pick an attack and press **Fire attack**. Then just watch: nobody presses a "defend" button.

You can also attack it from a terminal; the public API is on port 8080:

```bash
curl "http://localhost:8080/api/v1/documents/read?file=../../../../etc/passwd"
```

Press **Reset** in the dashboard to put the vulnerable release back.

**Options** (copy `.env.example` to `.env`): point `GLIMMER_BASE_URL` at a Glimmer server to use Glimmer for both tiers, or set `MODEL_API_KEY` to use Muse Spark 1.3 for repair.

**Benchmark.** `python benchmark/run_benchmark.py --trials 3` runs the four model tasks against the three vulnerabilities with the local Llama models. `python benchmark/kaggle/make_kernel.py` builds the Kaggle job that does the same with Muse Glimmer 30B.

**Recorded runs.** Every live run is saved by the agent. `python tools/export_replay.py latest <name> "<title>"` turns the newest one into a replay for the website.

## What is real and what is not

- **Real:** the vulnerable FastAPI service and its three bugs, the leaks, Nginx, Redis, the three peer containers, the Docker sandbox, the image builds, the weighted traffic shifting, the rollback, and every model call. The website replays runs recorded from the live system; it does not simulate anything.
- **Not real:** the customer records and the "secrets" in the service are fake demo data. The three vulnerabilities were written for this demo (they are common, textbook bugs, not CVEs in someone's product). The fleet is three containers on one machine, not three regions.
- **Limits:** the legitimate-traffic check compares only the recorded legitimate requests, so a fix can still change behaviour on inputs nobody recorded (for example, a ReDoS fix that accepts a slightly different set of unusual email addresses). Detection uses rules for the three classes of harm shown here, so an attack that leaks nothing those rules recognise will not trigger the loop. The repair model only edits the handler file it is given. Small local models do not always produce a passing fix; when they do not, the agent says so and leaves production alone.

## Repository

```
infrastructure/
  app/            DocVault: the vulnerable FastAPI service, its tests and recorded legitimate traffic
  agent/aegis/    the agent: llm.py (models), detect.py, prompts.py, verify.py (sandbox proof),
                  infra.py (Docker, Nginx, Redis), engine.py (the OODA loop), server.py (API + live stream)
  proxy/          Nginx config; the agent rewrites the virtual-patch and upstream files at runtime
  fleet/          a peer edge node that receives vaccines
  dashboard/      container that serves the React dashboard
src/              the React dashboard (live mode, replay mode, ?autoplay for embedding)
public/replays/   recorded live runs shown on the website
benchmark/        run_benchmark.py, kaggle/ (Muse Glimmer job), results/
tools/            demo_run.py (scripted attacks), export_replay.py, build_site.sh
site/             the home page (three.js scroll scene), source for docs/
docs/             the built website for GitHub Pages: home page, app/ (dashboard), assets/ (film)
video/            the film: STORYBOARD.md, CHARACTERS.md, SCORE.md, scene.js, music.py, record.mjs
```

**Rebuilding the website and film.** `sh tools/build_site.sh` builds the dashboard and copies everything into `docs/`. For the film, serve the repo root (`python3 -m http.server 8770`), then run `node video/record.mjs` and `python3 video/music.py`, and join them with the `ffmpeg` line at the top of `video/record.mjs`.

## Credits

Built by **Nikhil Kumar**. Models: Meta Llama 3.2, Llama 3.1 and Muse Glimmer under Meta's licences (not redistributed). Uses FastAPI, Nginx, Redis, Docker, Ollama, llama.cpp, React, Vite and Tailwind. MIT licence.
