"""SQLite checkpointer for LangGraph — persistent chat memory."""

from __future__ import annotations

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from config import settings

_checkpointer: AsyncSqliteSaver | None = None


def get_checkpointer() -> AsyncSqliteSaver:
    """Get or create the shared async SQLite checkpointer."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = AsyncSqliteSaver.from_conn_string(settings.SQLITE_DB_PATH)
    return _checkpointer
