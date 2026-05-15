from typing import Optional
from pydantic import BaseModel


# ─────────────────────── Pipeline Config ────────────────────────

class PipelineConfigRequest(BaseModel):
    use_multi_query: bool = False
    use_self_rag: bool = False
    use_compression: bool = False
    vector_method: str = "brute_force"
    merge_method: str = "weighted"
    vector_k: int = 5
    bm25_k: int = 5
    top_k: int = 5
    vector_weight: float = 0.5
    bm25_weight: float = 0.5


# ─────────────────────── Query ──────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    pipeline_config: Optional[PipelineConfigRequest] = None


class PipelineStepModel(BaseModel):
    name: str
    status: str
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0
    details: dict = {}


class SourceReference(BaseModel):
    filename: str
    page: int | str
    chunk_index: int | str
    snippet: str


class CrossChatRef(BaseModel):
    session_id: str
    session_title: str
    archived_at: str
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    session_id: str
    cross_chat_refs: list[CrossChatRef] = []
    pipeline_steps: list[PipelineStepModel] = []


# ─────────────────────── Upload / Documents ─────────────────────

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


# ─────────────────────── Sessions ───────────────────────────────

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


# ─────────────────────── Cross-Chat Memory ──────────────────────

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


# ─────────────────────── Stats ──────────────────────────────────

class StatsResponse(BaseModel):
    vector_store: dict
    bm25: dict
    sessions: int
    chat_memories: int


# ─────────────────────── Pipeline Traces ────────────────────────

class TraceStepModel(BaseModel):
    name: str
    status: str
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0
    details: dict = {}


class TraceRecord(BaseModel):
    trace_id: str
    session_id: str
    turn_index: int
    query: str
    started_at: str
    total_duration_ms: float
    steps: list[TraceStepModel]


class SessionTracesResponse(BaseModel):
    session_id: str
    traces: list[TraceRecord]
