"""
Admin reconciliation endpoints

GET  /api/v1/admin/reconciliation/run    — trigger a reconciliation check
GET  /api/v1/admin/reconciliation/status — return the last cached result

Backed by ReconciliationService.check_integrity(), which compares the
internal ledger (Redis/DB) against live on-chain balances for APTOS and
POLYGON and alerts on drift > 0.01%.

Restricted to users with the "admin" role.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ....models.user import User
from ....services.reconciliation import ReconciliationService
from ....core.redis import get_cache
from ....api.dependencies.auth import get_current_active_user

logger = structlog.get_logger(__name__)
router = APIRouter()

_CACHE_KEY = "reconciliation:last_result"
_CACHE_TTL = 300  # 5 minutes


def _require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


class ChainCheck(BaseModel):
    chain: str
    internal_balance: Optional[float] = None
    on_chain_balance: Optional[float] = None
    drift_pct: Optional[float] = None
    status: str
    error: Optional[str] = None


class ReconciliationResult(BaseModel):
    timestamp: str
    status: str  # HEALTHY | CRITICAL_DRIFT
    checks: List[ChainCheck]
    cached: bool = False


@router.get(
    "/run",
    response_model=ReconciliationResult,
    status_code=status.HTTP_200_OK,
    summary="Run reconciliation",
    description=(
        "Trigger a live reconciliation check — compares the internal ledger "
        "balance against the real on-chain balance for each supported chain. "
        "Returns CRITICAL_DRIFT if any chain drifts more than 0.01%. "
        "Result is cached for 5 minutes; use /status to retrieve the cached copy."
    ),
)
async def run_reconciliation(
    _admin: User = Depends(_require_admin),
) -> ReconciliationResult:
    cache = get_cache()
    try:
        service = ReconciliationService()
        report: Dict[str, Any] = await service.check_integrity()
    except Exception as exc:
        logger.error("reconciliation_run_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reconciliation failed: {exc}",
        )

    # Cache for /status
    try:
        await cache.set(_CACHE_KEY, report, _CACHE_TTL)
    except Exception:
        pass  # caching is best-effort

    checks = [ChainCheck(**c) for c in report.get("checks", [])]
    return ReconciliationResult(
        timestamp=report.get("timestamp", datetime.now(timezone.utc).isoformat()),
        status=report.get("status", "UNKNOWN"),
        checks=checks,
        cached=False,
    )


@router.get(
    "/status",
    response_model=ReconciliationResult,
    status_code=status.HTTP_200_OK,
    summary="Last reconciliation result",
    description=(
        "Return the most recent cached reconciliation result (up to 5 minutes old). "
        "Call /run first to get a fresh check."
    ),
)
async def reconciliation_status(
    _admin: User = Depends(_require_admin),
) -> ReconciliationResult:
    cache = get_cache()
    try:
        cached = await cache.get(_CACHE_KEY)
    except Exception:
        cached = None

    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reconciliation result cached — call /run first",
        )

    checks = [ChainCheck(**c) for c in cached.get("checks", [])]
    return ReconciliationResult(
        timestamp=cached.get("timestamp", ""),
        status=cached.get("status", "UNKNOWN"),
        checks=checks,
        cached=True,
    )
