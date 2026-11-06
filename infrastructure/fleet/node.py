"""A peer edge node. It receives virtual-patch "vaccines" from the fleet bus,
compiles and self-tests each rule, keeps it, and acknowledges."""
import json
import os
import re
import time

import redis

NODE = os.getenv("NODE_ID", "node-x")
ZONE = os.getenv("NODE_ZONE", "unknown")
bus = redis.Redis(host=os.getenv("REDIS_HOST", "redis_bus"), port=6379, decode_responses=True)
rules = {}

while True:
    try:
        sub = bus.pubsub(ignore_subscribe_messages=True)
        sub.subscribe("aegis:vaccine")
        print(f"[{NODE}] listening for vaccines", flush=True)
        for msg in sub.listen():
            vaccine = json.loads(msg["data"])
            received = time.time()
            try:
                compiled = re.compile(vaccine["regex"], re.IGNORECASE)
                self_test = compiled.search("/healthcheck?probe=ok") is None
                rules[vaccine["rule_id"]] = compiled
            except re.error:
                self_test = False
            ack = {"vaccine_id": vaccine["vaccine_id"], "node": NODE, "zone": ZONE, "self_test": self_test,
                   "rules_loaded": len(rules), "latency_ms": round((received - vaccine["sent_at"]) * 1000, 1)}
            bus.publish("aegis:vaccine:ack", json.dumps(ack))
            print(f"[{NODE}] applied {vaccine['rule_id']} self_test={self_test}", flush=True)
    except redis.ConnectionError:
        time.sleep(1)
