# OODA-Aegis infrastructure

Everything the demo runs, as one Docker Compose project.

| Container | What it is |
|---|---|
| `aegis_proxy` | Nginx on **localhost:8080**, the public entry point. Loads `/etc/nginx/aegis/dynamic_rules.conf` (virtual patches) and `upstream.conf` (which release gets traffic, with weights). Both live on a shared volume the agent rewrites. |
| `aegis_app_blue` | DocVault v1.0.0, the vulnerable FastAPI service ([`app/`](app/)). Streams one telemetry record per request to Redis. |
| `aegis_redis` | Telemetry stream (`aegis:telemetry`) and fleet bus (`aegis:vaccine`, `aegis:vaccine:ack`). |
| `aegis_node_eu/ap/us` | Peer edge nodes ([`fleet/node.py`](fleet/node.py)): compile, self-test and acknowledge each vaccine. |
| `aegis_agent` | The OODA agent ([`agent/aegis/`](agent/aegis/)), API on port 8090 inside the network. Talks to the Docker socket to run sandboxes, build images and start releases. |
| `aegis_dashboard` | The React dashboard on **localhost:3030**; proxies `/api` to the agent. |
| `aegis_app_v2_0_0`, … | Patched releases the agent builds and starts at runtime (labelled `aegis.managed`). |

```bash
ollama pull llama3.2:3b && ollama pull llama3.1:8b   # models run natively on the host
docker compose up --build -d
docker logs -f aegis_agent
```

Try it from a terminal:

```bash
curl "http://localhost:8080/api/v1/documents/read?file=quarterly_report_2026.pdf"     # legitimate
curl "http://localhost:8080/api/v1/documents/read?file=../../../../etc/passwd"        # leaks, then gets contained
curl "http://localhost:8080/api/v1/auth/customer-lookup?tenant=tenant-prod-99&email=x%27%20OR%20%271%27%3D%271"
curl "http://localhost:8080/api/v1/validator/email-or-domain?input=aaaaaaaaaaaaaaaaaaaaaaaaaaa%21"
```

The agent needs the Docker socket because it starts sandbox containers and new releases. Run this only on a machine you control. The sandbox containers have no network and a 512 MB memory cap.

Reset to the vulnerable release from the dashboard (**Reset**) or with `docker compose restart agent`.
