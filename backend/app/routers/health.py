"""
Health check endpoint.

Exposes a ``GET /health`` route that returns system diagnostics including
FFmpeg availability, disk space, and application version information.
"""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_health_service
from app.schemas.responses import HealthResponse
from app.services.health_checks import HealthCheckService

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
    description="Returns system health diagnostics including service availability, disk usage, and version info.",
)
async def health_check(
    service: HealthCheckService = Depends(get_health_service),
) -> HealthResponse:
    """Check application health and system diagnostics.

    Returns a comprehensive health report including:
    - Overall status (healthy / degraded / unhealthy)
    - FFmpeg availability
    - Temporary directory disk usage
    - Application version
    """
    return await service.run_checks()
