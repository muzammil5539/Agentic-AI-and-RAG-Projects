"""LangGraph ReAct agent — graph definition and builder."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver

from agent.state import AgentState
from agent.nodes import make_agent_node, make_tool_node, should_continue
from tools.registry import get_all_tools


def build_agent_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    tools: list | None = None,
) -> StateGraph:
    """Build and compile the ReAct agent graph.

    Flow:
        START → agent → (has tool calls?) → tools → agent → ... → END
    """
    if tools is None:
        tools = get_all_tools()

    agent_node = make_agent_node(tools)
    tool_node = make_tool_node(tools)

    graph = StateGraph(AgentState)

    # ── Nodes ────────────────────────────────────────────
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    # ── Edges ────────────────────────────────────────────
    graph.add_edge(START, "agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    graph.add_edge("tools", "agent")

    # ── Compile ──────────────────────────────────────────
    compiled = graph.compile(checkpointer=checkpointer)
    return compiled
