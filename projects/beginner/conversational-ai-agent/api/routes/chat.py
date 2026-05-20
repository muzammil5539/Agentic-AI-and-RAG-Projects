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


@router.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    summary="Chat (non-streaming)",
    description="""
Send a message to the ReAct agent and receive the **complete response** in one request.

The agent will reason, call tools, and return the final answer along with the full
ReAct trace (`steps`). For real-time streaming with visible thought process,
use the WebSocket endpoint at `/ws/chat` instead.

**Request body:**
```json
{
  "query": "What is 25% of 840?",
  "session_id": "abc123",
  "model": "gpt-4o-mini"
}
```

**Response example:**
```json
{
  "answer": "25% of 840 is 210.",
  "session_id": "abc123",
  "model": "gpt-4o-mini",
  "steps": [
    {"type": "thought", "content": "I need to calculate 25% of 840."},
    {"type": "tool_call", "tool_name": "calculator", "tool_args": {"expression": "0.25 * 840"}},
    {"type": "tool_result", "tool_name": "calculator", "content": "210.0"},
    {"type": "answer", "content": "25% of 840 is 210."}
  ]
}
```

Requires `X-API-Key` header.
""",
)
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
    """WebSocket endpoint for real-time agent streaming.

    Connect with: ws://localhost:8002/ws/chat

    **Client → Server** (send one JSON message per query):
    ```json
    {
      "type": "chat",
      "query": "What's the weather in Paris?",
      "session_id": "abc123",
      "model": "gpt-4o-mini",
      "api_key": "sk-..."
    }
    ```

    **Server → Client** (stream of typed JSON events):
    - `{"type": "thought", "content": "I need to check the weather..."}` — agent reasoning
    - `{"type": "tool_call", "tool_name": "weather", "tool_args": {"location": "Paris"}}` — tool invoked
    - `{"type": "tool_result", "tool_name": "weather", "content": "15°C, partly cloudy"}` — tool output
    - `{"type": "token", "content": "The "}` — streaming answer token
    - `{"type": "done", "session_id": "abc123", "model": "gpt-4o-mini"}` — completion
    - `{"type": "error", "message": "..."}` — error

    The `session_id` can be `null` — the agent creates a new session automatically.
    Pass the `session_id` from the `done` event in subsequent messages to continue the conversation.
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
