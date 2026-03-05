import os
import shutil
from collections import Counter

from fastapi import APIRouter, UploadFile, File, HTTPException
from api.models import (
    QueryRequest,
    QueryResponse,
    UploadResponse,
    CollectionStatsResponse,
    SetSharedRequest,
    SessionListResponse,
    SessionMessagesResponse,
    RenameSessionRequest,
    ChatSession,
    ChatMemoryEntry,
    ChatMemoryListResponse,
)
from ingestion.loader import load_document
from ingestion.chunker import chunk_documents
from vectorstore.chroma_store import add_documents, get_vectorstore
from retrieval.hybrid_retriever import get_ensemble_retriever, refresh_bm25
from generation.chain import generate_answer
from memory.session_store import session_store
from memory.cross_chat_store import cross_chat_store
from memory.chat_memory_store import chat_memory_store
from config import settings

router = APIRouter(prefix="/api")

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".md"}


# ===========================================================================
# Documents – Upload / List / Delete
# ===========================================================================

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
                detail=(
                    "No text could be extracted from the file. "
                    "The document may be empty, image-only, or encrypted."
                ),
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


@router.get("/documents", response_model=CollectionStatsResponse)
async def list_documents():
    store = get_vectorstore()
    all_data = store.get(include=["metadatas"])
    counts = Counter(
        m.get("source_filename", "Unknown") for m in all_data["metadatas"]
    )
    docs = [
        {
            "filename": k,
            "chunk_count": v,
            "is_shared": cross_chat_store.is_shared(k),
        }
        for k, v in counts.items()
    ]
    return CollectionStatsResponse(
        total_chunks=len(all_data["metadatas"]),
        documents=docs,
    )


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    store = get_vectorstore()
    all_data = store.get(include=["metadatas"])

    ids_to_delete = [
        doc_id
        for doc_id, meta in zip(all_data["ids"], all_data["metadatas"])
        if meta.get("source_filename") == filename
    ]

    if not ids_to_delete:
        raise HTTPException(status_code=404, detail=f"No document found: {filename}")

    store.delete(ids=ids_to_delete)
    refresh_bm25()
    cross_chat_store.remove_document(filename)

    upload_path = os.path.join(settings.UPLOAD_DIR, filename)
    if os.path.exists(upload_path):
        os.remove(upload_path)

    return {"message": f"Deleted {len(ids_to_delete)} chunks from {filename}"}


# ===========================================================================
# Cross-Chat Document Sharing
# ===========================================================================

@router.put("/documents/{filename}/shared")
async def set_document_shared(filename: str, req: SetSharedRequest):
    """Toggle whether a document is shared across all chat sessions."""
    store = get_vectorstore()
    all_data = store.get(include=["metadatas"])
    known = {m.get("source_filename") for m in all_data["metadatas"]}
    if filename not in known:
        raise HTTPException(status_code=404, detail=f"No document found: {filename}")
    cross_chat_store.set_shared(filename, req.shared)
    return {"filename": filename, "is_shared": req.shared}


@router.get("/shared-documents")
async def get_shared_documents():
    """Return the list of documents currently marked as cross-chat shared."""
    return {"shared_documents": cross_chat_store.get_shared_documents()}


# ===========================================================================
# Chat Sessions
# ===========================================================================

@router.post("/sessions")
async def create_session():
    session = session_store.create_session()
    return _session_to_model(session)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    sessions = session_store.list_sessions()
    return SessionListResponse(sessions=[_session_to_model(s) for s in sessions])


@router.get("/sessions/{session_id}", response_model=SessionMessagesResponse)
async def get_session(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionMessagesResponse(
        session_id=session_id,
        messages=session.get("messages", []),
    )


@router.put("/sessions/{session_id}/rename")
async def rename_session(session_id: str, req: RenameSessionRequest):
    if not session_store.rename_session(session_id, req.title):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "title": req.title}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Auto-archive into cross-chat memory before deletion
    messages = session.get("messages", [])
    if messages:
        try:
            chat_memory_store.summarize_and_store(
                session_id=session_id,
                session_title=session.get("title", "Untitled Chat"),
                messages=messages,
            )
        except Exception:
            pass  # archive failure must not block deletion

    session_store.delete_session(session_id)
    return {"message": f"Session {session_id} deleted and archived to memory"}


@router.post("/sessions/{session_id}/clear")
async def clear_session_history(session_id: str):
    if not session_store.clear_history(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Chat history cleared"}


@router.post("/sessions/{session_id}/archive")
async def archive_session(session_id: str):
    """
    Manually summarise and store a session in Cross-Chat Memory
    without deleting it.  Safe to call multiple times — always
    upserts the latest state.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.get("messages", [])
    if not messages:
        raise HTTPException(
            status_code=400,
            detail="Session has no messages to archive.",
        )

    try:
        summary = chat_memory_store.summarize_and_store(
            session_id=session_id,
            session_title=session.get("title", "Untitled Chat"),
            messages=messages,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Archiving failed: {exc}",
        )

    return {
        "message": "Session archived to Cross-Chat Memory.",
        "session_id": session_id,
        "summary_preview": (summary or "")[:300],
    }


# ===========================================================================
# Query
# ===========================================================================

@router.post("/query", response_model=QueryResponse)
async def query_documents(req: QueryRequest):
    store = get_vectorstore()
    all_data = store.get(include=["metadatas"])
    if not all_data["metadatas"]:
        raise HTTPException(
            status_code=400,
            detail="No documents ingested yet. Please upload documents first.",
        )

    # Get or create the session for this query
    session = session_store.get_or_create(req.session_id)
    session_id = session["id"]

    # ── Memory Type 1: In-Chat history ───────────────────────────────────
    chat_history = session_store.get_history(session_id)

    # ── Memory Type 2: Cross-Chat memory (semantic search over archived
    #    conversation summaries from all previous sessions) ───────────────
    cross_chat_docs = chat_memory_store.search_relevant(req.question, k=3)

    try:
        retriever    = get_ensemble_retriever()
        retrieved_docs = retriever.invoke(req.question)
        result = generate_answer(
            req.question,
            retrieved_docs,
            chat_history,
            cross_chat_docs,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

    # Persist user message and assistant reply
    session_store.add_message(session_id, "user", req.question)
    session_store.add_message(session_id, "assistant", result["answer"])

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        session_id=session_id,
        cross_chat_refs=result.get("cross_chat_refs", []),
    )


# ===========================================================================
# Cross-Chat Memory  (archived conversation summaries)
# ===========================================================================

@router.get("/chat-memory", response_model=ChatMemoryListResponse)
async def list_chat_memory():
    """Return all archived conversation summaries."""
    entries = chat_memory_store.list_all()
    return ChatMemoryListResponse(
        entries=[
            ChatMemoryEntry(
                id=e["id"],
                session_id=e["session_id"],
                session_title=e["session_title"],
                summary=e["summary"],
                message_count=e["message_count"],
                archived_at=e["archived_at"],
            )
            for e in entries
        ],
        total=len(entries),
    )


@router.delete("/chat-memory/{session_id}")
async def delete_chat_memory_entry(session_id: str):
    """Remove the archived memory for a specific session."""
    deleted = chat_memory_store.delete_by_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No memory entry found for session {session_id}",
        )
    return {"message": f"Memory entry for session {session_id} deleted."}


# ===========================================================================
# Helper
# ===========================================================================

def _session_to_model(session: dict) -> ChatSession:
    return ChatSession(
        id=session["id"],
        title=session.get("title", "New Chat"),
        created_at=session.get("created_at", ""),
        updated_at=session.get("updated_at", session.get("created_at", "")),
        message_count=len(session.get("messages", [])),
    )
