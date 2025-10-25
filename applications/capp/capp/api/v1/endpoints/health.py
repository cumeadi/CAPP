"""
Health Check API Endpoints

Provides health, readiness, and liveness endpoints for monitoring.
"""

from typing import Dict, Any
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from ....core.health import get_health, get_readiness, get_liveness, HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(response: Response) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Returns detailed health information about all system services.
    Sets appropriate HTTP status codes based on overall system health.

    Returns:
        Dict: System health information including all service statuses
    """
    health = await get_health()

    # Set HTTP status code based on health status
    if health.status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif health.status == HealthStatus.DEGRADED:
        response.status_code = status.HTTP_200_OK  # Still accepting traffic
    else:
        response.status_code = status.HTTP_200_OK

    return health.dict()


@router.get("/health/ready")
async def readiness_check(response: Response) -> Dict[str, Any]:
    """
    Readiness check endpoint.

    Indicates whether the service is ready to accept traffic.
    Used by load balancers and orchestrators (Kubernetes, etc.).

    Returns:
        Dict: Readiness status
    """
    readiness = await get_readiness()

    # Set appropriate status code
    if readiness["ready"]:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return readiness


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint.

    Indicates whether the service is alive and responding.
    Used by orchestrators to determine if the service should be restarted.

    Returns:
        Dict: Liveness status
    """
    liveness = await get_liveness()
    return liveness
