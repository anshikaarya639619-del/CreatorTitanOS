# Integration status and activation boundaries

## Implemented in this repository
- Provider router, free-first policy, bounded retries and task persistence.
- Generic adapter for APIs that explicitly document OpenAI-compatible chat completions.
- FFmpeg wrappers for audio extraction, voice denoising/loudness normalization and video transcode.
- Persistent scheduler primitives with atomic single-node job claiming.
- Social draft storage and explicit-approval publishing contract.
- Bearer-token and in-memory rate-limit security primitives.
- Redacted structured event logging, process-local metrics and a read-only dashboard starter.
- Unit tests for the new primitives.

## Not connected / requires credentials or infrastructure
- 500 real AI providers: registry capacity contains placeholders; provider discovery, official API verification, credentials and per-provider adapters remain external tasks.
- Real social publishing: no OAuth clients, callbacks, platform upload adapters, app reviews or user accounts are connected.
- Real TTS, voice cloning, image/video generation and third-party noise-engineering models: require selected services/models and their documented adapters. FFmpeg cleanup is local post-processing, not AI voice cloning.
- Multi-node scheduling/queueing, Redis/Postgres, distributed locks, production rate limiting, telemetry export, alerting and backups.
- Cloud deployment, TLS/domain, secret manager, persistent storage and disaster recovery.

## Cost and safety
- The runtime must remain free-tier-first. Paid fallback, paid API credits, hosting upgrades or subscriptions require explicit operator approval.
- Never send account passwords, API keys or OAuth tokens in chat or commit them to Git.
- Publishing must require approval of the exact draft and a verified publisher adapter.
- Do not bypass quotas, platform limits, OAuth scopes, app reviews or provider terms.
