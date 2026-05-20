"""FastAPI dependencies — shared resources injected into routes."""

import hashlib
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from config import settings


def get_api_key(x_api_key: Annotated[str, Header()] = "") -> str:
    """Extract and validate the OpenAI API key from the request header."""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header. Provide your OpenAI API key.",
        )
    if not x_api_key.startswith("sk-"):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format. Must start with 'sk-'.",
        )
    return x_api_key


def get_user_id(api_key: Annotated[str, Depends(get_api_key)]) -> str:
    """Derive a stable user_id from the API key (SHA-256 hash, first 16 hex chars)."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


def get_checkpointer(request: Request):
    """Return the shared SQLite checkpointer from app state."""
    return request.app.state.checkpointer
