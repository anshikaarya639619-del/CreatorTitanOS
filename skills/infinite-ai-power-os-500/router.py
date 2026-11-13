"""Quota-aware AI provider router with bounded automatic failover.

Standard-library-only reference implementation. Provider-specific HTTP calls belong
in adapters. Never treat unknown quota as unlimited or silently enable paid spend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence
import random
import time
import uuid


class ErrorKind(str, Enum):
    RATE_LIMITED = "rate_limited"
    QUOTA_EXHAUSTED = "quota_exhausted"
    AUTH = "auth"
    BILLING = "billing"
    TRANSIENT = "transient"
    INVALID_REQUEST = "invalid_request"
    POLICY = "policy"
    UNKNOWN = "unknown"


class RouteStatus(str, Enum):
    SUCCEEDED = "succeeded"
    QUEUED_NO_PROVIDER = "queued_no_provider"
    FAILED = "failed"


@dataclass
class ProviderError(Exception):
    kind: ErrorKind
    message: str
    retry_after_seconds: Optional[float] = None

    def __str__(self) -> str:
        return self.message


@dataclass
class TaskRequest:
    capability: str
    payload: Dict[str, Any]
    allowed_cost_tiers: Sequence[str] = ("free",)
    max_failovers: int = 5
    max_attempts_per_provider: int = 2
    required_context_tokens: Optional[int] = None
    allowed_regions: Optional[Sequence[str]] = None
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ProviderRecord:
    provider_id: str
    provider_name: str
    model: str
    capabilities: Sequence[str]
    cost_tier: str = "free"
    enabled: bool = False
    authenticated: bool = False
    priority: int = 100
    quota_status: str = "unknown"  # available, exhausted, unknown
    quota_remaining: Optional[int] = None
    quota_reset_at: Optional[datetime] = None
    max_context_tokens: Optional[int] = None
    region: Optional[str] = None
    data_policy: str = "review-required"
    cooldown_until: Optional[datetime] = None
    consecutive_failures: int = 0
    disabled_reason: Optional[str] = None


class ProviderAdapter(Protocol):
    def invoke(self, model: str, payload: Dict[str, Any], *,
               idempotency_key: str, timeout_seconds: float) -> Any:
        """Invoke the documented provider API and normalize errors to ProviderError."""
        ...


class TaskStore(Protocol):
    def save(self, task_id: str, state: Dict[str, Any]) -> None: ...
    def load(self, task_id: str) -> Optional[Dict[str, Any]]: ...


class MemoryTaskStore:
    """Development-only store. Replace with durable DB/queue for production."""
    def __init__(self) -> None:
        self._items: Dict[str, Dict[str, Any]] = {}

    def save(self, task_id: str, state: Dict[str, Any]) -> None:
        self._items[task_id] = dict(state)

    def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        value = self._items.get(task_id)
        return dict(value) if value else None


@dataclass
class RouteResult:
    status: RouteStatus
    task_id: str
    output: Any = None
    provider_id: Optional[str] = None
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    message: str = ""


class ProviderRouter:
    def __init__(self, providers: Iterable[ProviderRecord],
                 adapters: Dict[str, ProviderAdapter],
                 task_store: Optional[TaskStore] = None,
                 *, request_timeout_seconds: float = 45.0,
                 base_backoff_seconds: float = 1.0,
                 max_backoff_seconds: float = 30.0,
                 clock=lambda: datetime.now(timezone.utc),
                 sleep=time.sleep,
                 rng=random.random) -> None:
        self.providers = {p.provider_id: p for p in providers}
        self.adapters = adapters
        self.task_store = task_store or MemoryTaskStore()
        self.timeout = request_timeout_seconds
        self.base_backoff = base_backoff_seconds
        self.max_backoff = max_backoff_seconds
        self.clock = clock
        self.sleep = sleep
        self.rng = rng

    def _eligible(self, task: TaskRequest) -> List[ProviderRecord]:
        now = self.clock()
        eligible = []
        for p in self.providers.values():
            if not p.enabled or not p.authenticated:
                continue
            if p.provider_id not in self.adapters:
                continue
            if p.cost_tier not in task.allowed_cost_tiers:
                continue
            if task.capability not in p.capabilities:
                continue
            if p.quota_status == "exhausted":
                # A known reset time can make it eligible again only after reset.
                if not p.quota_reset_at or now < p.quota_reset_at:
                    continue
                p.quota_status = "unknown"
                p.quota_remaining = None
            if p.cooldown_until and now < p.cooldown_until:
                continue
            if task.required_context_tokens and p.max_context_tokens is not None:
                if p.max_context_tokens < task.required_context_tokens:
                    continue
            if task.allowed_regions and p.region not in task.allowed_regions:
                continue
            eligible.append(p)
        # Free-first, then operator priority. Unknown quota remains eligible but is
        # never represented as unlimited; providers can still return a 429.
        return sorted(eligible, key=lambda p: (0 if p.cost_tier == "free" else 1,
                                                p.priority, p.consecutive_failures))

    def route(self, task: TaskRequest) -> RouteResult:
        attempts: List[Dict[str, Any]] = []
        tried = set()
        failovers = 0
        self.task_store.save(task.task_id, {
            "status": "running", "capability": task.capability,
            "idempotency_key": task.idempotency_key, "attempts": attempts
        })

        while failovers <= task.max_failovers:
            candidates = [p for p in self._eligible(task) if p.provider_id not in tried]
            if not candidates:
                self.task_store.save(task.task_id, {
                    "status": RouteStatus.QUEUED_NO_PROVIDER.value,
                    "capability": task.capability, "attempts": attempts,
                    "idempotency_key": task.idempotency_key
                })
                return RouteResult(RouteStatus.QUEUED_NO_PROVIDER, task.task_id,
                                   attempts=attempts,
                                   message="No authorized, compatible provider is currently eligible. Task state preserved.")

            provider = candidates[0]
            tried.add(provider.provider_id)
            adapter = self.adapters[provider.provider_id]

            for attempt_no in range(1, max(1, task.max_attempts_per_provider) + 1):
                try:
                    output = adapter.invoke(
                        provider.model, task.payload,
                        idempotency_key=task.idempotency_key,
                        timeout_seconds=self.timeout
                    )
                    provider.consecutive_failures = 0
                    self.task_store.save(task.task_id, {
                        "status": RouteStatus.SUCCEEDED.value,
                        "provider_id": provider.provider_id,
                        "attempts": attempts, "idempotency_key": task.idempotency_key
                    })
                    return RouteResult(RouteStatus.SUCCEEDED, task.task_id, output,
                                       provider.provider_id, attempts, "Task completed.")
                except ProviderError as exc:
                    attempts.append({"provider_id": provider.provider_id,
                                     "attempt": attempt_no, "error": exc.kind.value,
                                     "message": exc.message})
                    provider.consecutive_failures += 1

                    if exc.kind == ErrorKind.RATE_LIMITED:
                        provider.cooldown_until = self.clock() + timedelta(
                            seconds=max(0.0, exc.retry_after_seconds or 60.0))
                        break
                    if exc.kind == ErrorKind.QUOTA_EXHAUSTED:
                        provider.quota_status = "exhausted"
                        provider.quota_remaining = 0
                        provider.quota_reset_at = (
                            self.clock() + timedelta(seconds=exc.retry_after_seconds)
                            if exc.retry_after_seconds is not None else None
                        )
                        break
                    if exc.kind in (ErrorKind.AUTH, ErrorKind.BILLING):
                        provider.enabled = False
                        provider.disabled_reason = exc.kind.value
                        break
                    if exc.kind in (ErrorKind.INVALID_REQUEST, ErrorKind.POLICY):
                        self.task_store.save(task.task_id, {
                            "status": RouteStatus.FAILED.value, "attempts": attempts,
                            "idempotency_key": task.idempotency_key
                        })
                        return RouteResult(RouteStatus.FAILED, task.task_id,
                                           attempts=attempts,
                                           message="Request or policy error; not blindly retried.")
                    if exc.kind in (ErrorKind.TRANSIENT, ErrorKind.UNKNOWN):
                        if attempt_no < task.max_attempts_per_provider:
                            delay = min(self.max_backoff,
                                        self.base_backoff * (2 ** (attempt_no - 1)))
                            delay = delay * (0.5 + self.rng())
                            self.sleep(delay)
                            continue
                        provider.cooldown_until = self.clock() + timedelta(seconds=30)
                        break
            failovers += 1

        self.task_store.save(task.task_id, {
            "status": RouteStatus.QUEUED_NO_PROVIDER.value,
            "capability": task.capability, "attempts": attempts,
            "idempotency_key": task.idempotency_key
        })
        return RouteResult(RouteStatus.QUEUED_NO_PROVIDER, task.task_id,
                           attempts=attempts,
                           message="Failover limit reached or no eligible provider remains; task preserved.")


def load_registry(data: Dict[str, Any]) -> List[ProviderRecord]:
    """Load safe registry metadata. Authentication is established separately by health checks."""
    records = []
    for item in data.get("providers", []):
        records.append(ProviderRecord(
            provider_id=item["id"],
            provider_name=item["provider"],
            model=item["model"],
            capabilities=item.get("capabilities", []),
            cost_tier=item.get("cost_tier", "free"),
            enabled=bool(item.get("enabled", False)),
            authenticated=False,  # Never trust a JSON flag as proof of authentication.
            priority=int(item.get("priority", 100)),
            quota_status=item.get("quota_status", "unknown"),
            max_context_tokens=item.get("max_context_tokens"),
            region=item.get("region"),
            data_policy=item.get("data_policy", "review-required")
        ))
    return records
