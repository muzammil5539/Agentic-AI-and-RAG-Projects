"""Graph nodes for the LangGraph ReAct agent."""

from __future__ import annotations

import logging
from datetime import datetime

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from agent.state import AgentState, AgentStep
from agent.prompts import build_system_prompt
from config import settings

logger = logging.getLogger("agent_app.nodes")


def _format_tool_descriptions(tools: list) -> str:
    """Build a human-readable list of tool names + descriptions."""
    lines = []
    for t in tools:
        lines.append(f"- **{t.name}**: {t.description}")
    return "\n".join(lines)


def make_agent_node(tools: list):
    """Factory: returns an agent_node function with tools bound."""

    tool_desc = _format_tool_descriptions(tools)
    system_msg = build_system_prompt(tool_desc)

    async def agent_node(state: AgentState, config: RunnableConfig) -> dict:
        """Call the LLM with tools bound. Emits a 'thought' step."""
        model_name = state.get("model_name", settings.DEFAULT_MODEL)
        api_key = config.get("configurable", {}).get("api_key", "")

        llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            temperature=0.1,
            streaming=True,
        )
        llm_with_tools = llm.bind_tools(tools)

        messages = state["messages"]
        # Inject system prompt as the first message if not present
        if not messages or messages[0].type != "system":
            from langchain_core.messages import SystemMessage

            messages = [SystemMessage(content=system_msg)] + list(messages)

        response: AIMessage = await llm_with_tools.ainvoke(messages)

        # Build visible steps
        new_steps: list[AgentStep] = []

        # If the model included reasoning text before tool calls
        if response.content and response.tool_calls:
            new_steps.append(
                AgentStep(
                    type="thought",
                    content=response.content,
                )
            )

        # Log tool calls as steps
        for tc in response.tool_calls:
            new_steps.append(
                AgentStep(
                    type="tool_call",
                    content=f"Calling {tc['name']}",
                    tool_name=tc["name"],
                    tool_args=tc["args"],
                )
            )

        # If no tool calls, this is the final answer
        if not response.tool_calls and response.content:
            new_steps.append(
                AgentStep(
                    type="answer",
                    content=response.content,
                )
            )

        iteration = state.get("iteration_count", 0) + 1

        return {
            "messages": [response],
            "steps": new_steps,
            "iteration_count": iteration,
        }

    return agent_node


def make_tool_node(tools: list):
    """Factory: returns a tool_node that executes tool calls."""

    tool_map = {t.name: t for t in tools}

    async def tool_node(state: AgentState) -> dict:
        """Execute all tool calls from the last AI message."""
        last_msg = state["messages"][-1]
        if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
            return {"messages": [], "steps": []}

        result_messages = []
        result_steps = []

        for tc in last_msg.tool_calls:
            tool_name = tc["name"]
            tool_obj = tool_map.get(tool_name)

            if tool_obj is None:
                content = f"Error: Unknown tool '{tool_name}'"
            else:
                try:
                    content = await tool_obj.ainvoke(tc["args"])
                except Exception as e:
                    content = f"Error executing {tool_name}: {e}"
                    logger.exception("Tool %s failed", tool_name)

            result_messages.append(
                ToolMessage(
                    tool_call_id=tc["id"],
                    name=tool_name,
                    content=str(content),
                )
            )
            result_steps.append(
                AgentStep(
                    type="tool_result",
                    tool_name=tool_name,
                    content=str(content)[:2000],  # Truncate for UI
                )
            )

        return {"messages": result_messages, "steps": result_steps}

    return tool_node


def should_continue(state: AgentState) -> str:
    """Route after the agent node: loop to tools or finish."""
    last_msg = state["messages"][-1]

    # Safety: max iteration guard
    if state.get("iteration_count", 0) >= settings.MAX_ITERATIONS:
        logger.warning("Max iterations reached (%d)", settings.MAX_ITERATIONS)
        return "end"

    # If the LLM wants to call tools, go to tool_node
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tools"

    # Otherwise, we're done
    return "end"
