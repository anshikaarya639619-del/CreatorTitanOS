"""Polling worker that resumes durable queued tasks after provider recovery."""
import os
import time

from router import TaskRequest
from service import build_router
from sqlite_store import SQLiteTaskStore


def run_forever():
    store = SQLiteTaskStore(os.environ.get("AI_TASK_DB", "data/tasks.sqlite3"))
    router = build_router()
    interval = max(5, int(os.environ.get("QUEUE_POLL_SECONDS", "30")))
    while True:
        for item in store.list_by_status("queued_no_provider", limit=50):
            # Reconstruct only the original task data. A repeated task must use the
            # same idempotency key; downstream side-effecting tools must honor it.
            task = TaskRequest(
                capability=item.get("capability", "text"),
                payload=item.get("task_payload") or {},
                allowed_cost_tiers=tuple(item.get("allowed_cost_tiers") or ["free"]),
                max_failovers=int(item.get("max_failovers", 5)),
                max_attempts_per_provider=int(item.get("max_attempts_per_provider", 2)),
                required_context_tokens=item.get("required_context_tokens"),
                allowed_regions=item.get("allowed_regions"),
                task_id=item["task_id"],
                idempotency_key=item.get("idempotency_key", item["task_id"]),
            )
            router.route(task)
        time.sleep(interval)


if __name__ == "__main__":
    run_forever()
