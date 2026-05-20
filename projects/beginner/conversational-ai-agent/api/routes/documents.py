"""Document upload endpoint — indexes files into Chroma for RAG search."""

from __future__ import annotations

import logging
from typing import Annotated

import chromadb
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.dependencies import get_api_key, get_user_id
from api.models.responses import DocumentUploadResponse
from config import settings

logger = logging.getLogger("agent_app.documents")

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: Annotated[UploadFile, File(description="Document to upload")],
    api_key: Annotated[str, Depends(get_api_key)],
    user_id: Annotated[str, Depends(get_user_id)],
    collection: str = "agent_docs",
) -> DocumentUploadResponse:
    """Upload a document and index it into Chroma for RAG search."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Read content
    content = await file.read()
    text = ""

    try:
        if file.filename.endswith(".txt") or file.filename.endswith(".md"):
            text = content.decode("utf-8")
        elif file.filename.endswith(".pdf"):
            try:
                import pypdf
                import io

                reader = pypdf.PdfReader(io.BytesIO(content))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                raise HTTPException(
                    status_code=400,
                    detail="pypdf not installed. Install with: pip install pypdf",
                )
        else:
            # Try to decode as text
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.filename}",
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty or unreadable")

    # Chunk and index
    chunks = _chunk_text(text)

    try:
        client = chromadb.HttpClient(
            host=settings.CHROMA_URL.replace("http://", "").split(":")[0],
            port=int(settings.CHROMA_URL.split(":")[-1]),
        )
        coll = client.get_or_create_collection(name=collection)

        ids = [f"{file.filename}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"source": file.filename, "chunk_index": i, "user_id": user_id}
            for i in range(len(chunks))
        ]
        coll.upsert(ids=ids, documents=chunks, metadatas=metadatas)

        logger.info(
            "Indexed %d chunks from '%s' into collection '%s'",
            len(chunks),
            file.filename,
            collection,
        )

    except Exception as e:
        logger.exception("Chroma indexing failed")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to index document: {e}. Is Chroma running at {settings.CHROMA_URL}?",
        )

    return DocumentUploadResponse(
        filename=file.filename,
        num_chunks=len(chunks),
        collection=collection,
        message=f"Successfully indexed {len(chunks)} chunks from '{file.filename}'",
    )
