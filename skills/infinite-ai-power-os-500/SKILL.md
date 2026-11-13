---
name: infinite-ai-power-os-500
version: 1.2.0
description: Starter runtime for quota-aware multi-provider AI routing, free-tier-first failover, persistent task state, media processing, scheduled jobs, social approval gates, and a 500-slot registry.
---

# INFINITE AI POWER OS 500

## Mission
Keep authorized AI tasks moving when a provider is unavailable, rate-limited, or out of quota by routing to another compatible provider. The code provides a Python router, a generic OpenAI-compatible adapter, an authenticated HTTP service, SQLite task persistence, container scaffolding, local media helpers, scheduling primitives, social draft approval, security helpers, observability primitives and a read-only dashboard starter.

**Important truth:** the 500-slot registry is capacity only. Its 500 entries are unconfigured placeholders, not 500 connected AIs. Providers have finite independent quotas. Only providers configured with authorized credentials and successfully health-checked can be used. Never claim unlimited tokens or guaranteed uptime.

## Current implementation
- `router.py`: capability filtering, free-first ordering, bounded retry/failover, cooldowns, normalized provider errors, and task-state updates.
- `openai_compatible.py`: generic adapter for endpoints that explicitly document OpenAI-compatible chat completions.
- `sqlite_store.py`: durable single-node task state across process restarts.
- `service.py`: HTTP service with `GET /health` and bearer-token-protected `POST /v1/generate`; paid tier is blocked at the service layer.
- `queue_worker.py`: polling worker that retries persisted queued tasks when eligible providers recover.
- `scheduler.py`: persistent scheduled-job storage and atomic single-node claiming. A production scheduler/worker daemon and distributed queue are not included.
- `media_pipeline.py`: safe FFmpeg subprocess wrappers for audio extraction, denoise/loudness normalization and video transcode.
- `social_gateway.py`: SQLite draft storage and exact-draft approval gate. Real platform publishers are not included.
- `security.py`: constant-time bearer-token validation and an in-memory sliding-window rate limiter.
- `observability.py`: redacted JSON event logging and process-local counters.
- `dashboard/index.html`: read-only status dashboard starter.
- `Dockerfile` and `compose.yaml`: container deployment scaffold, restart policy, persistent local volume and health check.
- `.github/workflows/infinite-ai-power-os-tests.yml`: CI test and syntax-check workflow.
- `registry-capacity.json`: 500 unconfigured placeholder slots.
- `tests/`: unit tests for routing and the added primitives.

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

## Media and voice engineering
Install FFmpeg separately and use `media_pipeline.py` for local media conversion, audio extraction, noise reduction using FFmpeg's `afftdn` filter, EQ filtering and loudness normalization. This is deterministic local post-processing, not AI voice cloning, TTS or neural source separation. Those require chosen providers, verified adapters and credentials. Keep input/output paths controlled by the operator; do not accept arbitrary shell commands or untrusted remote URLs.

## Social integrations
- `social-platforms.json` inventories YouTube, Instagram, Facebook Pages, Threads, TikTok, X, LinkedIn, Pinterest, Bluesky and Mastodon.
- `SOCIAL_INTEGRATIONS.md` defines the official OAuth, account verification, scope, draft approval, publishing, idempotency and analytics contract.
- `social_gateway.py` stores drafts and enforces explicit approval of the exact draft before calling a publisher adapter.
- All social entries remain disconnected by default. No platform-specific OAuth or publishing adapter is claimed as implemented until tested with a real authorized account.

## Scheduling, security and observability
- `scheduler.py` stores timezone-aware jobs in SQLite and atomically claims due jobs for a single-node worker. A crash-recovery lease/requeue loop and multi-node coordination remain to be implemented.
- `security.py` provides constant-time bearer comparison and an in-memory rate limiter; `service.py` now enforces both for generation requests. Distributed limits, TLS, WAF and production abuse controls remain.
- `observability.py` redacts common secret/prompt fields and offers process-local counters. Export to OpenTelemetry/Prometheus and configure alerts before production.
- `dashboard/index.html` is a read-only starter, not an admin control plane.

## Safety and cost rules
- Free tier only by default. The HTTP service currently sends requests with `allowed_cost_tiers=("free",)`.
- No quota bypass, account rotation, parallel quota multiplication, automatic paid upgrades or top-ups.
- 401/403 disables a provider pending credential repair; 402 blocks it; 429 triggers cooldown; quota exhaustion triggers failover.
- Unknown quota remains unknown.
- Do not log secrets, authorization headers or full sensitive prompts.
- Validate provider terms, data retention, privacy and model licensing before onboarding.
- Publishing requires approval of the exact draft and a verified platform adapter.

## Current deployment boundary
Docker Compose is a template; it does not deploy itself. SQLite is a single-node persistence layer, not a distributed queue. Production multi-replica operation needs a managed database/queue, encrypted secret storage, monitoring, backups, concurrency controls and a selected always-on host. Cloud hosting may have costs; no paid service should be activated without operator approval. Actual 24/7 operation and uptime must be measured after deployment.

## 500-slot status vocabulary
- `unconfigured`: placeholder slot only.
- `discovered`: provider identified but not connected.
- `configured`: metadata and credential reference supplied.
- `authenticated`: actual authentication check succeeded.
- `eligible`: compatible with this task and current policy/quota state.
- `rate_limited`, `quota_exhausted`, `quota_unknown`, `disabled`: operational states.

Never present a placeholder as a working provider. See `INTEGRATION_STATUS.md` for what is implemented and what still requires credentials, official adapters or infrastructure.
