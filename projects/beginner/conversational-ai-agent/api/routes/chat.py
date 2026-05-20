"""Chat endpoints — REST and WebSocket."""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from api.dependencies import get_api_key, get_user_id
from api.models.requests import ChatRequest
from api.models.responses import ChatResponse
from api.models.ws_messages import WSChatMessage, WSErrorEvent
from services.agent_service import get_agent_service

logger = logging.getLogger("agent_app.chat")

router = APIRouter(tags=["chat"])


# ── REST endpoint (synchronous response) ─────────────────────────


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    api_key: Annotated[str, Depends(get_api_key)],
    user_id: Annotated[str, Depends(get_user_id)],
) -> ChatResponse:
    """Send a message and get the full agent response (non-streaming)."""
    svc = get_agent_service()
    try:
        return await svc.invoke(
            query=body.query,
            session_id=body.session_id or "",
            model=body.model,
            api_key=api_key,
            user_id=user_id,
        )
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=str(e))


# ── WebSocket endpoint (streaming) ───────────────────────────────


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Stream agent execution over WebSocket.

    Protocol:
      1. Client connects
      2. Client sends JSON matching WSChatMessage schema
      3. Server streams WSOutgoingEvent JSON messages
      4. Server sends WSDoneEvent when finished
    """
    await websocket.accept()
    logger.info("WebSocket connected")

    try:
        while True:
            # Wait for a message from the client
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
                msg = WSChatMessage.model_validate(data)
            except Exception as e:
                await websocket.send_text(
                    WSErrorEvent(message=f"Invalid message: {e}").model_dump_json()
                )
                continue

            # Derive user_id from API key
            import hashlib

            user_id = hashlib.sha256(msg.api_key.encode()).hexdigest()[:16]

            # Stream the agent response
            svc = get_agent_service()
            async for event in svc.stream(
                query=msg.query,
                session_id=msg.session_id or "",
                model=msg.model,
                api_key=msg.api_key,
                user_id=user_id,
            ):
                await websocket.send_text(event.model_dump_json())

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await websocket.send_text(
                WSErrorEvent(message=str(e)).model_dump_json()
            )
        except Exception:
            pass
