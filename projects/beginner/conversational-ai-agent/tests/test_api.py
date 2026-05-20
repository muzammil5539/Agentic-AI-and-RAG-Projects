"""Tests for API endpoints."""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert data["tools_count"] == 6
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0


class TestTools:
    def test_list_tools(self, client):
        resp = client.get("/api/v1/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tools"]) == 6
        names = {t["name"] for t in data["tools"]}
        assert "calculator" in names
        assert "weather" in names
        assert "datetime_tool" in names
        assert "web_search" in names
        assert "code_interpreter" in names
        assert "rag_search" in names

    def test_tool_has_schema(self, client):
        resp = client.get("/api/v1/tools")
        tools = resp.json()["tools"]
        calc = next(t for t in tools if t["name"] == "calculator")
        assert "properties" in calc["parameters"]
        assert "expression" in calc["parameters"]["properties"]


class TestSessions:
    def test_list_sessions_requires_auth(self, client):
        resp = client.get("/api/v1/sessions")
        assert resp.status_code == 401

    def test_create_and_list_sessions(self, authed_client):
        # Create
        resp = authed_client.post(
            "/api/v1/sessions",
            json={"title": "Test Session"},
        )
        assert resp.status_code == 201
        session = resp.json()
        assert session["title"] == "Test Session"
        session_id = session["id"]

        # List
        resp = authed_client.get("/api/v1/sessions")
        assert resp.status_code == 200
        sessions = resp.json()["sessions"]
        assert any(s["id"] == session_id for s in sessions)

        # Get
        resp = authed_client.get(f"/api/v1/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id

        # Delete
        resp = authed_client.delete(f"/api/v1/sessions/{session_id}")
        assert resp.status_code == 204

    def test_get_nonexistent_session(self, authed_client):
        resp = authed_client.get("/api/v1/sessions/nonexistent")
        assert resp.status_code == 404


class TestChat:
    def test_chat_requires_auth(self, client):
        resp = client.post("/api/v1/chat", json={"query": "hello"})
        assert resp.status_code == 401

    def test_chat_invalid_key_format(self, client):
        resp = client.post(
            "/api/v1/chat",
            json={"query": "hello"},
            headers={"X-API-Key": "invalid-key"},
        )
        assert resp.status_code == 401
