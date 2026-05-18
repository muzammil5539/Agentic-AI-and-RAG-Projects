"""
Comprehensive API test suite for RAG From Scratch.

Run (server must be up at localhost:8001):
    pytest                         # unit/structural tests only
    pytest -m integration          # include LLM-calling tests
    pytest -m "not ui"             # all except Playwright

Coverage:
  - GET  /api/stats
  - POST /api/upload
  - GET  /api/documents
  - DELETE /api/documents/{filename}
  - PUT  /api/documents/{filename}/shared
  - GET  /api/shared-documents
  - POST /api/sessions
  - GET  /api/sessions
  - GET  /api/sessions/{id}
  - DELETE /api/sessions/{id}
  - PUT  /api/sessions/{id}/rename
  - POST /api/sessions/{id}/clear
  - POST /api/sessions/{id}/archive
  - GET  /api/chat-memory
  - DELETE /api/chat-memory/{session_id}
  - POST /api/query          [integration]
  - POST /api/query/stream   [integration]
"""

import json
import pytest
import httpx

BASE_URL = "http://localhost:8001"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _tiny_txt() -> bytes:
    """Minimal text content for upload tests."""
    return (
        b"RAG test document. "
        b"Retrieval augmented generation uses vector search and language models."
    )


# ═══════════════════════════════════════════════════════════════
# 1. Stats
# ═══════════════════════════════════════════════════════════════

class TestStats:
    def test_stats_ok(self, client: httpx.Client):
        r = client.get("/api/stats")
        assert r.status_code == 200

    def test_stats_structure(self, client: httpx.Client):
        data = client.get("/api/stats").json()
        assert "vector_store" in data
        assert "bm25" in data
        assert "sessions" in data
        assert "chat_memories" in data

    def test_stats_counts_are_non_negative(self, client: httpx.Client):
        data = client.get("/api/stats").json()
        vs = data["vector_store"]
        # vector_store has total_entries (or total_vectors in some builds)
        count = vs.get("total_entries", vs.get("total_vectors", 0))
        assert count >= 0
        assert data["bm25"].get("total_docs", 0) >= 0
        # sessions and chat_memories are plain ints in StatsResponse
        assert isinstance(data["sessions"], int) and data["sessions"] >= 0
        assert isinstance(data["chat_memories"], int) and data["chat_memories"] >= 0


# ═══════════════════════════════════════════════════════════════
# 2. Upload & Documents
# ═══════════════════════════════════════════════════════════════

class TestDocuments:
    def test_upload_txt(self, client: httpx.Client):
        r = client.post(
            "/api/upload",
            files={"file": ("api_test_upload.txt", _tiny_txt(), "text/plain")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["filename"] == "api_test_upload.txt"
        assert data["num_chunks"] >= 1
        # cleanup
        client.delete("/api/documents/api_test_upload.txt")

    def test_upload_returns_message(self, client: httpx.Client):
        r = client.post(
            "/api/upload",
            files={"file": ("msg_test.txt", _tiny_txt(), "text/plain")},
        )
        assert r.status_code == 200
        assert "message" in r.json()
        client.delete("/api/documents/msg_test.txt")

    def test_upload_no_file_422(self, client: httpx.Client):
        r = client.post("/api/upload")
        assert r.status_code == 422

    def test_list_documents(self, client: httpx.Client, uploaded_doc):
        r = client.get("/api/documents")
        assert r.status_code == 200
        data = r.json()
        assert "documents" in data
        assert "total_chunks" in data
        names = [d["filename"] for d in data["documents"]]
        assert uploaded_doc in names

    def test_document_has_fields(self, client: httpx.Client, uploaded_doc):
        r = client.get("/api/documents")
        docs = {d["filename"]: d for d in r.json()["documents"]}
        doc = docs[uploaded_doc]
        assert "chunk_count" in doc
        assert "is_shared" in doc
        assert doc["chunk_count"] >= 1

    def test_delete_document(self, client: httpx.Client):
        # Upload then delete
        r = client.post(
            "/api/upload",
            files={"file": ("del_test.txt", _tiny_txt(), "text/plain")},
        )
        assert r.status_code == 200
        r2 = client.delete("/api/documents/del_test.txt")
        assert r2.status_code == 200
        # Verify gone
        names = [d["filename"] for d in client.get("/api/documents").json()["documents"]]
        assert "del_test.txt" not in names

    def test_delete_nonexistent_404(self, client: httpx.Client):
        r = client.delete("/api/documents/this_file_does_not_exist_xyz.txt")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════
# 3. Shared Documents
# ═══════════════════════════════════════════════════════════════

class TestSharedDocuments:
    def test_set_shared(self, client: httpx.Client, uploaded_doc):
        r = client.put(
            f"/api/documents/{uploaded_doc}/shared",
            json={"shared": True},
        )
        assert r.status_code == 200

    def test_get_shared_documents(self, client: httpx.Client, uploaded_doc):
        # Share the doc first
        client.put(f"/api/documents/{uploaded_doc}/shared", json={"shared": True})
        r = client.get("/api/shared-documents")
        assert r.status_code == 200
        data = r.json()
        assert "shared_documents" in data
        assert uploaded_doc in data["shared_documents"]

    def test_unset_shared(self, client: httpx.Client, uploaded_doc):
        client.put(f"/api/documents/{uploaded_doc}/shared", json={"shared": True})
        client.put(f"/api/documents/{uploaded_doc}/shared", json={"shared": False})
        r = client.get("/api/shared-documents")
        assert uploaded_doc not in r.json()["shared_documents"]

    def test_shared_invalid_body_422(self, client: httpx.Client, uploaded_doc):
        r = client.put(
            f"/api/documents/{uploaded_doc}/shared",
            json={"wrong_key": True},
        )
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# 4. Sessions
# ═══════════════════════════════════════════════════════════════

class TestSessions:
    def test_create_session(self, client: httpx.Client):
        r = client.post("/api/sessions")
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        # cleanup
        client.delete(f"/api/sessions/{data['id']}")

    def test_list_sessions(self, client: httpx.Client, test_session):
        r = client.get("/api/sessions")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()["sessions"]]
        assert test_session in ids

    def test_get_session(self, client: httpx.Client, test_session):
        r = client.get(f"/api/sessions/{test_session}")
        assert r.status_code == 200
        data = r.json()
        # GET /sessions/{id} returns SessionMessagesResponse with session_id field
        assert data["session_id"] == test_session
        assert "messages" in data

    def test_get_nonexistent_session_404(self, client: httpx.Client):
        r = client.get("/api/sessions/nonexistent-session-id-abc123")
        assert r.status_code == 404

    def test_rename_session(self, client: httpx.Client, test_session):
        r = client.put(
            f"/api/sessions/{test_session}/rename",
            json={"title": "Pytest Renamed Session"},
        )
        assert r.status_code == 200
        data = r.json()
        # Rename returns {session_id, title}
        assert data["title"] == "Pytest Renamed Session"

    def test_rename_missing_title_422(self, client: httpx.Client, test_session):
        r = client.put(
            f"/api/sessions/{test_session}/rename",
            json={"wrong": "field"},
        )
        assert r.status_code == 422

    def test_clear_session(self, client: httpx.Client, test_session):
        r = client.post(f"/api/sessions/{test_session}/clear")
        assert r.status_code == 200

    def test_delete_session(self, client: httpx.Client):
        r = client.post("/api/sessions")
        sid = r.json()["id"]
        r2 = client.delete(f"/api/sessions/{sid}")
        assert r2.status_code == 200
        # Verify gone
        ids = [s["id"] for s in client.get("/api/sessions").json()["sessions"]]
        assert sid not in ids

    def test_archive_session(self, client: httpx.Client, test_session):
        r = client.post(f"/api/sessions/{test_session}/archive")
        # 200 success or 400 if no messages — both are valid application states
        assert r.status_code in (200, 400)


# ═══════════════════════════════════════════════════════════════
# 5. Chat Memory
# ═══════════════════════════════════════════════════════════════

class TestChatMemory:
    def test_get_chat_memory(self, client: httpx.Client):
        r = client.get("/api/chat-memory")
        assert r.status_code == 200
        data = r.json()
        assert "entries" in data
        assert "total" in data

    def test_chat_memory_total_matches_entries(self, client: httpx.Client):
        data = client.get("/api/chat-memory").json()
        assert data["total"] == len(data["entries"])

    def test_delete_nonexistent_memory_ok(self, client: httpx.Client):
        """Deleting a non-existent memory should not crash (200 or 404)."""
        r = client.delete("/api/chat-memory/nonexistent-session-xyz")
        assert r.status_code in (200, 404)


# ═══════════════════════════════════════════════════════════════
# 6. Query  [integration — calls OpenAI]
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestQuery:
    def test_query_returns_answer(self, client: httpx.Client, uploaded_doc, test_session):
        r = client.post(
            "/api/query",
            json={
                "question": "What is this document about?",
                "session_id": test_session,
                "pipeline_config": {
                    "use_multi_query": False,
                    "use_self_rag": False,
                    "use_compression": False,
                    "vector_method": "brute_force",
                    "merge_method": "weighted",
                },
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_query_has_sources(self, client: httpx.Client, uploaded_doc, test_session):
        r = client.post(
            "/api/query",
            json={
                "question": "What is RAG?",
                "session_id": test_session,
                "pipeline_config": {
                    "use_multi_query": False,
                    "use_self_rag": False,
                    "use_compression": False,
                    "vector_method": "brute_force",
                    "merge_method": "weighted",
                },
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)

    def test_query_has_pipeline_steps(self, client: httpx.Client, test_session):
        r = client.post(
            "/api/query",
            json={
                "question": "Hello",
                "session_id": test_session,
                "pipeline_config": {
                    "use_multi_query": False,
                    "use_self_rag": True,
                    "use_compression": False,
                    "vector_method": "brute_force",
                    "merge_method": "weighted",
                },
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "pipeline_steps" in data
        assert len(data["pipeline_steps"]) > 0

    def test_query_missing_question_422(self, client: httpx.Client):
        r = client.post("/api/query", json={"session_id": "whatever"})
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# 7. Streaming Query  [integration — calls OpenAI]
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestStream:
    def test_stream_returns_events(self, client: httpx.Client, uploaded_doc, test_session):
        """Stream should emit at least one step_start and one answer event."""
        events = []
        with client.stream(
            "POST",
            "/api/query/stream",
            json={
                "question": "Summarise the document.",
                "session_id": test_session,
                "pipeline_config": {
                    "use_multi_query": False,
                    "use_self_rag": False,
                    "use_compression": False,
                    "vector_method": "brute_force",
                    "merge_method": "weighted",
                },
            },
        ) as response:
            assert response.status_code == 200
            buffer = ""
            for chunk in response.iter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    boundary = buffer.index("\n\n")
                    raw = buffer[:boundary].strip()
                    buffer = buffer[boundary + 2:]
                    if raw.startswith("data: "):
                        try:
                            events.append(json.loads(raw[6:]))
                        except json.JSONDecodeError:
                            pass

        types = {e["type"] for e in events}
        assert "step_start" in types or "step_complete" in types
        assert "answer" in types

    def test_stream_answer_has_content(self, client: httpx.Client, test_session):
        answer_data = None
        with client.stream(
            "POST",
            "/api/query/stream",
            json={
                "question": "What is machine learning?",
                "session_id": test_session,
                "pipeline_config": {
                    "use_multi_query": False,
                    "use_self_rag": False,
                    "use_compression": False,
                    "vector_method": "brute_force",
                    "merge_method": "weighted",
                },
            },
        ) as response:
            buffer = ""
            for chunk in response.iter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    boundary = buffer.index("\n\n")
                    raw = buffer[:boundary].strip()
                    buffer = buffer[boundary + 2:]
                    if raw.startswith("data: "):
                        try:
                            ev = json.loads(raw[6:])
                            if ev["type"] == "answer":
                                answer_data = ev["data"]
                        except json.JSONDecodeError:
                            pass

        assert answer_data is not None
        assert len(answer_data.get("answer", "")) > 0
