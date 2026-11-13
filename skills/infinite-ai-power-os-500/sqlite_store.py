"""SQLite-backed task state store for single-node deployments."""
import json
import sqlite3
from pathlib import Path
from threading import RLock


class SQLiteTaskStore:
    """Durable across process restarts; use Postgres/Redis for multi-replica workers."""
    def __init__(self, database_path="data/tasks.sqlite3"):
        self.path = str(database_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS task_states (
                    task_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=15000")
        return db

    def save(self, task_id, state):
        payload = json.dumps(state, ensure_ascii=False, default=str)
        with self._lock, self._connect() as db:
            db.execute("""
                INSERT INTO task_states(task_id, state_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(task_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    updated_at=CURRENT_TIMESTAMP
            """, (task_id, payload))

    def load(self, task_id):
        with self._connect() as db:
            row = db.execute(
                "SELECT state_json FROM task_states WHERE task_id=?", (task_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None
