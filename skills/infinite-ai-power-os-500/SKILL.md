---
name: infinite-ai-power-os-500
version: 1.0.0
description: Quota-aware multi-provider AI router with safe automatic failover, free-tier preference, task persistence, and a 500-slot provider registry.
---

# INFINITE AI POWER OS 500

## Mission

Keep authorized AI tasks moving when one provider is unavailable, rate-limited, or out of quota by routing to another compatible provider. This skill is designed for long-running workflows and 365×24×7 deployments.

**Important truth:** 500 registry slots do not create unlimited tokens. Providers have independent quotas, model capabilities, terms, and availability. Only providers actually configured with valid, authorized credentials can be used. Never claim a provider is connected or has quota without checking it.

## Non-negotiable safety and cost rules

1. Use only provider APIs, credentials, and accounts the operator is authorized to use.
2. Never bypass provider quotas, account restrictions, paywalls, identity checks, or rate limits. Fail over only to another provider under its own permitted quota.
3. Free-tier-first is the default. Paid models, paid fallback, paid retries, and automatic top-ups are **disabled** unless the operator explicitly enables a budget and spending cap.
4. Never ask users to paste secrets into chat. Read credentials from a secret manager or environment variables. Never log keys, authorization headers, or full secret-bearing request URLs.
5. Respect provider terms, model licenses, data-retention settings, privacy requirements, and request limits.
6. Do not run parallel requests to multiply quotas. Parallelize only independent work when each provider's limits and the task's cost/privacy rules allow it.
7. Do not claim 500 live integrations. Distinguish registry capacity, discovered providers, configured providers, authenticated providers, health-checked providers, and currently eligible providers.

## Core architecture

Implement these components as separate modules:

- **Provider Registry:** up to 500 provider/model entries; each entry has a unique ID, API base URL, adapter, supported models, capabilities, context limits, pricing/free-tier metadata, region, data policy, credential reference, status, and last health-check time.
- **Capability Matcher:** selects providers that can perform the requested task (text, code, reasoning, embeddings, image, audio, video, transcription, translation, or search). Do not send a task to an incompatible model.
- **Quota & Health Monitor:** tracks observed remaining quota when exposed by the provider, rate-limit headers, reset time, error codes, latency, availability, and last successful call. Mark unknown quota as unknown, not unlimited.
- **Policy & Budget Gate:** blocks providers outside the user's allowed spend, data, region, or licensing policy.
- **Router:** ranks eligible providers by capability fit, free-tier availability, health, latency, context window, reliability, and user-configured priority.
- **Failover Controller:** moves to the next eligible provider after a retryable failure or exhausted quota, with bounded retries and cooldowns.
- **Task Store / Queue:** persists task ID, input reference, state, attempt history, output, and idempotency key so a temporary outage does not lose work.
- **Observability:** records provider ID, model ID, request ID, latency, status, retry/failover reason, and estimated usage without recording secrets or sensitive prompt contents by default.

## Registry capacity and provider onboarding

Support up to 500 entries, but populate the registry only with verified providers. Do not invent provider names, free quotas, or API endpoints.

For each candidate provider:
1. Verify its official API documentation and current availability.
2. Confirm the specific model and task capability.
3. Verify free-tier eligibility, quota, reset behavior, and whether a payment method is required.
4. Implement or select a maintained adapter for its documented API.
5. Store credentials in a secret manager using a reference such as `PROVIDER_X_API_KEY`; do not put secrets in the registry file.
6. Run a minimal health check and a minimal capability test.
7. Mark it `configured` only after successful authentication; mark quota `unknown` unless verified.
8. Re-check documentation and pricing periodically. Disable stale or unverified entries.

## Routing and failover algorithm

For every task:

1. Normalize the task into a capability request and constraints.
2. Load providers that are configured, authenticated, policy-compliant, and capability-compatible.
3. Exclude providers in cooldown, known exhausted quota, unsupported region, or disallowed cost tier.
4. Rank free/zero-cost eligible providers first, then apply configured priority and health/latency scores.
5. Send the request with a stable idempotency key where supported.
6. On success, validate the response and persist the result.
7. On HTTP 429 or explicit quota exhaustion, parse `Retry-After` and reset headers if present, mark the provider rate-limited/exhausted, set a cooldown, and try the next eligible provider.
8. On transient 5xx, timeout, or connection failure, retry with exponential backoff and jitter within a strict attempt limit, then fail over.
9. On authentication/permission errors (401/403), disable that credential/provider pending operator repair; do not endlessly retry.
10. On billing/credit/payment-required errors (402 or provider equivalent), block the provider. Never switch to a paid plan or incur spend automatically.
11. On invalid input or policy refusal, do not blindly retry the same request across providers. Surface the issue or use an explicitly approved compatible alternative.
12. If no eligible provider remains, save the task as `queued_no_provider`, preserve its state, and report that no authorized quota is currently available. Resume only after a provider's documented reset/health recovery or operator action.

### Retry defaults

- Maximum attempts per provider: 2 (one retry only for transient failures).
- Maximum provider failovers per task: 5 by default, configurable up to a safe operator-defined ceiling.
- Exponential backoff with jitter; honor `Retry-After`.
- Circuit breaker: open after repeated failures; periodically probe with a low-cost health check.
- Never retry non-idempotent actions unless the destination supports idempotency or the action's outcome is verified first.

## Provider adapter contract

Every adapter should implement:

- `healthCheck()`
- `listModels()` (when supported)
- `getCapabilities(model)`
- `getQuota()` (return explicit values or `unknown`)
- `invoke(request, options)`
- `normalizeError(error)` returning categories: `rate_limited`, `quota_exhausted`, `auth`, `billing`, `transient`, `invalid_request`, `policy`, `unknown`
- `parseResetTime(headers, body)`

Keep provider-specific behavior inside adapters. The router must not assume all providers use the same headers, token counters, model names, or error formats.

## Suggested provider record

```json
{
  "id": "provider-model-id",
  "provider": "verified-provider-name",
  "model": "verified-model-id",
  "adapter": "adapter-module",
  "capabilities": ["text", "code"],
  "credential_ref": "PROVIDER_API_KEY",
  "cost_tier": "free",
  "free_tier_verified_at": "YYYY-MM-DD",
  "quota_status": "unknown",
  "quota_reset_at": null,
  "status": "discovered",
  "enabled": false,
  "priority": 100,
  "max_context_tokens": null,
  "data_policy": "review-required"
}
```

Do not commit real credentials, private prompts, personal data, or unverified quota claims.

## Task compatibility and quality

- Preserve the original task intent, output format, language, and constraints during failover.
- Convert provider-specific request formats through adapters; do not silently truncate or alter the user's content.
- If a fallback model has a smaller context window or lower capability, stop and request approval or use a safe, explicit chunking strategy.
- Validate structured outputs against the requested schema.
- For code, run tests or static checks where available before marking complete.
- For generated media, verify that the returned asset exists and is readable before reporting success.
- Do not treat a successful HTTP response as proof that the task output is correct.

## 365×24×7 operations

For continuous deployment, run the router as a managed service with:
- durable queue and database,
- encrypted secret storage,
- scheduler/worker process,
- health checks and restart policy,
- bounded concurrency,
- per-provider rate-limit buckets,
- metrics and alerts,
- backups and recovery tests,
- timezone-aware maintenance windows.

A phone app or an open browser tab is not a reliable 24/7 host. Continuous operation requires an always-on server/cloud runtime and may incur infrastructure costs. Keep the service idle when no tasks are queued.

## Status vocabulary

Use these exact distinctions in reports:
- `registry_slot`: an available place for a provider record.
- `discovered`: provider identified; not yet configured.
- `configured`: adapter and credential reference supplied.
- `authenticated`: a real API health/auth check succeeded.
- `eligible`: currently compatible with this task and all policies.
- `rate_limited`: provider asked the client to slow down.
- `quota_exhausted`: provider confirmed the relevant quota is used.
- `quota_unknown`: no reliable quota data is available.
- `disabled`: operator or safety policy has disabled the provider.

Never display a provider as active/ready solely because it exists in the registry.

## Operator report format

For each run, report:
1. Task status and task ID.
2. Selected provider/model and why it was selected.
3. Failovers attempted and normalized reasons.
4. Verified quota/reset details, or explicitly `unknown`.
5. Whether paid usage was blocked or allowed under the configured budget.
6. Final output location or queued/error state.
7. One concrete action needed if no eligible provider remains.

## Acceptance tests

Before production:
- 429 with `Retry-After` causes cooldown and safe failover.
- Explicit quota exhaustion selects another eligible provider.
- 401/403 disables the broken credential without retry loops.
- 402 never triggers paid usage when paid mode is disabled.
- No eligible provider persists the task without losing input.
- A worker restart resumes queued tasks without duplicate side effects.
- A fallback with insufficient context/capability is rejected safely.
- Secrets never appear in logs, commits, traces, or user-facing reports.
- Registry can hold 500 records, while only verified/configured records are shown as usable.
- A simulated 24-hour run respects each provider's rate limits and budget.

## User-facing behavior

Be concise and honest. Say what is connected, tested, available, unknown, and blocked. Never promise unlimited tokens, guaranteed uptime, or 500 working providers. Prefer the next authorized free provider; otherwise preserve the task and explain that all eligible quotas are exhausted or unavailable.
