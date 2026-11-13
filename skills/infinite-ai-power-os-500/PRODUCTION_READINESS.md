# Production Readiness — no-demo release checklist

## Delivered in repository
- [x] Provider routing foundation with free-tier-only service policy.
- [x] Generic OpenAI-compatible adapter (only for documented compatible APIs).
- [x] Persistent single-node task state and queue-worker scaffold.
- [x] Docker Compose deployment template and GitHub Actions workflow.
- [x] 500 placeholder registry slots with honest status vocabulary.
- [x] Social platform integration inventory and explicit OAuth/publishing contract.

## Still blocked on external operator setup
- [ ] Add actual provider credentials as deployment secrets; verify each provider with live requests.
- [ ] Implement individual adapters for providers whose APIs are not OpenAI-compatible.
- [ ] Run CI and fix all failures; inspect the latest workflow result.
- [ ] Select a hosting account/region and deploy the service; configure domain, TLS, secret storage, persistent storage and backups.
- [ ] Replace single-node SQLite polling with a managed transactional database and durable queue before horizontal scaling.
- [ ] Add rate/concurrency limits, request-size limits, structured redacted logs, metrics, alerting and abuse controls.
- [ ] Complete social OAuth apps, redirect URIs, scopes, reviews and platform-specific upload/publish adapters.
- [ ] Run end-to-end, duplicate-submission, crash-recovery, load, security and restore tests.

## Go-live gates
Do not mark a provider or social platform connected until authentication and a real permitted API call succeed. Do not mark the service production-ready until deployment, TLS, secrets, persistent queue, monitoring, backup/restore and recovery tests have passed. No paid provider, host, API credit or subscription may be activated without explicit approval.

## Operator-provided inputs needed for live activation
1. A hosting target/account with permission to deploy.
2. Provider API keys added directly to the host's secret manager (not sent in chat or committed).
3. OAuth app credentials and redirect URI setup for each social platform.
4. Approval for any service that incurs charges.
