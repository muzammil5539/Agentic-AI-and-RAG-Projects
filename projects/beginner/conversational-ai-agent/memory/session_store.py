"""Session metadata store — JSON-backed persistence (consistent with P1/P2)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from config import settings


class Session(BaseModel):
    """Session metadata (not the messages — those live in the checkpointer)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: str
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0


class SessionStore:
    """Thread-safe JSON-backed session metadata store."""

    def __init__(self, path: str | None = None):
        self._path = Path(path or settings.SESSIONS_FILE)
        self._lock = threading.Lock()
        self._sessions: dict[str, Session] = {}
        self._load()

    # ── Persistence ──────────────────────────────────────
    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                for sid, data in raw.items():
                    self._sessions[sid] = Session.model_validate(data)
            except (json.JSONDecodeError, Exception):
                self._sessions = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            sid: s.model_dump(mode="json") for sid, s in self._sessions.items()
        }
        self._path.write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )

    # ── CRUD ─────────────────────────────────────────────
    def create(self, user_id: str, title: str | None = None) -> Session:
        session = Session(user_id=user_id, title=title or "New Chat")
        with self._lock:
            self._sessions[session.id] = session
            self._save()
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def list_for_user(self, user_id: str) -> list[Session]:
        return sorted(
            (s for s in self._sessions.values() if s.user_id == user_id),
            key=lambda s: s.updated_at,
            reverse=True,
        )

    def update_title(self, session_id: str, title: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.title = title
                session.updated_at = datetime.utcnow()
                self._save()
            return session

    def increment_messages(self, session_id: str, count: int = 1) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.message_count += count
                session.updated_at = datetime.utcnow()
                self._save()

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._save()
                return True
            return False


# ── Singleton ────────────────────────────────────────────────────
_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
