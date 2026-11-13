import unittest
from datetime import datetime, timezone

from router import (
    ErrorKind, MemoryTaskStore, ProviderError, ProviderRecord,
    ProviderRouter, RouteStatus, TaskRequest
)


class FakeAdapter:
    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = 0

    def invoke(self, model, payload, *, idempotency_key, timeout_seconds):
        self.calls += 1
        result = self.behavior()
        if isinstance(result, Exception):
            raise result
        return result


class RouterTests(unittest.TestCase):
    def provider(self, pid, *, cost="free", priority=1):
        return ProviderRecord(
            provider_id=pid, provider_name=pid, model="model",
            capabilities=["text"], cost_tier=cost,
            enabled=True, authenticated=True, priority=priority,
            quota_status="unknown"
        )

    def test_quota_exhaustion_fails_over(self):
        first = FakeAdapter(lambda: ProviderError(ErrorKind.QUOTA_EXHAUSTED, "empty"))
        second = FakeAdapter(lambda: {"answer": "ok"})
        router = ProviderRouter(
            [self.provider("a"), self.provider("b", priority=2)],
            {"a": first, "b": second}, sleep=lambda _: None
        )
        result = router.route(TaskRequest("text", {"prompt": "hello"}))
        self.assertEqual(result.status, RouteStatus.SUCCEEDED)
        self.assertEqual(result.provider_id, "b")
        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 1)

    def test_paid_provider_blocked_by_default(self):
        paid = FakeAdapter(lambda: {"answer": "should not run"})
        router = ProviderRouter([self.provider("paid", cost="paid")], {"paid": paid})
        result = router.route(TaskRequest("text", {"prompt": "hello"}))
        self.assertEqual(result.status, RouteStatus.QUEUED_NO_PROVIDER)
        self.assertEqual(paid.calls, 0)

    def test_auth_failure_disables_provider(self):
        adapter = FakeAdapter(lambda: ProviderError(ErrorKind.AUTH, "bad credential"))
        router = ProviderRouter([self.provider("a")], {"a": adapter})
        result = router.route(TaskRequest("text", {"prompt": "hello"}))
        self.assertEqual(result.status, RouteStatus.QUEUED_NO_PROVIDER)
        self.assertFalse(router.providers["a"].enabled)

    def test_task_is_preserved_when_no_provider(self):
        store = MemoryTaskStore()
        router = ProviderRouter([], {}, task_store=store)
        task = TaskRequest("text", {"prompt": "persist me"})
        result = router.route(task)
        self.assertEqual(result.status, RouteStatus.QUEUED_NO_PROVIDER)
        self.assertEqual(store.load(task.task_id)["status"], "queued_no_provider")


if __name__ == "__main__":
    unittest.main()
