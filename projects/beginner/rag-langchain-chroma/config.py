from pydantic_settings import BaseSettings
from pathlib import Path

# Always resolve .env relative to this file, not the CWD
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = str(Path(__file__).parent / "data" / "chroma_db")
    CHROMA_COLLECTION_NAME: str = "rag_documents"

    # HNSW parameters
    HNSW_SPACE: str = "cosine"
    HNSW_EF_CONSTRUCTION: int = 200
    HNSW_EF_SEARCH: int = 150
    HNSW_MAX_NEIGHBORS: int = 16

    # Chunking
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Retrieval
    VECTOR_SEARCH_K: int = 5
    BM25_SEARCH_K: int = 5
    VECTOR_WEIGHT: float = 0.5
    BM25_WEIGHT: float = 0.5

    # Paths
    UPLOAD_DIR: str = str(Path(__file__).parent / "data" / "uploads")

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


settings = Settings()
