# Infinite AI Power OS 500 — Router Engine

A provider-agnostic, quota-aware failover engine. This is a working foundation, not a bundle of 500 live provider integrations.

## Requirements
- Python 3.10+
- Standard library only

## Quick start
```bash
python -m unittest discover -s tests -v
```

Integrate the router into your service by implementing the `ProviderAdapter` interface and registering only providers for which you have authorized credentials and verified API documentation.

## Safety defaults
- Free tier only unless an explicit positive spend budget is supplied by the calling application.
- No credentials in registry files; pass secrets to adapters from a secret manager/environment.
- No automatic quota bypass, account rotation, or paid upgrades.
- Unknown quota is never treated as unlimited.
- Bounded retries and failovers.
- If no eligible provider remains, return a queued state instead of discarding the task.

## Files
- `router.py`: registry, eligibility, failover, cooldown, retry, task state, and in-memory demo adapter.
- `providers.example.json`: safe example registry format; no real credentials.
- `tests/test_router.py`: deterministic tests for failover and cost safeguards.

## Production deployment
Use a durable database/queue, encrypted secret manager, managed always-on worker, monitoring, backups, and provider-specific adapters. The included in-memory task store is for development/testing only; it does not survive process restarts. A 24/7 claim requires deployment and operational testing.
