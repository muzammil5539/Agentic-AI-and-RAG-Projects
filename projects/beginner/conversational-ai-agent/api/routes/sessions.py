"""Session management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_api_key, get_user_id
from api.models.requests import SessionCreateRequest
from api.models.responses import SessionListResponse, SessionResponse
from services.session_service import get_session_service

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List sessions",
    description="""
Return all chat sessions owned by the authenticated user (identified by API key hash).

Sessions are sorted newest-first and include metadata:
`id`, `title`, `created_at`, `updated_at`, `message_count`.

Requires `X-API-Key` header.
""",
)
async def list_sessions(
    user_id: Annotated[str, Depends(get_user_id)],
) -> SessionListResponse:
    """List all sessions for the authenticated user."""
    svc = get_session_service()
    return svc.list_for_user(user_id)


@router.post(
    "",
    response_model=SessionResponse,
    status_code=201,
    summary="Create session",
    description="""
Create a new chat session and return its metadata.

Optionally provide a `title` in the request body. If omitted, the session is
automatically titled from the first message sent.

The returned `id` can be passed as `session_id` in chat requests to continue
the conversation with persistent memory (LangGraph SQLite checkpointer).

Requires `X-API-Key` header.
""",
)
async def create_session(
    user_id: Annotated[str, Depends(get_user_id)],
    body: SessionCreateRequest | None = None,
) -> SessionResponse:
    """Create a new chat session."""
    svc = get_session_service()
    title = body.title if body else None
    return svc.create(user_id=user_id, title=title)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session",
    description="""
Retrieve metadata for a specific session by its ID.

Returns 404 if the session does not exist, 403 if it belongs to a different user.

Requires `X-API-Key` header.
""",
)
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


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Rename session",
    description="""\
Update the title of a session. The new title must be provided in the request body.

Requires `X-API-Key` header.
""",
)
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


@router.delete(
    "/{session_id}",
    status_code=204,
    summary="Delete session",
    description="""
Permanently delete a session and all its associated metadata.

Note: This removes the session record from the JSON store but does **not** purge
the LangGraph SQLite checkpoint history. Returns `204 No Content` on success.

Returns 404 if the session does not exist, 403 if it belongs to a different user.

Requires `X-API-Key` header.
""",
)
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
