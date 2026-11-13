"""Small security primitives; production deployments still need a gateway/WAF."""
from collections import defaultdict, deque
from hmac import compare_digest
from threading import Lock
from time import monotonic
import secrets


def generate_service_token() -> str:
    return secrets.token_urlsafe(48)


def bearer_authorized(header: str, expected_token: str) -> bool:
    if not expected_token or not header.startswith("Bearer "):
        return False
    supplied = header[7:].strip()
    return bool(supplied) and compare_digest(supplied, expected_token)


class SlidingWindowRateLimiter:
    """Per-key in-memory limiter. Use Redis/API gateway for multi-worker production."""
    def __init__(self, limit: int = 60, window_seconds: float = 60.0):
        if limit < 1 or window_seconds <= 0:
            raise ValueError("limit and window_seconds must be positive")
        self.limit, self.window = limit, window_seconds
        self.events = defaultdict(deque)
        self.lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        current = monotonic() if now is None else now
        with self.lock:
            q = self.events[key]
            while q and current - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(current)
            return True
