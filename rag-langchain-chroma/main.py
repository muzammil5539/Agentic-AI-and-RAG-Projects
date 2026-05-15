import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from api.api_routes import router
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast if the OpenAI key is missing
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Add it to rag-langchain-chroma/.env or set it as an environment variable."
        )
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    yield


app = FastAPI(title="RAG LangChain Chroma", version="1.0.0", lifespan=lifespan)

app.include_router(router)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
