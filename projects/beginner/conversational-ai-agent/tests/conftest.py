"""Shared test fixtures."""

import os
import sys
import pytest

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app


@pytest.fixture()
def client():
    """FastAPI test client (no auth)."""
    return TestClient(app)


@pytest.fixture()
def authed_client():
    """FastAPI test client with a dummy API key header."""
    client = TestClient(app)
    client.headers["X-API-Key"] = "sk-test-key-1234567890abcdef"
    return client
