import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from security import SlidingWindowRateLimiter, bearer_authorized
from scheduler import SQLiteScheduler
from social_gateway import SocialDraftStore
from observability import redact


class ModuleTests(unittest.TestCase):
    def test_bearer_token_constant_contract(self):
        self.assertTrue(bearer_authorized("Bearer abc", "abc"))
        self.assertFalse(bearer_authorized("Bearer wrong", "abc"))
        self.assertFalse(bearer_authorized("Bearer abc", ""))

    def test_rate_limit_window(self):
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10)
        self.assertTrue(limiter.allow("client", now=0))
        self.assertTrue(limiter.allow("client", now=1))
        self.assertFalse(limiter.allow("client", now=2))
        self.assertTrue(limiter.allow("client", now=11))

    def test_scheduler_claims_due_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            scheduler = SQLiteScheduler(str(Path(tmp) / "jobs.sqlite"))
            scheduler.schedule("2026-01-01T00:00:00+00:00", {"capability": "text"})
            now = datetime(2026, 1, 2, tzinfo=timezone.utc)
            self.assertEqual(len(scheduler.claim_due(now=now)), 1)
            self.assertEqual(scheduler.claim_due(now=now), [])

    def test_social_draft_requires_explicit_approval_and_publisher(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SocialDraftStore(str(Path(tmp) / "social.sqlite"))
            draft = store.create("youtube", "channel-ref", "Draft caption")
            with self.assertRaises(PermissionError):
                store.approve_and_publish(draft.draft_id, approved=False)
            with self.assertRaises(RuntimeError):
                store.approve_and_publish(draft.draft_id, approved=True)

    def test_redaction(self):
        value = redact({"api_key": "secret", "nested": {"prompt": "private", "count": 3}})
        self.assertEqual(value["api_key"], "[REDACTED]")
        self.assertEqual(value["nested"]["prompt"], "[REDACTED]")
        self.assertEqual(value["nested"]["count"], 3)


if __name__ == "__main__":
    unittest.main()
