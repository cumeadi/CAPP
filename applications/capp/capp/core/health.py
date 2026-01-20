"""
Health Check System for CAPP

Provides deep health checks for all critical services including database,
Redis, and system status.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum
import asyncio

import structlog
from sqlalchemy import text
from pydantic import BaseModel

from .database import AsyncSessionLocal
from .redis import get_cache
from ..config.settings import get_settings

logger = structlog.get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Health information for a single service"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = {}
    checked_at: datetime


class SystemHealth(BaseModel):
    """Overall system health information"""
    status: HealthStatus
    version: str
    uptime_seconds: Optional[float] = None
    services: Dict[str, ServiceHealth]
    checked_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthChecker:
    """
    Health checker for CAPP services.

    Performs deep health checks on all critical services and dependencies.
    """

    def __init__(self):
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        self.startup_time = datetime.now(timezone.utc)

    async def check_database(self) -> ServiceHealth:
        """
        Check database health.

        Returns:
            ServiceHealth: Database health status
        """
        start_time = asyncio.get_event_loop().time()
        checked_at = datetime.now(timezone.utc)

        try:
            async with AsyncSessionLocal() as session:
                # Execute simple query to check connectivity
                result = await session.execute(text("SELECT 1"))
                result.scalar()

                # Check if we can connect to the database
                response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

                return ServiceHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection is healthy",
                    response_time_ms=round(response_time_ms, 2),
                    details={
                        "database_url": self._mask_connection_string(self.settings.DATABASE_URL)
                    },
                    checked_at=checked_at
                )

        except Exception as e:
            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            self.logger.error("Database health check failed", error=str(e))

            return ServiceHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=round(response_time_ms, 2),
                details={"error": str(e)},
                checked_at=checked_at
            )

    async def check_redis(self) -> ServiceHealth:
        """
        Check Redis health.

        Returns:
            ServiceHealth: Redis health status
        """
        start_time = asyncio.get_event_loop().time()
        checked_at = datetime.now(timezone.utc)

        try:
            cache = get_cache()

            # Perform a simple ping to check connectivity
            await cache.ping()

            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Get Redis info if available
            info = await cache.info("server")
            redis_version = info.get("redis_version", "unknown")

            return ServiceHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection is healthy",
                response_time_ms=round(response_time_ms, 2),
                details={
                    "redis_url": self._mask_connection_string(self.settings.REDIS_URL),
                    "redis_version": redis_version
                },
                checked_at=checked_at
            )

        except Exception as e:
            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            self.logger.error("Redis health check failed", error=str(e))

            return ServiceHealth(
                name="redis",
                status=HealthStatus.DEGRADED,  # Redis is not critical, so degraded not unhealthy
                message=f"Redis connection failed: {str(e)}",
                response_time_ms=round(response_time_ms, 2),
                details={"error": str(e)},
                checked_at=checked_at
            )

    async def check_all_services(self) -> SystemHealth:
        """
        Check health of all services.

        Returns:
            SystemHealth: Overall system health
        """
        checked_at = datetime.now(timezone.utc)

        # Run all health checks concurrently
        health_checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            return_exceptions=True
        )

        # Process results
        services = {}
        for health in health_checks:
            if isinstance(health, ServiceHealth):
                services[health.name] = health
            elif isinstance(health, Exception):
                # Handle unexpected exceptions from health checks
                self.logger.error("Health check raised unexpected exception", error=str(health))
                services["unknown"] = ServiceHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(health)}",
                    checked_at=checked_at
                )

        # Determine overall system health
        overall_status = self._determine_overall_status(services)

        # Calculate uptime
        uptime_seconds = (checked_at - self.startup_time).total_seconds()

        return SystemHealth(
            status=overall_status,
            version="1.0.0",
            uptime_seconds=round(uptime_seconds, 2),
            services=services,
            checked_at=checked_at
        )

    async def check_readiness(self) -> bool:
        """
        Check if the system is ready to accept traffic.

        Returns:
            bool: True if ready, False otherwise
        """
        health = await self.check_all_services()
        # System is ready if not unhealthy (degraded is still acceptable)
        return health.status != HealthStatus.UNHEALTHY

    async def check_liveness(self) -> bool:
        """
        Check if the system is alive (basic liveness check).

        Returns:
            bool: True if alive, False otherwise
        """
        # Liveness check is simpler - just check if we can respond
        return True

    def _determine_overall_status(self, services: Dict[str, ServiceHealth]) -> HealthStatus:
        """
        Determine overall system health based on individual service health.

        Args:
            services: Dictionary of service health statuses

        Returns:
            HealthStatus: Overall system health
        """
        if not services:
            return HealthStatus.UNHEALTHY

        # Count statuses
        unhealthy_count = sum(1 for s in services.values() if s.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for s in services.values() if s.status == HealthStatus.DEGRADED)

        # If any critical service is unhealthy, system is unhealthy
        # Database is critical, Redis is not
        critical_services = ["database"]
        critical_unhealthy = any(
            services[s].status == HealthStatus.UNHEALTHY
            for s in critical_services
            if s in services
        )

        if critical_unhealthy:
            return HealthStatus.UNHEALTHY

        # If any service is degraded or unhealthy, system is degraded
        if degraded_count > 0 or unhealthy_count > 0:
            return HealthStatus.DEGRADED

        # All services are healthy
        return HealthStatus.HEALTHY

    def _mask_connection_string(self, connection_string: str) -> str:
        """
        Mask sensitive information in connection strings.

        Args:
            connection_string: The connection string to mask

        Returns:
            str: Masked connection string
        """
        import re

        # Mask password in connection strings
        # Matches patterns like: user:password@host
        masked = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', connection_string)
        return masked


# Global health checker instance
health_checker = HealthChecker()


async def get_health() -> SystemHealth:
    """
    Get current system health.

    Returns:
        SystemHealth: Current system health information
    """
    return await health_checker.check_all_services()


async def get_readiness() -> Dict[str, Any]:
    """
    Get readiness status.

    Returns:
        Dict: Readiness information
    """
    ready = await health_checker.check_readiness()
    return {
        "ready": ready,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def get_liveness() -> Dict[str, Any]:
    """
    Get liveness status.

    Returns:
        Dict: Liveness information
    """
    alive = await health_checker.check_liveness()
    return {
        "alive": alive,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
