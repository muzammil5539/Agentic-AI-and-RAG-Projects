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
    description="""
## Overview

A **ReAct-style AI agent** powered by LangGraph that reasons step-by-step, calls tools,
and streams its thought process in real time over WebSocket.

### Authentication

All endpoints that interact with the LLM require an **OpenAI API key** passed in the
`X-API-Key` header. The key is forwarded to OpenAI per-request and **never stored**.
A SHA-256 hash of the key is used internally as a `user_id` for session isolation.

```
X-API-Key: sk-...
```

### Ports

| Service | Port |
|---------|------|
| Backend (this API) | `8002` |
| Frontend (Next.js) | `3000` |
| Chroma vector DB | `8000` |

### WebSocket Streaming

Connect to `ws://localhost:8002/ws/chat` for real-time streaming.

**Send one JSON message per query:**
```json
{
  "type": "chat",
  "query": "What's the weather in Tokyo?",
  "session_id": null,
  "model": "gpt-4o-mini",
  "api_key": "sk-..."
}
```

**Receive a stream of typed events:**
| Event type | Description |
|-----------|-------------|
| `thought` | Agent reasoning step |
| `tool_call` | Tool being invoked (name + args) |
| `tool_result` | Tool output |
| `token` | Streamed answer token |
| `done` | Final event — includes `session_id` and `model` |
| `error` | Error message |

### Agent Tools

| Tool | Type | Description |
|------|------|-------------|
| `calculator` | Custom | Safe AST-based math (arithmetic, sqrt, trig, log) |
| `weather` | Custom | Open-Meteo weather forecast — no API key needed |
| `datetime_tool` | Custom | Current time, timezone convert, date arithmetic |
| `web_search` | OpenAI | Web search via OpenAI built-in |
| `code_interpreter` | OpenAI | Python code execution via OpenAI built-in |
| `rag_search` | Custom | Similarity search on uploaded documents (Chroma) |
""",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and server status. No authentication required.",
        },
        {
            "name": "chat",
            "description": (
                "Send messages to the ReAct agent. "
                "Use the REST endpoint for a single request/response, "
                "or the WebSocket endpoint (`/ws/chat`) for real-time streaming with "
                "visible thought process."
            ),
        },
        {
            "name": "sessions",
            "description": (
                "Manage conversation sessions. Sessions persist chat history "
                "using the LangGraph SQLite checkpointer. "
                "Each session is isolated per API key (user). "
                "Requires `X-API-Key` header."
            ),
        },
        {
            "name": "tools",
            "description": (
                "Inspect available agent tools and their input schemas. "
                "No authentication required."
            ),
        },
        {
            "name": "documents",
            "description": (
                "Upload documents for RAG (Retrieval-Augmented Generation) search. "
                "Uploaded files are chunked and indexed into ChromaDB. "
                "Use the `rag_search` tool to query them. "
                "Requires `X-API-Key` header."
            ),
        },
    ],
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
