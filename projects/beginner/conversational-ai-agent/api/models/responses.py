"""Pydantic response models for the Conversational AI Agent API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AgentStep(BaseModel):
    """A single step in the ReAct trace."""

    type: Literal["thought", "tool_call", "tool_result", "answer"] = Field(
        ..., description="Kind of step."
    )
    content: str = Field(..., description="Text content of the step.")
    tool_name: str | None = Field(
        default=None, description="Tool name (for tool_call / tool_result)."
    )
    tool_args: dict | None = Field(
        default=None, description="Arguments passed to the tool."
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatResponse(BaseModel):
    """Response for POST /api/v1/chat."""

    answer: str
    session_id: str
    model: str
    steps: list[AgentStep] = Field(default_factory=list)


class SessionResponse(BaseModel):
    """A single chat session."""

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class SessionListResponse(BaseModel):
    """Wrapper for listing sessions."""

    sessions: list[SessionResponse]


class SessionMessagesResponse(BaseModel):
    """Full message history for a session."""

    session_id: str
    messages: list[dict]


class ToolInfo(BaseModel):
    """Metadata about an available tool."""

    name: str
    description: str
    parameters: dict = Field(default_factory=dict)
    category: Literal["openai_builtin", "custom"] = "custom"


class ToolListResponse(BaseModel):
    """Wrapper for listing tools."""

    tools: list[ToolInfo]


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document for RAG."""

    filename: str
    num_chunks: int
    collection: str
    message: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "1.0.0"
    models: list[str] = Field(default_factory=list)
    tools_count: int = 0


class ErrorResponse(BaseModel):
    """Standard error body."""

    detail: str
