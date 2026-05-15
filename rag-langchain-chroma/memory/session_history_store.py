"""
Per-chat session memory.

Each session has its own isolated conversation history.
Sessions are persisted to disk so they survive server restarts.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SESSIONS_FILE = Path(__file__).parent.parent / "data" / "sessions.json"
MAX_HISTORY_TURNS = 20  # keep last 20 user/assistant pairs per session


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------------ I/O --
    def _load(self) -> None:
        if SESSIONS_FILE.exists():
            try:
                with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                    self._sessions = json.load(f)
            except Exception:
                self._sessions = {}

    def _save(self) -> None:
        SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._sessions, f, indent=2, ensure_ascii=False)

    # ---------------------------------------------------------- CRUD ---------
    def create_session(self, session_id: Optional[str] = None, title: str = "New Chat") -> dict:
        sid = session_id or str(uuid.uuid4())
        session = {
            "id": sid,
            "title": title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
        }
        self._sessions[sid] = session
        self._save()
        return session

    def get_session(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: Optional[str]) -> dict:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        return self.create_session(session_id)

    def list_sessions(self) -> list[dict]:
        sessions = list(self._sessions.values())
        sessions.sort(key=lambda x: x.get("updated_at", x["created_at"]), reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._save()
            return True
        return False

    def rename_session(self, session_id: str, title: str) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id]["title"] = title
            self._save()
            return True
        return False

    # ------------------------------------------------------- Messages --------
    def add_message(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._sessions:
            self.create_session(session_id)
        session = self._sessions[session_id]
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        session["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Auto-title from first user message
        user_msgs = [m for m in session["messages"] if m["role"] == "user"]
        if role == "user" and len(user_msgs) == 1:
            session["title"] = content[:60] + ("…" if len(content) > 60 else "")

        self._save()

    def get_history(self, session_id: str, max_turns: int = MAX_HISTORY_TURNS) -> list[dict]:
        """Return last ``max_turns`` user/assistant pairs as a flat list."""
        session = self._sessions.get(session_id)
        if not session:
            return []
        messages = session["messages"]
        # Keep last max_turns * 2 messages
        return messages[-(max_turns * 2):]

    def clear_history(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id]["messages"] = []
            self._sessions[session_id]["title"] = "New Chat"
            self._sessions[session_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save()
            return True
        return False


# Singleton
session_store = SessionStore()
