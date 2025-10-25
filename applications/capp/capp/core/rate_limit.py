"""
Rate limiting for CAPP API

This module provides rate limiting functionality to protect against
abuse and ensure fair usage of the API.
"""

from typing import Callable
import structlog
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ..config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


def get_user_identifier(request: Request) -> str:
    """
    Get user identifier for rate limiting

    Uses the authenticated user's ID if available, otherwise falls back
    to IP address.

    Args:
        request: FastAPI request object

    Returns:
        User identifier string
    """
    # Try to get user ID from token if authenticated
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[
        f"{settings.RATE_LIMIT_PER_MINUTE}/minute",
        f"{settings.RATE_LIMIT_PER_HOUR}/hour"
    ],
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",  # Can also use "moving-window" for more accuracy
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom rate limit exceeded handler

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception

    Returns:
        JSON response with rate limit error
    """
    logger.warning(
        "Rate limit exceeded",
        path=request.url.path,
        method=request.method,
        client=get_user_identifier(request),
        limit=exc.detail
    )

    return Response(
        content='{"detail": "Rate limit exceeded. Please try again later."}',
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        headers={
            "Content-Type": "application/json",
            "Retry-After": str(60),  # Retry after 60 seconds
            "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(60)
        }
    )


# Rate limit decorators for different tiers
def rate_limit_strict(func: Callable) -> Callable:
    """
    Strict rate limit for sensitive operations

    Limits:
    - 10 requests per minute
    - 100 requests per hour
    """
    return limiter.limit("10/minute;100/hour")(func)


def rate_limit_moderate(func: Callable) -> Callable:
    """
    Moderate rate limit for standard operations

    Limits:
    - 60 requests per minute
    - 500 requests per hour
    """
    return limiter.limit("60/minute;500/hour")(func)


def rate_limit_relaxed(func: Callable) -> Callable:
    """
    Relaxed rate limit for public read operations

    Limits:
    - 100 requests per minute
    - 1000 requests per hour
    """
    return limiter.limit("100/minute;1000/hour")(func)


def rate_limit_exempt(func: Callable) -> Callable:
    """
    Exempt function from rate limiting

    Use for health checks and other critical endpoints
    """
    return limiter.exempt(func)
