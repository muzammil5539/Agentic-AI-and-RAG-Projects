import os
import shutil
from collections import Counter

from fastapi import APIRouter, UploadFile, File, HTTPException
from api.models import (
    QueryRequest,
    QueryResponse,
    UploadResponse,
    CollectionStatsResponse,
)
from ingestion.loader import load_document
from ingestion.chunker import chunk_documents
from vectorstore.chroma_store import add_documents, get_vectorstore
from retrieval.hybrid_retriever import get_ensemble_retriever, refresh_bm25
from generation.chain import generate_answer
from config import settings

router = APIRouter(prefix="/api")

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv"}


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        docs = load_document(file_path)
        chunks = chunk_documents(docs)
        if not chunks:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the file. The document may be empty, image-only, or encrypted.",
            )
        add_documents(chunks)
        refresh_bm25()
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    return UploadResponse(
        filename=file.filename,
        num_chunks=len(chunks),
        message=f"Successfully ingested {len(chunks)} chunks from {file.filename}.",
    )


@router.post("/query", response_model=QueryResponse)
async def query_documents(req: QueryRequest):
    store = get_vectorstore()
    all_data = store.get(include=["metadatas"])
    if not all_data["metadatas"]:
        raise HTTPException(
            status_code=400,
            detail="No documents ingested yet. Please upload documents first.",
        )

    try:
        retriever = get_ensemble_retriever()
        retrieved_docs = retriever.invoke(req.question)
        result = generate_answer(req.question, retrieved_docs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

    return QueryResponse(**result)


@router.get("/documents", response_model=CollectionStatsResponse)
async def list_documents():
    store = get_vectorstore()
    all_data = store.get(include=["metadatas"])
    counts = Counter(
        m.get("source_filename", "Unknown") for m in all_data["metadatas"]
    )
    docs = [{"filename": k, "chunk_count": v} for k, v in counts.items()]
    return CollectionStatsResponse(
        total_chunks=len(all_data["metadatas"]),
        documents=docs,
    )


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    store = get_vectorstore()
    all_data = store.get(include=["metadatas"])

    ids_to_delete = []
    for doc_id, meta in zip(all_data["ids"], all_data["metadatas"]):
        if meta.get("source_filename") == filename:
            ids_to_delete.append(doc_id)

    if not ids_to_delete:
        raise HTTPException(status_code=404, detail=f"No document found: {filename}")

    store.delete(ids=ids_to_delete)
    refresh_bm25()

    upload_path = os.path.join(settings.UPLOAD_DIR, filename)
    if os.path.exists(upload_path):
        os.remove(upload_path)

    return {"message": f"Deleted {len(ids_to_delete)} chunks from {filename}"}
