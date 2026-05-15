"""
API routes — all REST endpoints for the RAG from scratch app.
"""

import os
import time
import asyncio
import logging
import shutil
from collections import Counter

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from api.request_models import (
    QueryRequest, QueryResponse, PipelineStepModel,
    UploadResponse, CollectionStatsResponse, DocumentInfo,
    SetSharedRequest, SessionListResponse, SessionMessagesResponse,
    RenameSessionRequest, ChatSession, ChatMemoryEntry,
    ChatMemoryListResponse, StatsResponse,
    TraceRecord, SessionTracesResponse,
)
from config import settings

logger = logging.getLogger("rag.routes")
router = APIRouter(prefix="/api")

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".md"}


# ═══════════════════════════════════════════════════════════════════
# Documents – Upload / List / Delete
# ═══════════════════════════════════════════════════════════════════

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

    # Save uploaded file (async-safe: write bytes we already have in memory)
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    def _ingest():
        from indexing.document_loader import load_document
        from indexing.text_splitter import chunk_documents
        from indexing.openai_embeddings import embed_texts
        from indexing.hnsw_vector_store import get_vector_store
        from indexing.bm25_index import get_bm25_index
        from retrieval.hybrid_search import DOC_NAMESPACE

        docs = load_document(file_path)
        chunks = chunk_documents(docs, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)

        if not chunks:
            return None  # signal empty doc

        texts = [c["content"] for c in chunks]
        vectors = embed_texts(texts)

        store = get_vector_store()
        metadatas = [c["metadata"] for c in chunks]
        store.add(vectors, texts, metadatas, namespace=DOC_NAMESPACE)

        bm25 = get_bm25_index()
        ids = [
            f"{c['metadata'].get('source_filename', '')}_{c['metadata'].get('chunk_index', i)}"
            for i, c in enumerate(chunks)
        ]
        bm25.add_documents(ids, texts, metadatas)
        bm25.save(settings.BM25_INDEX_FILE)
        return chunks

    try:
        loop = asyncio.get_running_loop()
        chunks = await loop.run_in_executor(None, _ingest)

        if chunks is None:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted. The document may be empty or image-only.",
            )

    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    logger.info("Uploaded '%s' → %d chunks", file.filename, len(chunks))
    return UploadResponse(
        filename=file.filename,
        num_chunks=len(chunks),
        message=f"Successfully ingested {len(chunks)} chunks from {file.filename}.",
    )


@router.get("/documents", response_model=CollectionStatsResponse)
async def list_documents():
    from indexing.hnsw_vector_store import get_vector_store
    from retrieval.hybrid_search import DOC_NAMESPACE
    from memory.cross_session_memory import get_cross_chat_doc_store

    store = get_vector_store()
    entries = store.get_all(namespace=DOC_NAMESPACE)
    counts = Counter(e.metadata.get("source_filename", "Unknown") for e in entries)
    cross_chat = get_cross_chat_doc_store()

    docs = [
        DocumentInfo(
            filename=k,
            chunk_count=v,
            is_shared=cross_chat.is_shared(k),
        )
        for k, v in counts.items()
    ]
    return CollectionStatsResponse(total_chunks=len(entries), documents=docs)


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    from indexing.hnsw_vector_store import get_vector_store
    from indexing.bm25_index import get_bm25_index
    from retrieval.hybrid_search import DOC_NAMESPACE
    from memory.cross_session_memory import get_cross_chat_doc_store

    store = get_vector_store()
    count = store.delete_by_metadata("source_filename", filename, namespace=DOC_NAMESPACE)

    if count == 0:
        raise HTTPException(status_code=404, detail=f"No document found: {filename}")

    logger.info("Deleted '%s' (%d chunks)", filename, count)
    # Remove from BM25
    bm25 = get_bm25_index()
    bm25.remove_by_metadata("source_filename", filename)
    bm25.save(settings.BM25_INDEX_FILE)

    # Remove sharing flag
    cross_chat = get_cross_chat_doc_store()
    cross_chat.remove_document(filename)

    # Remove uploaded file
    upload_path = os.path.join(settings.UPLOAD_DIR, filename)
    if os.path.exists(upload_path):
        os.remove(upload_path)

    return {"message": f"Deleted {count} chunks from {filename}"}


# ═══════════════════════════════════════════════════════════════════
# Cross-Chat Document Sharing
# ═══════════════════════════════════════════════════════════════════

@router.put("/documents/{filename}/shared")
async def set_document_shared(filename: str, req: SetSharedRequest):
    from indexing.hnsw_vector_store import get_vector_store
    from retrieval.hybrid_search import DOC_NAMESPACE
    from memory.cross_session_memory import get_cross_chat_doc_store

    store = get_vector_store()
    entries = store.get_all(namespace=DOC_NAMESPACE)
    known = {e.metadata.get("source_filename") for e in entries}
    if filename not in known:
        raise HTTPException(status_code=404, detail=f"No document found: {filename}")
    cross_chat = get_cross_chat_doc_store()
    cross_chat.set_shared(filename, req.shared)
    return {"filename": filename, "is_shared": req.shared}


@router.get("/shared-documents")
async def get_shared_documents():
    from memory.cross_session_memory import get_cross_chat_doc_store
    cross_chat = get_cross_chat_doc_store()
    return {"shared_documents": cross_chat.get_shared_documents()}


# ═══════════════════════════════════════════════════════════════════
# Chat Sessions
# ═══════════════════════════════════════════════════════════════════

@router.post("/sessions")
async def create_session():
    from memory.session_history_store import session_store
    session = session_store.create_session()
    return _session_to_model(session)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    from memory.session_history_store import session_store
    sessions = session_store.list_sessions()
    return SessionListResponse(sessions=[_session_to_model(s) for s in sessions])


@router.get("/sessions/{session_id}", response_model=SessionMessagesResponse)
async def get_session(session_id: str):
    from memory.session_history_store import session_store
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionMessagesResponse(
        session_id=session_id,
        messages=session.get("messages", []),
    )


@router.get("/sessions/{session_id}/traces", response_model=SessionTracesResponse)
async def get_session_traces(session_id: str):
    from memory.trace_store import get_trace_store
    traces = get_trace_store().get_traces(session_id)
    return SessionTracesResponse(session_id=session_id, traces=traces)


@router.put("/sessions/{session_id}/rename")
async def rename_session(session_id: str, req: RenameSessionRequest):
    from memory.session_history_store import session_store
    if not session_store.rename_session(session_id, req.title):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "title": req.title}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    from memory.session_history_store import session_store
    from memory.cross_session_memory import get_chat_memory_store
    from memory.trace_store import get_trace_store

    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Auto-archive before deletion
    messages = session.get("messages", [])
    if messages:
        try:
            memory_store = get_chat_memory_store()
            memory_store.summarize_and_store(
                session_id=session_id,
                session_title=session.get("title", "Untitled Chat"),
                messages=messages,
            )
        except Exception:
            pass  # Archive failure must not block deletion

    session_store.delete_session(session_id)
    get_trace_store().delete_traces(session_id)
    return {"message": f"Session {session_id} deleted and archived to memory"}


@router.post("/sessions/{session_id}/clear")
async def clear_session_history(session_id: str):
    from memory.session_history_store import session_store
    from memory.trace_store import get_trace_store
    if not session_store.clear_history(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    get_trace_store().delete_traces(session_id)
    return {"message": "Chat history cleared"}


@router.post("/sessions/{session_id}/archive")
async def archive_session(session_id: str):
    from memory.session_history_store import session_store
    from memory.cross_session_memory import get_chat_memory_store

    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="Session has no messages to archive.")

    try:
        memory_store = get_chat_memory_store()
        summary = memory_store.summarize_and_store(
            session_id=session_id,
            session_title=session.get("title", "Untitled Chat"),
            messages=messages,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Archiving failed: {exc}")

    return {
        "message": "Session archived to Cross-Chat Memory.",
        "session_id": session_id,
        "summary_preview": (summary or "")[:300],
    }


# ═══════════════════════════════════════════════════════════════════
# Query — Main RAG Pipeline
# ═══════════════════════════════════════════════════════════════════

@router.post("/query", response_model=QueryResponse)
async def query_documents(req: QueryRequest):
    from indexing.hnsw_vector_store import get_vector_store
    from retrieval.hybrid_search import DOC_NAMESPACE
    from memory.session_history_store import session_store
    from orchestration.rag_orchestrator import run_pipeline, PipelineConfig

    store = get_vector_store()
    if store.count(namespace=DOC_NAMESPACE) == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents ingested yet. Please upload documents first.",
        )

    # Get or create session
    session = session_store.get_or_create(req.session_id)
    session_id = session["id"]
    chat_history = session_store.get_history(session_id)

    # Build pipeline config
    pc = req.pipeline_config
    config = PipelineConfig(
        use_multi_query=pc.use_multi_query if pc else False,
        use_self_rag=pc.use_self_rag if pc else False,
        use_compression=pc.use_compression if pc else False,
        vector_method=pc.vector_method if pc else "brute_force",
        merge_method=pc.merge_method if pc else "weighted",
        vector_k=pc.vector_k if pc else settings.VECTOR_SEARCH_K,
        bm25_k=pc.bm25_k if pc else settings.BM25_SEARCH_K,
        top_k=pc.top_k if pc else 5,
        vector_weight=pc.vector_weight if pc else settings.VECTOR_WEIGHT,
        bm25_weight=pc.bm25_weight if pc else settings.BM25_WEIGHT,
    )

    result = run_pipeline(req.question, session_id, chat_history, config)

    # Persist messages
    session_store.add_message(session_id, "user", req.question)
    session_store.add_message(session_id, "assistant", result.answer)

    return QueryResponse(
        answer=result.answer,
        sources=result.sources,
        session_id=session_id,
        cross_chat_refs=result.cross_chat_refs,
        pipeline_steps=[
            PipelineStepModel(**s.to_dict()) for s in result.steps
        ],
    )


@router.post("/query/stream")
async def query_documents_stream(req: QueryRequest):
    """
    Streaming RAG pipeline via Server-Sent Events.

    Each SSE event is: `data: {json}\\n\\n`
    Event types: step_start | step_complete | answer | error
    """
    from indexing.hnsw_vector_store import get_vector_store
    from retrieval.hybrid_search import DOC_NAMESPACE
    from memory.session_history_store import session_store
    from orchestration.rag_orchestrator import stream_pipeline, PipelineConfig

    store = get_vector_store()
    if store.count(namespace=DOC_NAMESPACE) == 0:
        # Return SSE error immediately
        async def _error_gen():
            import json
            yield f'data: {json.dumps({"type": "error", "data": {"message": "No documents ingested yet. Please upload documents first."}})}\n\n'
        return StreamingResponse(
            _error_gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    session = session_store.get_or_create(req.session_id)
    session_id = session["id"]
    chat_history = session_store.get_history(session_id)

    pc = req.pipeline_config
    config = PipelineConfig(
        use_multi_query=pc.use_multi_query if pc else False,
        use_self_rag=pc.use_self_rag if pc else False,
        use_compression=pc.use_compression if pc else False,
        vector_method=pc.vector_method if pc else "brute_force",
        merge_method=pc.merge_method if pc else "weighted",
        vector_k=pc.vector_k if pc else settings.VECTOR_SEARCH_K,
        bm25_k=pc.bm25_k if pc else settings.BM25_SEARCH_K,
        top_k=pc.top_k if pc else 5,
        vector_weight=pc.vector_weight if pc else settings.VECTOR_WEIGHT,
        bm25_weight=pc.bm25_weight if pc else settings.BM25_WEIGHT,
    )

    logger.info("Stream query | session=%s | q=%.80s | cfg=%s", session_id, req.question,
                 {"mq": config.use_multi_query, "sr": config.use_self_rag,
                  "cx": config.use_compression, "vm": config.vector_method})

    async def _event_generator():
        answer = ""
        t0 = time.perf_counter()
        try:
            async for event in stream_pipeline(req.question, session_id, chat_history, config):
                yield event
                # After the answer event, persist messages
                if '"type": "answer"' in event:
                    import json as _json
                    try:
                        payload = _json.loads(event[len("data: "):].strip())
                        answer = payload.get("data", {}).get("answer", "")
                    except Exception:
                        pass
        except Exception as exc:
            logger.exception("stream_pipeline raised: %s", exc)
            import json as _json
            yield f'data: {_json.dumps({"type": "error", "data": {"message": str(exc)}})}\n\n'
        finally:
            elapsed = round((time.perf_counter() - t0) * 1000)
            logger.info("Stream done | session=%s | %dms | answer=%d chars",
                        session_id, elapsed, len(answer))
            if req.question and answer:
                try:
                    session_store.add_message(session_id, "user", req.question)
                    session_store.add_message(session_id, "assistant", answer)
                except Exception:
                    pass

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ═══════════════════════════════════════════════════════════════════
# Cross-Chat Memory
# ═══════════════════════════════════════════════════════════════════

@router.get("/chat-memory", response_model=ChatMemoryListResponse)
async def list_chat_memory():
    from memory.cross_session_memory import get_chat_memory_store
    memory_store = get_chat_memory_store()
    entries = memory_store.list_all()
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
    from memory.cross_session_memory import get_chat_memory_store
    memory_store = get_chat_memory_store()
    deleted = memory_store.delete_by_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No memory entry found for session {session_id}",
        )
    return {"message": f"Memory entry for session {session_id} deleted."}


# ═══════════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    from indexing.hnsw_vector_store import get_vector_store
    from indexing.bm25_index import get_bm25_index
    from memory.session_history_store import session_store
    from memory.cross_session_memory import get_chat_memory_store

    store = get_vector_store()
    bm25 = get_bm25_index()
    memory_store = get_chat_memory_store()

    return StatsResponse(
        vector_store=store.get_stats(),
        bm25=bm25.get_stats(),
        sessions=len(session_store.list_sessions()),
        chat_memories=memory_store.get_count(),
    )


# ═══════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════

def _session_to_model(session: dict) -> ChatSession:
    return ChatSession(
        id=session["id"],
        title=session.get("title", "New Chat"),
        created_at=session.get("created_at", ""),
        updated_at=session.get("updated_at", session.get("created_at", "")),
        message_count=len(session.get("messages", [])),
    )
