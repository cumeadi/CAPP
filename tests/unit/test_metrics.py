"""
Unit tests for MetricsCollector (applications/capp/capp/services/metrics.py).

Covers:
  - record_payment_metrics (success / failure)
  - get_payment_metrics (counts, rates, avg processing time)
  - get_business_metrics
  - reset_metrics
  - P95 / P99 latency helpers (added in this sprint)
"""
from decimal import Decimal

import pytest

from applications.capp.capp.services.metrics import MetricsCollector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def collector(fake_cache):
    col = MetricsCollector()
    col.cache = fake_cache
    return col


# ---------------------------------------------------------------------------
# record_payment_metrics
# ---------------------------------------------------------------------------

class TestRecordPaymentMetrics:

    @pytest.mark.asyncio
    async def test_records_successful_payment(self, collector):
        await collector.record_payment_metrics(
            payment_id="pay_001",
            amount=Decimal("100.00"),
            processing_time=1.5,
            success=True,
            corridor="KE-UG",
        )
        total = await collector.cache.hget("metrics:payments:total", "count")
        assert int(total) == 1
        ok_count = await collector.cache.hget("metrics:payments:successful", "count")
        assert int(ok_count) == 1

    @pytest.mark.asyncio
    async def test_records_failed_payment(self, collector):
        await collector.record_payment_metrics(
            payment_id="pay_002",
            amount=Decimal("50.00"),
            processing_time=0.5,
            success=False,
            corridor="NG-GH",
        )
        fail_count = await collector.cache.hget("metrics:payments:failed", "count")
        assert int(fail_count) == 1

    @pytest.mark.asyncio
    async def test_processing_time_stored(self, collector):
        await collector.record_payment_metrics(
            payment_id="p3",
            amount=Decimal("10.00"),
            processing_time=2.25,
            success=True,
            corridor="ZA-BW",
        )
        times = await collector.cache.lrange("metrics:processing_times", 0, -1)
        assert len(times) >= 1


# ---------------------------------------------------------------------------
# get_payment_metrics
# ---------------------------------------------------------------------------

class TestGetPaymentMetrics:

    @pytest.mark.asyncio
    async def test_empty_state_returns_zeros(self, collector):
        metrics = await collector.get_payment_metrics()
        assert metrics["total_count"] == 0
        assert metrics["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_success_rate_computed_correctly(self, collector):
        for i in range(8):
            await collector.record_payment_metrics(
                f"p{i}", Decimal("100"), 1.0, True, "KE-UG"
            )
        for i in range(2):
            await collector.record_payment_metrics(
                f"f{i}", Decimal("100"), 1.0, False, "KE-UG"
            )

        metrics = await collector.get_payment_metrics()
        assert metrics["total_count"] == 10
        assert abs(metrics["success_rate"] - 0.8) < 0.001

    @pytest.mark.asyncio
    async def test_average_processing_time(self, collector):
        times = [1.0, 2.0, 3.0]
        for t in times:
            await collector.record_payment_metrics("p", Decimal("1"), t, True, "x-y")

        metrics = await collector.get_payment_metrics()
        # Average of 1, 2, 3 → 2.0
        assert abs(metrics["average_processing_time"] - 2.0) < 0.01


# ---------------------------------------------------------------------------
# get_business_metrics
# ---------------------------------------------------------------------------

class TestGetBusinessMetrics:

    @pytest.mark.asyncio
    async def test_returns_expected_keys(self, collector):
        biz = await collector.get_business_metrics()
        expected = {"total_payments", "total_volume", "success_rate",
                    "average_processing_time", "top_corridors"}
        assert expected.issubset(biz.keys())


# ---------------------------------------------------------------------------
# reset_metrics
# ---------------------------------------------------------------------------

class TestResetMetrics:

    @pytest.mark.asyncio
    async def test_reset_clears_payment_data(self, collector):
        await collector.record_payment_metrics("p", Decimal("100"), 1.0, True, "KE-UG")
        await collector.reset_metrics("payments")
        metrics = await collector.get_payment_metrics()
        assert metrics["total_count"] == 0

    @pytest.mark.asyncio
    async def test_reset_all_clears_all(self, collector):
        await collector.record_payment_metrics("p", Decimal("100"), 1.0, True, "KE-UG")
        await collector.reset_metrics()
        metrics = await collector.get_payment_metrics()
        assert metrics["total_count"] == 0


# ---------------------------------------------------------------------------
# P95 / P99 latency tracking
# ---------------------------------------------------------------------------

class TestP95P99Latency:
    """
    Tests for the get_latency_percentiles method added in this sprint.
    The method must return p50, p95, and p99 from the stored processing times.
    """

    @pytest.mark.asyncio
    async def test_percentiles_computed(self, collector):
        # Record 100 payments with deterministic times 1..100 ms
        for i in range(1, 101):
            await collector.record_payment_metrics(
                f"p{i}", Decimal("1"), float(i) / 1000.0, True, "KE-UG"
            )

        percentiles = await collector.get_latency_percentiles()
        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

        # p95 should be higher than p50
        assert percentiles["p95"] > percentiles["p50"]
        # p99 should be >= p95
        assert percentiles["p99"] >= percentiles["p95"]

    @pytest.mark.asyncio
    async def test_empty_state_returns_zeros(self, collector):
        percentiles = await collector.get_latency_percentiles()
        assert percentiles["p50"] == 0.0
        assert percentiles["p95"] == 0.0
        assert percentiles["p99"] == 0.0
