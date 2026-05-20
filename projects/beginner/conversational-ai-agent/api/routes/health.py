"""Health check endpoint."""

from fastapi import APIRouter

from api.models.responses import HealthResponse
from config import settings
from tools.registry import get_all_tools

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="""
Verify the server is running and retrieve available models and tools count.

No authentication required. Use this endpoint to confirm connectivity before
making API calls or opening a WebSocket connection.

Example response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o4-mini"],
  "tools_count": 6
}
```
""",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="1.0.0",
        models=settings.AVAILABLE_MODELS,
        tools_count=len(get_all_tools()),
    )
