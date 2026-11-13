"""Approval-gated social publishing contract; no platform is connected by default."""
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from typing import Protocol
import uuid


@dataclass
class PublishDraft:
    draft_id: str
    platform: str
    account_ref: str
    media_path: str | None
    text: str
    status: str
    scheduled_at: str | None


class Publisher(Protocol):
    def publish(self, draft: PublishDraft, *, idempotency_key: str) -> dict: ...


class SocialDraftStore:
    def __init__(self, db_path: str = "data/social.sqlite3"):
        self.path = str(db_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS drafts(
                draft_id TEXT PRIMARY KEY, platform TEXT NOT NULL, account_ref TEXT NOT NULL,
                media_path TEXT, text TEXT NOT NULL, status TEXT NOT NULL,
                scheduled_at TEXT, created_at TEXT NOT NULL)""")

    def create(self, platform: str, account_ref: str, text: str,
               media_path: str | None = None, scheduled_at: str | None = None) -> PublishDraft:
        if not platform or not account_ref or not text.strip():
            raise ValueError("platform, account_ref and non-empty text are required")
        if scheduled_at:
            datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        draft = PublishDraft(str(uuid.uuid4()), platform, account_ref, media_path,
                             text, "awaiting_approval", scheduled_at)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?,?,?)",
                       (draft.draft_id, draft.platform, draft.account_ref, draft.media_path,
                        draft.text, draft.status, draft.scheduled_at,
                        datetime.now(timezone.utc).isoformat()))
        return draft

    def approve_and_publish(self, draft_id: str, *, approved: bool,
                            publisher: Publisher | None = None) -> dict:
        if not approved:
            raise PermissionError("Explicit approval of this exact draft is required")
        if publisher is None:
            raise RuntimeError("No verified platform publisher is connected")
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT draft_id,platform,account_ref,media_path,text,status,scheduled_at FROM drafts WHERE draft_id=?",
                             (draft_id,)).fetchone()
            if not row:
                raise KeyError(draft_id)
            draft = PublishDraft(*row)
            if draft.status == "published":
                return {"status": "already_published", "draft_id": draft_id}
            if draft.status != "awaiting_approval":
                raise ValueError("Draft is not awaiting approval")
            db.execute("UPDATE drafts SET status='publishing' WHERE draft_id=? AND status='awaiting_approval'",
                       (draft_id,))
        result = publisher.publish(draft, idempotency_key=draft_id)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE drafts SET status='published' WHERE draft_id=?", (draft_id,))
        return {"status": "published", "draft_id": draft_id, "result": result}
