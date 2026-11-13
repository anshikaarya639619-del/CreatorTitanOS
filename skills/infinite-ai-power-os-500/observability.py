"""Minimal redacted JSON logging and in-process counters."""
import json
import logging
from threading import Lock
from datetime import datetime, timezone

SENSITIVE = {"authorization", "token", "api_key", "secret", "password", "prompt", "content"}


def redact(value):
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if k.lower() in SENSITIVE else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


class JsonEventLogger:
    def __init__(self, name: str = "infinite-ai-power-os"):
        self.logger = logging.getLogger(name)

    def event(self, event: str, **fields):
        record = {"timestamp": datetime.now(timezone.utc).isoformat(),
                  "event": event, **redact(fields)}
        self.logger.info(json.dumps(record, ensure_ascii=False, default=str))


class Metrics:
    """Process-local counters only; export to Prometheus/OTel in production."""
    def __init__(self):
        self._values = {}
        self._lock = Lock()

    def increment(self, name: str, amount: int = 1):
        with self._lock:
            self._values[name] = self._values.get(name, 0) + amount

    def snapshot(self):
        with self._lock:
            return dict(self._values)
