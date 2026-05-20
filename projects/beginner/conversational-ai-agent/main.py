"""
Conversational AI Agent — FastAPI entry point.
ReAct agent with LangGraph orchestration, tool calling, and WebSocket streaming.
"""

import os
import logging
import logging.handlers
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings

# ── Logging ──────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_fmt = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_file_handler = logging.handlers.RotatingFileHandler(
    _LOG_DIR / "app.log",
    maxBytes=10_000_000,
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(_fmt)
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _console_handler])
logger = logging.getLogger("agent_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    from memory.checkpointer import get_checkpointer

    checkpointer = get_checkpointer()
    app.state.checkpointer = checkpointer

    logger.info("SQLite checkpointer ready at %s", settings.SQLITE_DB_PATH)
    logger.info("Chroma RAG tool targeting %s", settings.CHROMA_URL)
    logger.info("Available models: %s", settings.AVAILABLE_MODELS)
    logger.info("Ready at http://localhost:%d", settings.PORT)

    yield

    # ── Shutdown ─────────────────────────────────────────
    logger.info("Shutting down.")


app = FastAPI(
    title="Conversational AI Agent",
    description=(
        "ReAct-style AI agent with tool calling, "
        "visible thought process, and WebSocket streaming."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────
from api.routes.health import router as health_router
from api.routes.chat import router as chat_router
from api.routes.sessions import router as sessions_router
from api.routes.tools import router as tools_router
from api.routes.documents import router as documents_router

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(tools_router)
app.include_router(documents_router)


# ── SPA fallback (serves frontend build if present) ──────────────
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        reload_excludes=["logs/*", "data/*", "frontend/*"],
    )
