"""Agent state schema — shared state flowing through the LangGraph ReAct loop."""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Annotated, Literal

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


class AgentStep(BaseModel):
    """A single visible step in the ReAct trace (streamed to the UI)."""

    type: Literal["thought", "tool_call", "tool_result", "answer"]
    content: str
    tool_name: str | None = None
    tool_args: dict | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentState(MessagesState):
    """Full state for the ReAct agent graph.

    Inherits `messages: Annotated[list[AnyMessage], add_messages]` from
    MessagesState so LangGraph handles message accumulation automatically.
    """

    # Visible thinking trace (accumulated via reducer)
    steps: Annotated[list[AgentStep], operator.add]

    # Loop safety counter (overwritten each iteration — no reducer)
    iteration_count: int

    # Model to use for this invocation (set once at entry)
    model_name: str
