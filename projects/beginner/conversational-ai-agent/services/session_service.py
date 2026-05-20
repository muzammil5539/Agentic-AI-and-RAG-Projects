"""Session service — CRUD operations for chat sessions."""

from __future__ import annotations

from api.models.responses import SessionResponse, SessionListResponse
from memory.session_store import get_session_store


class SessionService:
    """Thin wrapper around SessionStore producing Pydantic response models."""

    def __init__(self):
        self._store = get_session_store()

    def create(self, user_id: str, title: str | None = None) -> SessionResponse:
        session = self._store.create(user_id=user_id, title=title)
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
        )

    def list_for_user(self, user_id: str) -> SessionListResponse:
        sessions = self._store.list_for_user(user_id)
        return SessionListResponse(
            sessions=[
                SessionResponse(
                    id=s.id,
                    user_id=s.user_id,
                    title=s.title,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    message_count=s.message_count,
                )
                for s in sessions
            ]
        )

    def get(self, session_id: str) -> SessionResponse | None:
        session = self._store.get(session_id)
        if not session:
            return None
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
        )

    def delete(self, session_id: str) -> bool:
        return self._store.delete(session_id)

    def update_title(self, session_id: str, title: str) -> SessionResponse | None:
        session = self._store.update_title(session_id, title)
        if not session:
            return None
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
        )


# ── Singleton ────────────────────────────────────────────────────
_service: SessionService | None = None


def get_session_service() -> SessionService:
    global _service
    if _service is None:
        _service = SessionService()
    return _service
