"""
Full API coverage test for rag-custom-engine.
Run: python test_rag_custom_engine.py
"""
import httpx
import json
import sys

BASE = "http://localhost:8001/api"
PASS = []
FAIL = []


def check(label, r, expected=200, key_check=None):
    ok = r.status_code == expected
    if ok and key_check:
        try:
            body = r.json()
            ok = key_check(body)
        except Exception as e:
            ok = False
            print(f"  key_check error: {e}")
    tag = "PASS" if ok else "FAIL"
    (PASS if ok else FAIL).append(label)
    print(f"[{tag}] {label}  (HTTP {r.status_code})")
    if not ok:
        try:
            print(f"       Response: {json.dumps(r.json(), indent=2)[:400]}")
        except Exception:
            print(f"       Response: {r.text[:400]}")
    return r


print("=" * 62)
print("RAG CUSTOM ENGINE — Full API Coverage Test")
print("=" * 62)

# ── Stats ─────────────────────────────────────────────────────────
print("\n── Stats ──────────────────────────────────────────────────")
r = check("GET /stats", httpx.get(f"{BASE}/stats", timeout=15),
          key_check=lambda b: "vector_store" in b and "bm25" in b and "sessions" in b)
if r.status_code == 200:
    s = r.json()
    vs_total = s["vector_store"].get("total")
    bm25_total = s["bm25"].get("total_documents")
    print(f"       vector_chunks={vs_total}, bm25_docs={bm25_total}, sessions={s['sessions']}")

# ── Documents ─────────────────────────────────────────────────────
print("\n── Documents ──────────────────────────────────────────────")
r = check("GET /documents", httpx.get(f"{BASE}/documents", timeout=15),
          key_check=lambda b: "total_chunks" in b and isinstance(b.get("documents"), list))
if r.status_code == 200:
    db = r.json()
    filenames = [d["filename"] for d in db["documents"]]
    print(f"       total_chunks={db['total_chunks']}, docs={filenames}")

# Upload txt file
test_txt = (b"This is a test document for RAG coverage testing. "
            b"It contains sample content about artificial intelligence "
            b"and machine learning concepts used in retrieval augmented generation.")
r = check("POST /upload (txt)",
          httpx.post(f"{BASE}/upload",
                     files={"file": ("test_coverage.txt", test_txt, "text/plain")},
                     timeout=60),
          key_check=lambda b: b.get("num_chunks", 0) > 0)
if r.status_code == 200:
    print(f"       ingested {r.json()['num_chunks']} chunks")

# Upload duplicate (should overwrite/succeed)
check("POST /upload (duplicate txt)",
      httpx.post(f"{BASE}/upload",
                 files={"file": ("test_coverage.txt", test_txt, "text/plain")},
                 timeout=60),
      key_check=lambda b: "num_chunks" in b)

# Bad extension
check("POST /upload (unsupported ext) → 400",
      httpx.post(f"{BASE}/upload",
                 files={"file": ("bad.xyz", b"data", "text/plain")},
                 timeout=10),
      expected=400)

# Verify doc appears
r = check("GET /documents (after upload)",
          httpx.get(f"{BASE}/documents", timeout=10),
          key_check=lambda b: any(d["filename"] == "test_coverage.txt"
                                   for d in b.get("documents", [])))
if r.status_code == 200:
    db2 = r.json()
    filenames2 = [d["filename"] for d in db2["documents"]]
    print(f"       docs now: {filenames2}")

# Shared flag operations
check("PUT /documents/test_coverage.txt/shared (→ true)",
      httpx.put(f"{BASE}/documents/test_coverage.txt/shared",
                json={"shared": True}, timeout=10),
      key_check=lambda b: b.get("is_shared") is True)

r = check("GET /shared-documents",
          httpx.get(f"{BASE}/shared-documents", timeout=10),
          key_check=lambda b: "shared_documents" in b)
if r.status_code == 200:
    print(f"       shared: {r.json()['shared_documents']}")

check("PUT /documents/test_coverage.txt/shared (→ false)",
      httpx.put(f"{BASE}/documents/test_coverage.txt/shared",
                json={"shared": False}, timeout=10),
      key_check=lambda b: b.get("is_shared") is False)

check("PUT /documents/nonexistent.txt/shared → 404",
      httpx.put(f"{BASE}/documents/nonexistent.txt/shared",
                json={"shared": True}, timeout=10),
      expected=404)

# Delete test doc
check("DELETE /documents/test_coverage.txt",
      httpx.delete(f"{BASE}/documents/test_coverage.txt", timeout=10),
      key_check=lambda b: "Deleted" in b.get("message", ""))

check("DELETE /documents/nonexistent.txt → 404",
      httpx.delete(f"{BASE}/documents/nonexistent.txt", timeout=10),
      expected=404)

# ── Sessions ──────────────────────────────────────────────────────
print("\n── Sessions ────────────────────────────────────────────────")
r = check("POST /sessions",
          httpx.post(f"{BASE}/sessions", timeout=10),
          key_check=lambda b: "id" in b and "title" in b)
if r.status_code != 200:
    print("FATAL: cannot continue session tests without a session")
    sys.exit(1)

sid = r.json()["id"]
print(f"       created session: {sid}")

r = check("GET /sessions",
          httpx.get(f"{BASE}/sessions", timeout=10),
          key_check=lambda b: "sessions" in b and isinstance(b["sessions"], list))
if r.status_code == 200:
    print(f"       total sessions: {len(r.json()['sessions'])}")

check("GET /sessions/{id}",
      httpx.get(f"{BASE}/sessions/{sid}", timeout=10),
      key_check=lambda b: b.get("session_id") == sid and "messages" in b)

check("PUT /sessions/{id}/rename",
      httpx.put(f"{BASE}/sessions/{sid}/rename",
                json={"title": "Coverage Test Session"}, timeout=10),
      key_check=lambda b: b.get("title") == "Coverage Test Session")

check("POST /sessions/{id}/clear",
      httpx.post(f"{BASE}/sessions/{sid}/clear", timeout=10))

# Archive empty session — must return 400
check("POST /sessions/{id}/archive (no msgs) → 400",
      httpx.post(f"{BASE}/sessions/{sid}/archive", timeout=10),
      expected=400)

# Non-existent session
check("GET /sessions/bad-id → 404",
      httpx.get(f"{BASE}/sessions/nonexistent-session-00000", timeout=10),
      expected=404)

check("PUT /sessions/bad-id/rename → 404",
      httpx.put(f"{BASE}/sessions/nonexistent-session-00000/rename",
                json={"title": "x"}, timeout=10),
      expected=404)

check("DELETE /sessions/{id}",
      httpx.delete(f"{BASE}/sessions/{sid}", timeout=10))

check("DELETE /sessions/bad-id → 404",
      httpx.delete(f"{BASE}/sessions/nonexistent-session-00000", timeout=10),
      expected=404)

# ── Chat Memory ────────────────────────────────────────────────────
print("\n── Chat Memory ─────────────────────────────────────────────")
r = check("GET /chat-memory",
          httpx.get(f"{BASE}/chat-memory", timeout=10),
          key_check=lambda b: "entries" in b and "total" in b)
if r.status_code == 200:
    print(f"       memory entries: {r.json()['total']}")

check("DELETE /chat-memory/nonexistent → 404",
      httpx.delete(f"{BASE}/chat-memory/nonexistent-session-00000", timeout=10),
      expected=404)

# ── Query (non-streaming) ─────────────────────────────────────────
print("\n── Query (non-streaming) ───────────────────────────────────")
r = check("POST /query",
          httpx.post(f"{BASE}/query",
                     json={"question": "What documents have been uploaded?"},
                     timeout=90),
          key_check=lambda b: len(b.get("answer", "")) > 0 and "session_id" in b)
if r.status_code == 200:
    qr = r.json()
    print(f"       answer_len={len(qr['answer'])}, sources={len(qr['sources'])}, steps={len(qr['pipeline_steps'])}")
    qsid = qr["session_id"]

    # Archive the query session (has messages now)
    check("POST /sessions/{query_sid}/archive",
          httpx.post(f"{BASE}/sessions/{qsid}/archive", timeout=30))

    # Delete memory for that session
    check("DELETE /chat-memory/{query_sid}",
          httpx.delete(f"{BASE}/chat-memory/{qsid}", timeout=10))

# ── Query (streaming SSE) ─────────────────────────────────────────
print("\n── Query (streaming SSE) ───────────────────────────────────")
try:
    with httpx.stream("POST", f"{BASE}/query/stream",
                      json={"question": "Give a brief overview of what was uploaded"},
                      timeout=90) as resp:
        step_starts = 0
        step_completes = 0
        answer_text = ""
        sse_errors = []
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            try:
                payload = json.loads(line[6:])
            except Exception:
                continue
            t = payload.get("type")
            if t == "step_start":
                step_starts += 1
            elif t == "step_complete":
                step_completes += 1
            elif t == "answer":
                answer_text = payload.get("data", {}).get("answer", "")
            elif t == "error":
                sse_errors.append(payload.get("data", {}).get("message", ""))

        ok = len(answer_text) > 0 and step_starts >= 10
        tag = "PASS" if ok else "FAIL"
        (PASS if ok else FAIL).append("POST /query/stream")
        print(f"[{tag}] POST /query/stream  (HTTP {resp.status_code})")
        print(f"       step_starts={step_starts}, step_completes={step_completes}, answer_len={len(answer_text)}")
        if sse_errors:
            print(f"       SSE errors: {sse_errors}")
except Exception as exc:
    FAIL.append("POST /query/stream")
    print(f"[FAIL] POST /query/stream  — {exc}")

# ── Summary ────────────────────────────────────────────────────────
print()
print("=" * 62)
print(f"Results: {len(PASS)} PASS  /  {len(FAIL)} FAIL  /  {len(PASS) + len(FAIL)} total")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print(f"  - {f}")
print("=" * 62)
sys.exit(0 if not FAIL else 1)
