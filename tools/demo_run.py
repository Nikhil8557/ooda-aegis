"""Drive one live defense cycle through the dashboard API, the same way a person
would from the attacker console, so the run can be recorded and replayed.

  python tools/demo_run.py path_traversal
Steps: reset, one legitimate request, the attack, then (while the agent works)
the attack again plus an encoded variant and a legitimate request, then wait
for the agent to finish and send one last legitimate request.
"""
import json
import sys
import time
import urllib.request

API = "http://localhost:3030/api"
PLAN = {
    "path_traversal": {"legit": "quarterly_report_2026.pdf", "attack": "../../../../etc/passwd",
                       "variant": "/etc/passwd"},
    "sqli": {"legit": "sarah.connor@cyberdyne.example", "attack": "x' OR '1'='1",
             "variant": "x' UNION SELECT id, tenant_id, full_name, email, role FROM customers --"},
    "redos": {"legit": "lead.architect@defense.example.com", "attack": "a" * 27 + "!",
              "variant": "b" * 27 + "!"},
}


def call(path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else b"",
                                 headers={"Content-Type": "application/json"}, method="POST" if body is not None or path != "/state" else "GET")
    if path == "/state":
        req = urllib.request.Request(API + path)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def send(scenario, value, malicious):
    r = call("/attack", {"scenario": scenario, "value": value, "malicious": malicious})
    print(f"  {'attack' if malicious else 'legit '} {value[:40]!r:44} -> {r['statusCode']} {r['verdict']}")
    return r


def main():
    scenario = sys.argv[1]
    p = PLAN[scenario]
    call("/reset", {})
    time.sleep(3)
    send(scenario, p["legit"], False)
    time.sleep(2)
    send(scenario, p["attack"], True)
    # wait for containment (or for the agent to move past it)
    for _ in range(120):
        s = call("/state")
        if s["virtualPatch"]["active"] or s["phase"] in ("code_repair", "sandbox_testing", "escalated"):
            break
        time.sleep(1)
    time.sleep(1.5)
    send(scenario, p["attack"], True)
    send(scenario, p["variant"], True)
    send(scenario, p["legit"], False)
    for _ in range(900):
        s = call("/state")
        if not s["busy"] and s["phase"] in ("immune", "escalated", "rolled_back", "degraded"):
            break
        time.sleep(2)
    time.sleep(2)
    send(scenario, p["legit"], False)
    send(scenario, p["variant"], True)
    s = call("/state")
    print(f"final phase {s['phase']}, contain {s['metrics']['timeToContainS']}s, heal {s['metrics']['timeToHealS']}s")


if __name__ == "__main__":
    main()
