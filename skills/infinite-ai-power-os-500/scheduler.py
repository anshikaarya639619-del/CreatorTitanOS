"""Persistent single-node scheduler with atomic due-job claiming."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import uuid


class SQLiteScheduler:
    def __init__(self, db_path: str = "data/scheduler.sqlite3"):
        self.path = str(db_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS scheduled_jobs(
                job_id TEXT PRIMARY KEY, run_at TEXT NOT NULL, payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', claimed_at TEXT)""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_due ON scheduled_jobs(status,run_at)")

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.execute("PRAGMA busy_timeout=15000")
        return db

    def schedule(self, run_at: str, payload: dict) -> str:
        when = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ValueError("run_at must include a timezone")
        job_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("INSERT INTO scheduled_jobs(job_id,run_at,payload) VALUES(?,?,?)",
                       (job_id, when.astimezone(timezone.utc).isoformat(),
                        json.dumps(payload, ensure_ascii=False)))
        return job_id

    def claim_due(self, limit: int = 25, now: datetime | None = None) -> list[dict]:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT job_id,payload FROM scheduled_jobs WHERE status='pending' AND run_at<=? ORDER BY run_at LIMIT ?",
                              (current, max(1, min(limit, 100)))).fetchall()
            for job_id, _ in rows:
                db.execute("UPDATE scheduled_jobs SET status='claimed',claimed_at=? WHERE job_id=? AND status='pending'",
                           (current, job_id))
            db.execute("COMMIT")
        return [{"job_id": job_id, "payload": json.loads(payload)} for job_id, payload in rows]

    def mark_done(self, job_id: str) -> None:
        with self._connect() as db:
            db.execute("UPDATE scheduled_jobs SET status='done' WHERE job_id=? AND status='claimed'", (job_id,))
