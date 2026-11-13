# Production Readiness — no-demo release checklist

## Delivered in repository
- [x] Provider routing foundation with free-tier-only service policy.
- [x] Generic OpenAI-compatible adapter (only for documented compatible APIs).
- [x] Persistent single-node task state and queue-worker scaffold.
- [x] Docker Compose deployment template and GitHub Actions workflow.
- [x] 500 placeholder registry slots with honest status vocabulary.
- [x] Social platform integration inventory and explicit OAuth/publishing contract.
- [x] FFmpeg media helpers for audio extraction, voice cleanup and video transcoding.
- [x] Persistent single-node scheduler primitives.
- [x] Social draft store with explicit-approval gate; no live publisher adapters.
- [x] Security primitives (constant-time bearer validation and in-memory rate limiter).
- [x] Redacted JSON event logging, process-local counters and read-only dashboard starter.
- [x] Unit tests for routing, scheduling, social approval, security and redaction.

## Still blocked on external operator setup / engineering
- [ ] Add actual provider credentials as deployment secrets; verify each provider with live requests.
- [ ] Implement individual adapters for providers whose APIs are not OpenAI-compatible; verify 500 provider candidates and terms before adding.
- [ ] Integrate security primitives into the public HTTP service; add distributed rate limiting, request quotas, TLS, WAF and abuse protection.
- [ ] Implement AI-specific TTS, voice cloning, neural noise removal, image/video generation and their provider adapters.
- [ ] Implement and test platform-specific OAuth clients, callbacks, token refresh, scopes, app reviews, media upload and publishing adapters.
- [ ] Add scheduler daemon, retry leases, crash recovery and durable distributed queue.
- [ ] Export metrics/logs to OpenTelemetry/Prometheus and configure alerting.
- [ ] Run CI and inspect the latest workflow result.
- [ ] Select a hosting account/region and deploy the service; configure domain, TLS, secret storage, persistent storage and backups.
- [ ] Replace single-node SQLite polling with a managed transactional database and durable queue before horizontal scaling.
- [ ] Run end-to-end, duplicate-submission, crash-recovery, load, security and restore tests.

## Go-live gates
Do not mark a provider or social platform connected until authentication and a real permitted API call succeed. Do not mark the service production-ready until deployment, TLS, secrets, persistent queue, monitoring, backup/restore and recovery tests have passed. No paid provider, host, API credit or subscription may be activated without explicit approval.

## Operator-provided inputs needed for live activation
1. A hosting target/account with permission to deploy.
2. Provider API keys added directly to the host's secret manager (not sent in chat or committed).
3. OAuth app credentials and redirect URI setup for each social platform.
4. Approval for any service that incurs charges.
5. Install FFmpeg on the selected runtime for local media processing.

See `INTEGRATION_STATUS.md` for exact connection boundaries.
