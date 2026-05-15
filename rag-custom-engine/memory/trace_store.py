"""
Persistent pipeline trace store — JSON-persisted, per-session.
Each query turn's pipeline trace (all 14 steps) is saved here so
the chat UI can re-render traces after page reload or session switch.
"""

import json
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path

from config import settings


class TraceStore:
    """
    Stores pipeline traces keyed by session_id.
    Each session maps to an ordered list of trace records (one per query turn).
    Uses threading.RLock so that nested lock acquisitions (if any) don't deadlock.
    Uses atomic tmp-then-rename writes to avoid corrupt JSON on crash.
    """

    def __init__(self):
        self._traces: dict[str, list[dict]] = {}
        self._path = Path(settings.TRACES_FILE)
        self._lock = threading.RLock()
        self._load()

    # ── Public API ───────────────────────────────────────────────────

    def save_trace(self, session_id: str, trace: dict) -> None:
        """Append a completed pipeline trace for the given session."""
        with self._lock:
            if session_id not in self._traces:
                self._traces[session_id] = []
            trace["turn_index"] = len(self._traces[session_id])
            self._traces[session_id].append(trace)
            self._save()

    def get_traces(self, session_id: str) -> list[dict]:
        """Return traces for a session ordered by turn_index, or [] if none."""
        with self._lock:
            return list(self._traces.get(session_id, []))

    def delete_traces(self, session_id: str) -> int:
        """Delete all traces for a session. Returns number of deleted traces."""
        with self._lock:
            traces = self._traces.pop(session_id, [])
            if traces:
                self._save()
            return len(traces)

    # ── Internal ─────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._traces = json.load(f)
            except Exception:
                self._traces = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(self._path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._traces, f, indent=2, ensure_ascii=False)
        Path(tmp).replace(self._path)


# ── Singleton factory ────────────────────────────────────────────────

_trace_store: "TraceStore | None" = None


def get_trace_store() -> TraceStore:
    global _trace_store
    if _trace_store is None:
        _trace_store = TraceStore()
    return _trace_store
