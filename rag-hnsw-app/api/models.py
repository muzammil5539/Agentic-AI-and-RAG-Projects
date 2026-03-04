from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
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


class UploadResponse(BaseModel):
    filename: str
    num_chunks: int
    message: str


class DocumentInfo(BaseModel):
    filename: str
    chunk_count: int


class CollectionStatsResponse(BaseModel):
    total_chunks: int
    documents: list[DocumentInfo]
