"""
Conversational AI Agent — Configuration.
All settings via Pydantic BaseSettings with .env support.
"""

from pydantic_settings import BaseSettings
from pathlib import Path

_ENV_FILE = Path(__file__).parent / ".env"
_DATA_DIR = Path(__file__).parent / "data"


class Settings(BaseSettings):
    # ── Defaults (user provides their own key per-request) ───────
    DEFAULT_MODEL: str = "gpt-4o-mini"
    AVAILABLE_MODELS: list[str] = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4.1-mini",
        "gpt-4.1",
        "o4-mini",
    ]

    # ── Agent ────────────────────────────────────────────────────
    MAX_ITERATIONS: int = 10
    SYSTEM_PROMPT_FILE: str = ""

    # ── Chroma (RAG tool) ────────────────────────────────────────
    CHROMA_URL: str = "http://localhost:8000"
    CHROMA_COLLECTION: str = "agent_docs"

    # ── Weather (Open-Meteo) ─────────────────────────────────────
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    OPEN_METEO_GEOCODING_URL: str = "https://geocoding-api.open-meteo.com/v1"

    # ── Paths ────────────────────────────────────────────────────
    DATA_DIR: str = str(_DATA_DIR)
    UPLOAD_DIR: str = str(_DATA_DIR / "uploads")
    SQLITE_DB_PATH: str = str(_DATA_DIR / "agent.db")
    SESSIONS_FILE: str = str(_DATA_DIR / "sessions.json")

    # ── Server ───────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


settings = Settings()
