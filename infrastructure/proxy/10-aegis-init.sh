#!/bin/sh
# Seed the shared conf volume on first start; OODA-Aegis rewrites these files at runtime.
for f in upstream.conf dynamic_rules.conf; do
  [ -f /etc/nginx/aegis/$f ] || cp /etc/nginx/aegis-templates/$f /etc/nginx/aegis/$f
done
# After `docker compose down` the volume can still point at a patched release the agent
# built and that no longer exists. Nginx refuses to start on an unknown host, so fall back
# to the original release (the agent resets to it on start-up anyway).
for host in $(sed -n 's/^[[:space:]]*server[[:space:]]\{1,\}\([^:;[:space:]]*\).*/\1/p' /etc/nginx/aegis/upstream.conf); do
  if ! getent hosts "$host" >/dev/null 2>&1 && ! nslookup "$host" >/dev/null 2>&1; then
    echo "aegis-init: $host not found, resetting upstream and rules to the original release"
    cp /etc/nginx/aegis-templates/upstream.conf /etc/nginx/aegis-templates/dynamic_rules.conf /etc/nginx/aegis/
    break
  fi
done
