---
name: infinite-ai-power-os-500
version: 1.1.0
description: Runnable starter runtime for quota-aware multi-provider AI routing, free-tier-first failover, persistent task state, and a 500-slot registry.
---

# INFINITE AI POWER OS 500

## Mission
Keep authorized AI tasks moving when a provider is unavailable, rate-limited, or out of quota by routing to another compatible provider. The code currently provides a Python router, a generic OpenAI-compatible adapter, a small authenticated HTTP service, SQLite task persistence, container scaffolding, and CI tests.

**Important truth:** the 500-slot registry is capacity only. Its 500 entries are unconfigured placeholders, not 500 connected AIs. Providers have finite independent quotas. Only providers configured with authorized credentials and successfully health-checked can be used. Never claim unlimited tokens or guaranteed uptime.

## Current implementation
- `router.py`: capability filtering, free-first ordering, bounded retry/failover, cooldowns, normalized provider errors, and task-state updates.
- `openai_compatible.py`: generic adapter for endpoints that explicitly document OpenAI-compatible chat completions.
- `sqlite_store.py`: durable single-node task state across process restarts.
- `service.py`: HTTP service with `GET /health` and bearer-token-protected `POST /v1/generate`; paid tier is blocked at the service layer.
- `Dockerfile` and `compose.yaml`: container deployment scaffold, restart policy, persistent local volume and health check.
- `.github/workflows/infinite-ai-power-os-tests.yml`: CI test and syntax-check workflow.
- `registry-capacity.json`: 500 unconfigured placeholder slots.
- `tests/test_router.py`: failover, paid-tier block, auth-disable and task-preservation tests.

## Run
From this directory:
```bash
python -m unittest discover -s tests -v
```

For local service use, copy `providers.example.json` to `providers.json`, add only verified provider metadata, set the required environment variables, and run:
```bash
python service.py
```

The service accepts `POST /v1/generate` with JSON such as:
```json
{"capability":"text","input":{"prompt":"Hello"}}
```
It requires `Authorization: Bearer <SERVICE_BEARER_TOKEN>`. `GET /health` is intentionally public for container health checks.

## Provider onboarding
1. Verify official API documentation, model availability, free-tier terms and regional restrictions.
2. Confirm the endpoint actually supports the OpenAI-compatible chat completions contract before selecting `adapter: openai_compatible`.
3. Add provider metadata to a local `providers.json`; include its documented `base_url`, model, capability, cost tier, and environment variable name.
4. Set the API key in the runtime environment/secret manager. Never commit credentials.
5. Run an authenticated minimal request and verify response format and quota behavior.
6. Only then mark it enabled. Do not treat unknown quota as unlimited.

The generic adapter is not universal: providers with different APIs need their own adapter. Never invent API endpoints or free quotas.

## Safety and cost rules
- Free tier only by default. The HTTP service currently sends requests with `allowed_cost_tiers=("free",)`.
- No quota bypass, account rotation, parallel quota multiplication, automatic paid upgrades or top-ups.
- 401/403 disables a provider pending credential repair; 402 blocks it; 429 triggers cooldown; quota exhaustion triggers failover.
- Unknown quota remains unknown.
- Do not log secrets, authorization headers or full sensitive prompts.
- Validate provider terms, data retention, privacy and model licensing before onboarding.

## Current deployment boundary
Docker Compose is a template; it does not deploy itself. SQLite is a single-node persistence layer, not a distributed queue. Production multi-replica operation needs a managed database/queue, encrypted secret storage, monitoring, backups, concurrency controls and a selected always-on host. Actual 24/7 operation and uptime must be measured after deployment. Cloud hosting may have costs; no paid service should be activated without operator approval.

## 500-slot status vocabulary
- `unconfigured`: placeholder slot only.
- `discovered`: provider identified but not connected.
- `configured`: metadata and credential reference supplied.
- `authenticated`: actual authentication check succeeded.
- `eligible`: compatible with this task and current policy/quota state.
- `rate_limited`, `quota_exhausted`, `quota_unknown`, `disabled`: operational states.

Never present a placeholder as a working provider.
