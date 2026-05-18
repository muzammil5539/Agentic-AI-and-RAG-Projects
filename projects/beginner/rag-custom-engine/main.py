"""
RAG Custom Engine — FastAPI entry point.
Every RAG component built from scratch: vector store, BM25, HNSW, hybrid retrieval.
No LangChain, no ChromaDB.
"""

import os
import sys
import time
import logging
import logging.handlers
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings

# ── Logging setup ────────────────────────────────────────────────
# Write logs ONE level above the app dir so watchfiles reload doesn't
# trigger on every log write.
_LOG_DIR = Path(__file__).parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_fmt = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_file_handler = logging.handlers.RotatingFileHandler(
    _LOG_DIR / "app.log",
    maxBytes=10_000_000,   # 10 MB per file
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(_fmt)
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _console_handler])
logger = logging.getLogger("rag_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set. Create a .env file with your key.")
        sys.exit(1)

    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    from indexing.hnsw_vector_store import get_vector_store
    from indexing.bm25_index import get_bm25_index
    from memory.trace_store import get_trace_store
    store = get_vector_store()
    bm25 = get_bm25_index()
    trace_store = get_trace_store()

    logger.info("Vector store: %d entries loaded", store.count())
    logger.info("BM25 index:   %d documents loaded", bm25.count())
    logger.info("Trace store:  %d sessions with traces", len(trace_store._traces))
    logger.info("Method:       %s", store.method)
    logger.info("Ready at http://localhost:8001")

    yield

    # ── Shutdown ─────────────────────────────────────────
    store.save()
    bm25.save(settings.BM25_INDEX_FILE)
    logger.info("Stores persisted to disk.")


app = FastAPI(
    title="RAG Custom Engine",
    description="Complete RAG pipeline built from scratch — no LangChain, no ChromaDB",
    lifespan=lifespan,
)


# ── Request / response logging middleware ────────────────────────
@app.middleware("http")
async def _log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "%s %s → %d  (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include API routes
from api.api_routes import router
app.include_router(router)


@app.get("/")
async def serve_spa():
    return FileResponse(str(static_dir / "index.html"))


if __name__ == "__main__":
    import uvicorn
    _base = Path(__file__).parent
    # Only watch source directories — this prevents tests/, .pytest_cache/,
    # data/, static/ from triggering unnecessary reloads.
    # Watch only source subdirs — do NOT include the root dir or tests/
    # so that .pytest_cache creation never triggers a reload.
    _watch_dirs = [
        str(_base / "api"),
        str(_base / "indexing"),
        str(_base / "generation"),
        str(_base / "memory"),
        str(_base / "orchestration"),
        str(_base / "retrieval"),
    ]
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=_watch_dirs,
        reload_excludes=[
            "*/tests/*", "*/tests/**",
            "*/.pytest_cache/*", "*/.pytest_cache/**",
            "*/data/*",
            "*.pyc",
        ],
    )
