"""Session management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_api_key, get_user_id
from api.models.requests import SessionCreateRequest
from api.models.responses import SessionListResponse, SessionResponse
from services.session_service import get_session_service

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user_id: Annotated[str, Depends(get_user_id)],
) -> SessionListResponse:
    """List all sessions for the authenticated user."""
    svc = get_session_service()
    return svc.list_for_user(user_id)


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    user_id: Annotated[str, Depends(get_user_id)],
    body: SessionCreateRequest | None = None,
) -> SessionResponse:
    """Create a new chat session."""
    svc = get_session_service()
    title = body.title if body else None
    return svc.create(user_id=user_id, title=title)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> SessionResponse:
    """Get session metadata by ID."""
    svc = get_session_service()
    session = svc.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session_title(
    session_id: str,
    body: SessionCreateRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> SessionResponse:
    """Update a session's title."""
    svc = get_session_service()
    existing = svc.get(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")
    if existing.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    updated = svc.update_title(session_id, body.title or "Untitled")
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    return updated


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
) -> None:
    """Delete a session."""
    svc = get_session_service()
    existing = svc.get(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Session not found")
    if existing.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    svc.delete(session_id)
