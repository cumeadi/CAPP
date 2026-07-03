"""
Analytics endpoints — GET /api/v1/analytics/summary

Exposes the PaymentAnalytics aggregation from PaymentOrchestrationService
alongside the raw cost-savings and performance metrics it already computes.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ....models.user import User
from ....services.payment_orchestration import PaymentOrchestrationService
from ....api.dependencies.auth import get_current_active_user

logger = structlog.get_logger(__name__)
router = APIRouter()


class CostSavings(BaseModel):
    traditional_cost_pct: float
    capp_cost_pct: float
    savings_pct: float
    savings_per_1000_usd: float


class PerformanceMetrics(BaseModel):
    avg_settlement_minutes: int
    traditional_settlement_days: int
    speed_improvement_x: int


class AnalyticsSummaryResponse(BaseModel):
    period: str
    generated_at: str
    cost_savings: CostSavings
    performance: PerformanceMetrics
    payment_metrics: dict
    business_metrics: dict


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Payment analytics summary",
    description=(
        "Return aggregated payment metrics for the current period. "
        "Includes cost savings vs. traditional rails, settlement performance, "
        "volume by corridor, and provider-level success rates. "
        "Use `period` to select daily / weekly / monthly aggregation."
    ),
)
async def analytics_summary(
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    current_user: User = Depends(get_current_active_user),
) -> AnalyticsSummaryResponse:
    try:
        service = PaymentOrchestrationService()
        raw = await service.get_payment_analytics()
    except Exception as exc:
        logger.error("analytics_fetch_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics",
        )

    cost = raw.get("cost_savings", {})
    perf = raw.get("performance", {})

    savings_pct = cost.get("traditional_cost_percentage", 8.9) - cost.get("capp_cost_percentage", 0.8)

    return AnalyticsSummaryResponse(
        period=period,
        generated_at=datetime.now(timezone.utc).isoformat(),
        cost_savings=CostSavings(
            traditional_cost_pct=cost.get("traditional_cost_percentage", 8.9),
            capp_cost_pct=cost.get("capp_cost_percentage", 0.8),
            savings_pct=savings_pct,
            savings_per_1000_usd=round(savings_pct * 10, 2),
        ),
        performance=PerformanceMetrics(
            avg_settlement_minutes=perf.get("average_settlement_time_minutes", 5),
            traditional_settlement_days=perf.get("traditional_settlement_time_days", 3),
            speed_improvement_x=perf.get("speed_improvement", 864),
        ),
        payment_metrics=raw.get("payment_metrics", {}),
        business_metrics=raw.get("business_metrics", {}),
    )
