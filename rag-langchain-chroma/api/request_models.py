from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    vector_weight: float | None = 0.5
    num_results: int | None = 5


class SourceReference(BaseModel):
    filename: str
    page: int | str
    chunk_index: int | str
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    session_id: str
    cross_chat_refs: list["CrossChatRef"] = []


class CrossChatRef(BaseModel):
    session_id: str
    session_title: str
    archived_at: str
    snippet: str


# ---------------------------------------------------------------------------
# Upload / Documents
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    filename: str
    num_chunks: int
    message: str


class DocumentInfo(BaseModel):
    filename: str
    chunk_count: int
    is_shared: bool = False


class CollectionStatsResponse(BaseModel):
    total_chunks: int
    documents: list[DocumentInfo]


class SetSharedRequest(BaseModel):
    shared: bool


# ---------------------------------------------------------------------------
# Chat Sessions
# ---------------------------------------------------------------------------

class ChatSession(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class SessionListResponse(BaseModel):
    sessions: list[ChatSession]


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[dict]


class RenameSessionRequest(BaseModel):
    title: str


# ---------------------------------------------------------------------------
# Cross-Chat Memory
# ---------------------------------------------------------------------------

class ChatMemoryEntry(BaseModel):
    id: str
    session_id: str
    session_title: str
    summary: str
    message_count: int
    archived_at: str


class ChatMemoryListResponse(BaseModel):
    entries: list[ChatMemoryEntry]
    total: int
