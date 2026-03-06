"""
Unit tests for the health-check system:
  - HealthChecker.check_database  (healthy / unhealthy)
  - HealthChecker.check_redis     (healthy / degraded)
  - HealthChecker.check_all_services
  - HealthChecker._determine_overall_status
  - get_health / get_readiness / get_liveness helpers
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from applications.capp.capp.core.health import (
    HealthChecker, HealthStatus, ServiceHealth,
    get_health, get_readiness, get_liveness,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _service_health(name: str, status: HealthStatus) -> ServiceHealth:
    return ServiceHealth(
        name=name,
        status=status,
        message="test",
        checked_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# check_database
# ---------------------------------------------------------------------------

class TestCheckDatabase:

    @pytest.mark.asyncio
    async def test_healthy_when_query_succeeds(self, mocker):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_session)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mocker.patch(
            "applications.capp.capp.core.health.AsyncSessionLocal",
            return_value=ctx,
        )

        checker = HealthChecker()
        result = await checker.check_database()

        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_unhealthy_when_query_raises(self, mocker):
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(side_effect=Exception("connection refused"))
        ctx.__aexit__ = AsyncMock(return_value=False)

        mocker.patch(
            "applications.capp.capp.core.health.AsyncSessionLocal",
            return_value=ctx,
        )

        checker = HealthChecker()
        result = await checker.check_database()

        assert result.status == HealthStatus.UNHEALTHY
        assert "connection refused" in result.message


# ---------------------------------------------------------------------------
# check_redis
# ---------------------------------------------------------------------------

class TestCheckRedis:

    @pytest.mark.asyncio
    async def test_healthy_when_ping_succeeds(self, fake_cache, mocker):
        mocker.patch(
            "applications.capp.capp.core.health.get_cache",
            return_value=fake_cache,
        )

        checker = HealthChecker()
        result = await checker.check_redis()

        assert result.status == HealthStatus.HEALTHY
        assert result.details.get("redis_version") == "7.0.0-mock"

    @pytest.mark.asyncio
    async def test_degraded_when_ping_fails(self, mocker):
        bad_cache = MagicMock()
        bad_cache.ping = AsyncMock(side_effect=ConnectionError("redis unreachable"))

        mocker.patch(
            "applications.capp.capp.core.health.get_cache",
            return_value=bad_cache,
        )

        checker = HealthChecker()
        result = await checker.check_redis()

        assert result.status == HealthStatus.DEGRADED


# ---------------------------------------------------------------------------
# _determine_overall_status
# ---------------------------------------------------------------------------

class TestDetermineOverallStatus:

    def test_all_healthy(self):
        checker = HealthChecker()
        services = {
            "database": _service_health("database", HealthStatus.HEALTHY),
            "redis": _service_health("redis", HealthStatus.HEALTHY),
        }
        assert checker._determine_overall_status(services) == HealthStatus.HEALTHY

    def test_degraded_redis_returns_degraded(self):
        checker = HealthChecker()
        services = {
            "database": _service_health("database", HealthStatus.HEALTHY),
            "redis": _service_health("redis", HealthStatus.DEGRADED),
        }
        assert checker._determine_overall_status(services) == HealthStatus.DEGRADED

    def test_unhealthy_database_returns_unhealthy(self):
        checker = HealthChecker()
        services = {
            "database": _service_health("database", HealthStatus.UNHEALTHY),
            "redis": _service_health("redis", HealthStatus.HEALTHY),
        }
        assert checker._determine_overall_status(services) == HealthStatus.UNHEALTHY

    def test_empty_services_returns_unhealthy(self):
        checker = HealthChecker()
        assert checker._determine_overall_status({}) == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# check_all_services
# ---------------------------------------------------------------------------

class TestCheckAllServices:

    @pytest.mark.asyncio
    async def test_returns_system_health(self, mocker):
        checker = HealthChecker()
        mocker.patch.object(
            checker,
            "check_database",
            new=AsyncMock(return_value=_service_health("database", HealthStatus.HEALTHY)),
        )
        mocker.patch.object(
            checker,
            "check_redis",
            new=AsyncMock(return_value=_service_health("redis", HealthStatus.HEALTHY)),
        )

        health = await checker.check_all_services()

        assert health.status == HealthStatus.HEALTHY
        assert "database" in health.services
        assert "redis" in health.services

    @pytest.mark.asyncio
    async def test_propagates_unhealthy_db(self, mocker):
        checker = HealthChecker()
        mocker.patch.object(
            checker,
            "check_database",
            new=AsyncMock(return_value=_service_health("database", HealthStatus.UNHEALTHY)),
        )
        mocker.patch.object(
            checker,
            "check_redis",
            new=AsyncMock(return_value=_service_health("redis", HealthStatus.HEALTHY)),
        )

        health = await checker.check_all_services()
        assert health.status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# Readiness / Liveness helpers
# ---------------------------------------------------------------------------

class TestReadinessLiveness:

    @pytest.mark.asyncio
    async def test_ready_when_healthy(self, mocker):
        from applications.capp.capp.core import health as health_mod

        mock_checker = MagicMock()
        mock_checker.check_readiness = AsyncMock(return_value=True)
        mocker.patch.object(health_mod, "health_checker", mock_checker)

        result = await get_readiness()
        assert result["ready"] is True
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_not_ready_when_unhealthy(self, mocker):
        from applications.capp.capp.core import health as health_mod

        mock_checker = MagicMock()
        mock_checker.check_readiness = AsyncMock(return_value=False)
        mocker.patch.object(health_mod, "health_checker", mock_checker)

        result = await get_readiness()
        assert result["ready"] is False

    @pytest.mark.asyncio
    async def test_liveness_always_alive(self, mocker):
        from applications.capp.capp.core import health as health_mod

        mock_checker = MagicMock()
        mock_checker.check_liveness = AsyncMock(return_value=True)
        mocker.patch.object(health_mod, "health_checker", mock_checker)

        result = await get_liveness()
        assert result["alive"] is True


# ---------------------------------------------------------------------------
# Mask connection string
# ---------------------------------------------------------------------------

class TestMaskConnectionString:

    def test_masks_password(self):
        checker = HealthChecker()
        raw = "postgresql+asyncpg://user:s3cr3t@localhost/db"
        masked = checker._mask_connection_string(raw)
        assert "s3cr3t" not in masked
        assert "***" in masked

    def test_no_password_unchanged(self):
        checker = HealthChecker()
        raw = "redis://localhost:6379"
        assert checker._mask_connection_string(raw) == raw
