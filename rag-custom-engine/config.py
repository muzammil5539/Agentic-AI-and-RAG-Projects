from pydantic_settings import BaseSettings
from pathlib import Path

_ENV_FILE = Path(__file__).parent / ".env"
_DATA_DIR = Path(__file__).parent / "data"


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    # HNSW parameters
    HNSW_M: int = 16
    HNSW_EF_CONSTRUCTION: int = 200
    HNSW_EF_SEARCH: int = 150

    # Chunking
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Retrieval
    VECTOR_SEARCH_K: int = 5
    BM25_SEARCH_K: int = 5
    VECTOR_WEIGHT: float = 0.5
    BM25_WEIGHT: float = 0.5

    # Paths
    DATA_DIR: str = str(_DATA_DIR)
    UPLOAD_DIR: str = str(_DATA_DIR / "uploads")
    VECTOR_STORE_FILE: str = str(_DATA_DIR / "vector_store.json")
    BM25_INDEX_FILE: str = str(_DATA_DIR / "bm25_index.json")
    SESSIONS_FILE: str = str(_DATA_DIR / "sessions.json")
    CROSS_CHAT_FILE: str = str(_DATA_DIR / "cross_session_settings.json")
    CHAT_MEMORY_FILE: str = str(_DATA_DIR / "chat_memory.json")
    TRACES_FILE: str = str(_DATA_DIR / "traces.json")

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


settings = Settings()
