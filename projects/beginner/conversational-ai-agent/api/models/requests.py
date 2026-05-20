"""Pydantic request models for the Conversational AI Agent API."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Body for POST /api/v1/chat."""

    query: str = Field(..., min_length=1, max_length=10_000)
    session_id: str | None = Field(
        default=None,
        description="Existing session ID. Omit to create a new session.",
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use for this request.",
    )


class SessionCreateRequest(BaseModel):
    """Body for POST /api/v1/sessions."""

    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional title. Auto-generated from first message if omitted.",
    )


class DocumentUploadMeta(BaseModel):
    """Optional metadata sent alongside a file upload."""

    collection: str = Field(
        default="agent_docs",
        description="Chroma collection to index the document into.",
    )
