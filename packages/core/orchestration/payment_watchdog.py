"""
Payment Watchdog

A background cron-style job that detects payments stuck in the SETTLING
state for more than SETTLING_TIMEOUT_MINUTES (default: 30) and issues
compensating transactions (refunds) via the saga rollback mechanism.

Schedule: every WATCHDOG_INTERVAL_SECONDS (default: 300 = 5 minutes).

Lifecycle
---------
* Call ``await watchdog.start()`` when the application boots to launch the
  background loop as an asyncio Task.
* Call ``await watchdog.stop()`` on shutdown for a clean cancellation.
* For one-shot / test invocations use ``await watchdog.run_once()``.

Integration
-----------
The watchdog requires:
  1. A ``PaymentWorkflowOrchestrator`` instance (for rollback_payment).
  2. An async SQLAlchemy session factory (``AsyncSessionLocal`` from
     ``applications.capp.capp.core.database``).
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

import structlog

from packages.core.orchestration.payment_workflow_orchestrator import (
    PaymentWorkflowOrchestrator,
    PaymentWorkflowStep,
    RollbackResult,
)
from packages.core.orchestration.payment_step_executor import PaymentStepContext

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WATCHDOG_INTERVAL_SECONDS: int = 300          # 5 minutes
SETTLING_TIMEOUT_MINUTES: int = 30            # payments stuck longer than this get refunded

# Steps that are guaranteed to have been completed before a payment reaches
# SETTLING — rolled back in reverse order by rollback_payment().
_STEPS_BEFORE_SETTLING: List[str] = [
    PaymentWorkflowStep.CREATE_PAYMENT,
    PaymentWorkflowStep.VALIDATE_PAYMENT,
    PaymentWorkflowStep.OPTIMIZE_ROUTE,
    PaymentWorkflowStep.VALIDATE_COMPLIANCE,
    PaymentWorkflowStep.CHECK_LIQUIDITY,
    PaymentWorkflowStep.LOCK_EXCHANGE_RATE,
    PaymentWorkflowStep.EXECUTE_MMO,
    PaymentWorkflowStep.SETTLE_PAYMENT,
]


# ---------------------------------------------------------------------------
# Data class for a stuck payment record
# ---------------------------------------------------------------------------

@dataclass
class StuckPayment:
    """Lightweight representation of a payment stuck in SETTLING."""
    payment_id: str
    settled_at: datetime
    payment_data: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------

class PaymentWatchdog:
    """
    Monitors for payments stuck in the SETTLING state and issues refunds.

    A payment is considered stuck when its ``settled_at`` timestamp is older
    than ``settling_timeout_minutes`` AND its ``status`` is still ``"settling"``.

    The watchdog runs as a persistent asyncio background task, sleeping for
    ``interval_seconds`` between each scan-and-refund cycle.
    """

    def __init__(
        self,
        orchestrator: PaymentWorkflowOrchestrator,
        db_session_factory: Callable,
        interval_seconds: int = WATCHDOG_INTERVAL_SECONDS,
        settling_timeout_minutes: int = SETTLING_TIMEOUT_MINUTES,
    ) -> None:
        """
        Args:
            orchestrator:            Initialised PaymentWorkflowOrchestrator.
            db_session_factory:      Async callable that returns an
                                     ``AsyncSession`` context-manager (e.g.
                                     ``AsyncSessionLocal`` from database.py).
            interval_seconds:        Seconds to sleep between scans.
            settling_timeout_minutes: Payments in SETTLING older than this
                                     many minutes are treated as stuck.
        """
        self.orchestrator = orchestrator
        self.db_session_factory = db_session_factory
        self.interval_seconds = interval_seconds
        self.settling_timeout_minutes = settling_timeout_minutes
        self.logger = structlog.get_logger(__name__)

        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public lifecycle API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Launch the watchdog background loop as an asyncio Task."""
        if self._running:
            self.logger.warning("PaymentWatchdog is already running — ignoring start()")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="payment_watchdog")
        self.logger.info(
            "PaymentWatchdog started",
            interval_seconds=self.interval_seconds,
            settling_timeout_minutes=self.settling_timeout_minutes,
        )

    async def stop(self) -> None:
        """Stop the watchdog loop gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("PaymentWatchdog stopped")

    async def run_once(self) -> None:
        """
        Trigger a single scan-and-refund cycle synchronously.

        Useful for one-shot cron invocations or integration tests.
        """
        await self._scan_and_refund()

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _run_loop(self) -> None:
        """Persistent background loop — scans every interval_seconds."""
        while self._running:
            try:
                await self._scan_and_refund()
            except Exception as exc:
                # Swallow unexpected errors so the loop never dies silently.
                self.logger.error(
                    "PaymentWatchdog scan raised an unexpected error",
                    error=str(exc),
                    exc_info=True,
                )
            await asyncio.sleep(self.interval_seconds)

    # ------------------------------------------------------------------
    # Scan helpers
    # ------------------------------------------------------------------

    async def _scan_and_refund(self) -> None:
        """
        1. Calculate the cutoff timestamp (now − settling_timeout_minutes).
        2. Query for payments with status='settling' older than the cutoff.
        3. Attempt a refund for each stuck payment.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.settling_timeout_minutes)

        self.logger.info(
            "Watchdog scanning for stuck payments",
            cutoff=cutoff.isoformat(),
            target_status="settling",
        )

        stuck_payments = await self._find_stuck_payments(cutoff)

        if not stuck_payments:
            self.logger.info("Watchdog scan complete: no stuck payments found")
            return

        self.logger.warning(
            "Stuck payments detected — initiating refunds",
            count=len(stuck_payments),
            payment_ids=[p.payment_id for p in stuck_payments],
        )

        for stuck in stuck_payments:
            try:
                await self._refund_stuck_payment(stuck)
            except Exception as exc:
                self.logger.error(
                    "Failed to process refund for stuck payment",
                    payment_id=stuck.payment_id,
                    error=str(exc),
                    exc_info=True,
                )

    async def _find_stuck_payments(self, cutoff: datetime) -> List[StuckPayment]:
        """
        Query the database for payments with:
          - status  = 'settling'
          - settled_at <= cutoff   (has been settling for too long)

        Returns an empty list if the DB is unreachable or the query fails.
        """
        from sqlalchemy import select
        from applications.capp.capp.core.database import Payment

        try:
            async with self.db_session_factory() as session:
                stmt = (
                    select(Payment)
                    .where(Payment.status == "settling")
                    .where(Payment.settled_at <= cutoff)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

            return [
                StuckPayment(
                    payment_id=str(row.id),
                    settled_at=row.settled_at,
                    payment_data={
                        "payment_id": str(row.id),
                        "reference_id": row.reference_id,
                        "amount": float(row.amount),
                        "from_currency": row.from_currency,
                        "to_currency": row.to_currency,
                        "status": row.status,
                    },
                )
                for row in rows
            ]
        except Exception as exc:
            self.logger.error(
                "Watchdog failed to query stuck payments",
                error=str(exc),
                exc_info=True,
            )
            return []

    # ------------------------------------------------------------------
    # Refund helpers
    # ------------------------------------------------------------------

    async def _refund_stuck_payment(self, stuck: StuckPayment) -> RollbackResult:
        """
        Orchestrate compensating transactions for a single stuck payment.

        Builds a minimal PaymentStepContext (without live step results — those
        are unavailable for a payment that never finished), then delegates to
        ``rollback_payment()`` with the ordered list of steps that must have
        been completed before reaching SETTLING.

        After the rollback attempt, persists the new status ('refunded' or
        'refund_failed') back to the database.
        """
        self.logger.warning(
            "Initiating rollback for stuck payment",
            payment_id=stuck.payment_id,
            stuck_since=stuck.settled_at.isoformat(),
        )

        context = PaymentStepContext(
            payment_id=stuck.payment_id,
            step_id=PaymentWorkflowStep.SETTLE_PAYMENT,
            step_name="Settle Payment",
            payment_data=stuck.payment_data,
        )

        # No live agents are passed — each executor's _rollback_step()
        # handles a missing agent gracefully (no-op for read-only steps,
        # FAILED result for critical irreversible steps like MMO / on-chain).
        result: RollbackResult = await self.orchestrator.rollback_payment(
            payment_id=stuck.payment_id,
            completed_steps=_STEPS_BEFORE_SETTLING,
            context=context,
            agents=[],
        )

        await self._persist_refund_status(stuck.payment_id, result)

        self.logger.info(
            "Stuck payment refund attempt complete",
            payment_id=stuck.payment_id,
            success=result.success,
            rolled_back_steps=result.rolled_back_steps,
            failed_rollbacks=result.failed_rollbacks,
        )

        return result

    async def _persist_refund_status(
        self,
        payment_id: str,
        rollback_result: RollbackResult,
    ) -> None:
        """
        Update the ``payments`` row with the outcome of the refund attempt:
          - 'refunded'      if all compensating transactions succeeded
          - 'refund_failed' if one or more compensating transactions failed
                            (requires manual intervention)
        """
        from sqlalchemy import update
        from applications.capp.capp.core.database import Payment

        new_status = "refunded" if rollback_result.success else "refund_failed"

        try:
            async with self.db_session_factory() as session:
                stmt = (
                    update(Payment)
                    .where(Payment.id == payment_id)
                    .values(
                        status=new_status,
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                await session.execute(stmt)
                await session.commit()

            self.logger.info(
                "Payment status updated after refund attempt",
                payment_id=payment_id,
                new_status=new_status,
            )
        except Exception as exc:
            self.logger.error(
                "Failed to persist refund status — DB update failed",
                payment_id=payment_id,
                intended_status=new_status,
                error=str(exc),
                exc_info=True,
            )
