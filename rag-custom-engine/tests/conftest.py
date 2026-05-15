"""
Pytest configuration and shared fixtures for RAG From Scratch API tests.
Server must be running at http://localhost:8001 before running integration tests.
"""

import pytest
import httpx

BASE_URL = "http://localhost:8001"
TIMEOUT = 60.0  # seconds — LLM pipeline can be slow


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: calls OpenAI API (requires live server + OPENAI_API_KEY)"
    )
    config.addinivalue_line(
        "markers", "ui: Playwright browser tests (requires live server)"
    )


@pytest.fixture(scope="session", autouse=True)
def check_server():
    """Skip all tests if the server is not reachable."""
    try:
        r = httpx.get(f"{BASE_URL}/api/stats", timeout=5)
        r.raise_for_status()
    except Exception:
        pytest.skip(
            "Server not reachable at http://localhost:8001 — "
            "start it first with: python main.py"
        )


@pytest.fixture(scope="session")
def client():
    """Shared HTTP client for the whole test session."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as c:
        yield c


@pytest.fixture
def test_session(client):
    """Create a fresh session and clean it up after the test."""
    r = client.post("/api/sessions")
    assert r.status_code == 200, f"create session: {r.text}"
    sid = r.json()["id"]
    yield sid
    client.delete(f"/api/sessions/{sid}")


@pytest.fixture
def uploaded_doc(client):
    """Upload a small test document and remove it after the test."""
    content = (
        b"Test document for pytest. "
        b"Artificial intelligence and machine learning are used in RAG systems "
        b"for retrieval augmented generation."
    )
    r = client.post(
        "/api/upload",
        files={"file": ("pytest_test_doc.txt", content, "text/plain")},
    )
    assert r.status_code == 200, f"upload fixture: {r.text}"
    yield "pytest_test_doc.txt"
    client.delete("/api/documents/pytest_test_doc.txt")
