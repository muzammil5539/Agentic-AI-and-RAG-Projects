"""Tool registry — central catalog of all available agent tools."""

from langchain_core.tools import BaseTool

from api.models.responses import ToolInfo
from tools.calculator import calculator
from tools.weather import weather
from tools.datetime_tool import datetime_tool
from tools.web_search import web_search
from tools.code_interpreter import code_interpreter
from tools.rag_search import rag_search


# ── Registry ─────────────────────────────────────────────────────

_TOOL_METADATA: dict[str, dict] = {
    "calculator": {"category": "custom", "description": "Evaluate math expressions safely (arithmetic, sqrt, log, trig)."},
    "weather": {"category": "custom", "description": "Get current weather and 3-day forecast for any location."},
    "datetime_tool": {"category": "custom", "description": "Get current date/time, convert timezones, date arithmetic."},
    "web_search": {"category": "openai_builtin", "description": "Search the web for current information."},
    "code_interpreter": {"category": "openai_builtin", "description": "Execute Python code for analysis and computation."},
    "rag_search": {"category": "custom", "description": "Search uploaded documents for relevant information."},
}

# All tools in a list for LangGraph binding
ALL_TOOLS: list[BaseTool] = [
    calculator,
    weather,
    datetime_tool,
    web_search,
    code_interpreter,
    rag_search,
]


def get_all_tools() -> list[BaseTool]:
    """Return all registered tools."""
    return ALL_TOOLS


def get_tool_by_name(name: str) -> BaseTool | None:
    """Look up a tool by name."""
    for t in ALL_TOOLS:
        if t.name == name:
            return t
    return None


def get_tool_infos() -> list[ToolInfo]:
    """Return Pydantic ToolInfo models for every registered tool."""
    infos = []
    for t in ALL_TOOLS:
        meta = _TOOL_METADATA.get(t.name, {})
        schema = t.args_schema.model_json_schema() if t.args_schema else {}
        infos.append(
            ToolInfo(
                name=t.name,
                description=meta.get("description", t.description or ""),
                parameters=schema,
                category=meta.get("category", "custom"),
            )
        )
    return infos
