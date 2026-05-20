"""Tests for the LangGraph agent — graph compilation and routing."""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage
from agent.state import AgentState, AgentStep
from agent.nodes import should_continue
from agent.graph import build_agent_graph


class TestShouldContinue:
    def test_routes_to_tools_when_tool_calls_present(self):
        msg = AIMessage(content="", tool_calls=[{"name": "calc", "args": {}, "id": "1"}])
        state: AgentState = {
            "messages": [msg],
            "steps": [],
            "iteration_count": 1,
            "model_name": "gpt-4o-mini",
        }
        assert should_continue(state) == "tools"

    def test_routes_to_end_when_no_tool_calls(self):
        msg = AIMessage(content="Hello!")
        state: AgentState = {
            "messages": [msg],
            "steps": [],
            "iteration_count": 1,
            "model_name": "gpt-4o-mini",
        }
        assert should_continue(state) == "end"

    def test_routes_to_end_on_max_iterations(self):
        msg = AIMessage(content="", tool_calls=[{"name": "calc", "args": {}, "id": "1"}])
        state: AgentState = {
            "messages": [msg],
            "steps": [],
            "iteration_count": 10,  # MAX_ITERATIONS default
            "model_name": "gpt-4o-mini",
        }
        assert should_continue(state) == "end"


class TestGraphCompilation:
    def test_graph_compiles_without_checkpointer(self):
        graph = build_agent_graph(checkpointer=None)
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_agent_graph(checkpointer=None)
        # The compiled graph should have agent and tools nodes
        node_names = set(graph.get_graph().nodes.keys())
        assert "agent" in node_names
        assert "tools" in node_names


class TestAgentStep:
    def test_step_creation(self):
        step = AgentStep(
            type="thought",
            content="Let me think...",
        )
        assert step.type == "thought"
        assert step.content == "Let me think..."
        assert step.tool_name is None
        assert step.timestamp is not None

    def test_tool_call_step(self):
        step = AgentStep(
            type="tool_call",
            content="Calling calculator",
            tool_name="calculator",
            tool_args={"expression": "2+2"},
        )
        assert step.type == "tool_call"
        assert step.tool_name == "calculator"
        assert step.tool_args == {"expression": "2+2"}
