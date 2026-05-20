"""Tools listing endpoint."""

from fastapi import APIRouter

from api.models.responses import ToolListResponse
from tools.registry import get_tool_infos

router = APIRouter(prefix="/api/v1", tags=["tools"])


@router.get(
    "/tools",
    response_model=ToolListResponse,
    summary="List available tools",
    description="""
Returns every tool the ReAct agent can call, with its name, description,
and full JSON Schema for the input parameters.

No authentication required.

Tools are grouped by category:
- **`custom`** — implemented in this project (calculator, weather, datetime, rag_search)
- **`openai_builtin`** — delegated to OpenAI native tools (web_search, code_interpreter)
""",
)
async def list_tools() -> ToolListResponse:
    """List all tools available to the agent."""
    return ToolListResponse(tools=get_tool_infos())
