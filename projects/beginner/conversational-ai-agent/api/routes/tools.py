"""Tools listing endpoint."""

from fastapi import APIRouter

from api.models.responses import ToolListResponse
from tools.registry import get_tool_infos

router = APIRouter(prefix="/api/v1", tags=["tools"])


@router.get("/tools", response_model=ToolListResponse)
async def list_tools() -> ToolListResponse:
    """List all tools available to the agent."""
    return ToolListResponse(tools=get_tool_infos())
