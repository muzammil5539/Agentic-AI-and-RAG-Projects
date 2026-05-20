"""Pydantic schemas for WebSocket messages (both directions)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Client → Server ──────────────────────────────────────────────


class WSChatMessage(BaseModel):
    """Client sends a chat query over WebSocket."""

    type: Literal["chat"] = "chat"
    query: str = Field(..., min_length=1)
    session_id: str | None = None
    model: str = "gpt-4o-mini"
    api_key: str = Field(..., min_length=1)


class WSCancelMessage(BaseModel):
    """Client requests cancellation of the current stream."""

    type: Literal["cancel"] = "cancel"


# ── Server → Client ──────────────────────────────────────────────


class WSThoughtEvent(BaseModel):
    """Agent is reasoning / planning."""

    type: Literal["thought"] = "thought"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSToolCallEvent(BaseModel):
    """Agent is calling a tool."""

    type: Literal["tool_call"] = "tool_call"
    tool_name: str
    tool_args: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSToolResultEvent(BaseModel):
    """Tool returned a result."""

    type: Literal["tool_result"] = "tool_result"
    tool_name: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSTokenEvent(BaseModel):
    """Streamed token from the final answer."""

    type: Literal["token"] = "token"
    content: str


class WSDoneEvent(BaseModel):
    """Stream finished."""

    type: Literal["done"] = "done"
    session_id: str
    model: str


class WSErrorEvent(BaseModel):
    """Error during processing."""

    type: Literal["error"] = "error"
    message: str


# Union type for all outgoing events
WSOutgoingEvent = (
    WSThoughtEvent
    | WSToolCallEvent
    | WSToolResultEvent
    | WSTokenEvent
    | WSDoneEvent
    | WSErrorEvent
)
