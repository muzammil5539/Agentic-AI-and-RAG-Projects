"""Health check endpoint."""

from fastapi import APIRouter

from api.models.responses import HealthResponse
from config import settings
from tools.registry import get_all_tools

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="1.0.0",
        models=settings.AVAILABLE_MODELS,
        tools_count=len(get_all_tools()),
    )
