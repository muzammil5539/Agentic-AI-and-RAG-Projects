"""SQLite checkpointer for LangGraph — persistent chat memory."""

from __future__ import annotations

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

_checkpointer: AsyncSqliteSaver | None = None


def set_checkpointer(checkpointer: AsyncSqliteSaver) -> None:
    """Set the shared checkpointer (called once from the app lifespan)."""
    global _checkpointer
    _checkpointer = checkpointer


def get_checkpointer() -> AsyncSqliteSaver:
    """Return the shared checkpointer. Must be set via set_checkpointer() first."""
    if _checkpointer is None:
        raise RuntimeError(
            "Checkpointer not initialized — call set_checkpointer() in lifespan first."
        )
    return _checkpointer
