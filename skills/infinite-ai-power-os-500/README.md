# Infinite AI Power OS 500 — Router Runtime

Quota-aware AI routing foundation with automatic failover. This repository contains runnable infrastructure scaffolding, not 500 live provider integrations.

## Run locally
```bash
python -m unittest discover -s tests -v
```

To run the HTTP service, create a local `providers.json` from `providers.example.json`, configure verified provider entries, inject API keys through environment variables, and set `SERVICE_BEARER_TOKEN`. Then run:
```bash
python service.py
```

- `GET /health` — process health
- `POST /v1/generate` — authenticated generation endpoint; free tier only
- Request body: `{"capability":"text","input":{"prompt":"Hello"}}`

## Runtime components
- `router.py`: capability filtering, free-first routing, bounded retries, quota/rate-limit failover, cooldown and task states.
- `openai_compatible.py`: generic adapter for endpoints that explicitly document OpenAI-compatible chat completions.
- `sqlite_store.py`: durable single-node task state across process restarts.
- `service.py`: small bearer-token-protected HTTP API and health endpoint.
- `Dockerfile` + `compose.yaml`: container deployment scaffold with persistent SQLite volume and restart/healthcheck policy.
- `.github/workflows/infinite-ai-power-os-tests.yml`: automated unit-test and Python compile workflow.
- `registry-capacity.json`: 500 placeholder slots. These are not real connected providers.
- `providers.example.json`: safe sample provider record.
- `tests/test_router.py`: failover and spend-safety tests.

## Security and cost defaults
- Paid providers are blocked by the HTTP service; no automatic paid fallback.
- Provider credentials are read from environment variables, never stored in registry JSON.
- Unknown quota is not unlimited quota.
- Do not add providers until official API docs, free-tier terms, adapter compatibility and credentials are verified.
- Never use this router to bypass quotas, rate limits, account restrictions or provider terms.

## Important deployment limits
The SQLite store is suitable for a single-node starter deployment; it is not a distributed queue. Use a managed database/queue and encrypted secret manager for multiple replicas. Docker Compose is a deployment template, not a deployed cloud service. A real 24/7 uptime claim requires selecting a host, configuring secrets and storage, deploying, monitoring and testing recovery. No provider is live until it has been authenticated and health-checked.
