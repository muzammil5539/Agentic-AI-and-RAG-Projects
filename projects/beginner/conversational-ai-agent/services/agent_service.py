"""Agent service — orchestrates graph invocation and streaming."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from datetime import datetime

import openai
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.graph import build_agent_graph
from agent.state import AgentStep
from api.models.responses import AgentStep as AgentStepResponse, ChatResponse
from api.models.ws_messages import (
    WSDoneEvent,
    WSErrorEvent,
    WSOutgoingEvent,
    WSThoughtEvent,
    WSToolCallEvent,
    WSToolResultEvent,
    WSTokenEvent,
)
from memory.checkpointer import get_checkpointer
from memory.session_store import get_session_store

logger = logging.getLogger("agent_app.service")


class AgentService:
    """Stateless service that builds per-request agent graphs and runs them."""

    def __init__(self):
        self._checkpointer = get_checkpointer()
        self._graph = build_agent_graph(checkpointer=self._checkpointer)

    # ── Sync invocation ──────────────────────────────────

    async def invoke(
        self,
        query: str,
        session_id: str,
        model: str,
        api_key: str,
        user_id: str,
    ) -> ChatResponse:
        """Run the agent to completion and return the full response."""
        store = get_session_store()

        # Ensure session exists
        session = store.get(session_id)
        if not session:
            session = store.create(user_id=user_id)
            session_id = session.id

        config = {
            "configurable": {
                "thread_id": session_id,
                "api_key": api_key,
            }
        }

        result = await self._graph.ainvoke(
            {
                "messages": [HumanMessage(content=query)],
                "steps": [],
                "iteration_count": 0,
                "model_name": model,
            },
            config,
        )

        # Extract answer from last AI message
        answer = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                answer = msg.content
                break

        # Convert agent steps to response model
        steps = [
            AgentStepResponse(
                type=s.type,
                content=s.content,
                tool_name=s.tool_name,
                tool_args=s.tool_args,
                timestamp=s.timestamp,
            )
            for s in result.get("steps", [])
        ]

        # Update session metadata
        store.increment_messages(session_id, count=2)  # user + assistant
        if session.message_count == 0:
            # Auto-title from first query
            title = query[:80] + ("..." if len(query) > 80 else "")
            store.update_title(session_id, title)

        return ChatResponse(
            answer=answer,
            session_id=session_id,
            model=model,
            steps=steps,
        )

    # ── Streaming invocation ─────────────────────────────

    async def stream(
        self,
        query: str,
        session_id: str,
        model: str,
        api_key: str,
        user_id: str,
    ) -> AsyncGenerator[WSOutgoingEvent, None]:
        """Stream agent execution as WebSocket events."""
        store = get_session_store()

        # Ensure session exists
        session = store.get(session_id)
        if not session:
            session = store.create(user_id=user_id)
            session_id = session.id

        config = {
            "configurable": {
                "thread_id": session_id,
                "api_key": api_key,
            }
        }

        try:
            async for event in self._graph.astream(
                {
                    "messages": [HumanMessage(content=query)],
                    "steps": [],
                    "iteration_count": 0,
                    "model_name": model,
                },
                config,
                stream_mode="updates",
            ):
                # event is {node_name: state_update_dict}
                for node_name, update in event.items():
                    steps: list[AgentStep] = update.get("steps", [])
                    for step in steps:
                        if step.type == "thought":
                            yield WSThoughtEvent(content=step.content)
                        elif step.type == "tool_call":
                            yield WSToolCallEvent(
                                tool_name=step.tool_name or "",
                                tool_args=step.tool_args or {},
                            )
                        elif step.type == "tool_result":
                            yield WSToolResultEvent(
                                tool_name=step.tool_name or "",
                                content=step.content,
                            )
                        elif step.type == "answer":
                            # Stream the answer as tokens (word by word for visual effect)
                            words = step.content.split(" ")
                            for i, word in enumerate(words):
                                token = word if i == 0 else " " + word
                                yield WSTokenEvent(content=token)

            # Update session metadata
            store.increment_messages(session_id, count=2)
            if session.message_count == 0:
                title = query[:80] + ("..." if len(query) > 80 else "")
                store.update_title(session_id, title)

            yield WSDoneEvent(session_id=session_id, model=model)

        except openai.AuthenticationError:
            logger.warning("Invalid API key — 401 from OpenAI")
            yield WSErrorEvent(
                message=(
                    "Invalid API key — OpenAI rejected it with 401. "
                    "Please update your key in Settings (the gear icon)."
                )
            )
        except openai.RateLimitError:
            logger.warning("OpenAI rate limit hit")
            yield WSErrorEvent(
                message="OpenAI rate limit reached. Please wait a moment and try again."
            )
        except Exception as e:
            logger.exception("Stream error")
            yield WSErrorEvent(message=str(e))


# ── Singleton ────────────────────────────────────────────────────
_service: AgentService | None = None


def init_agent_service() -> AgentService:
    """Initialize the service singleton. Called once from app lifespan after checkpointer is set."""
    global _service
    _service = AgentService()
    return _service


def get_agent_service() -> AgentService:
    global _service
    if _service is None:
        _service = AgentService()
    return _service
