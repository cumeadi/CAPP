"""
Payment Saga for CAPP

Implements the Saga pattern for distributed payment transactions.
Each step registers a compensation action so that on failure, all
previously completed steps are cleanly rolled back.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, List, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

Compensation = Callable[[], Coroutine[Any, Any, None]]


class SagaStep:
    """A single step in the payment saga with its compensation action."""

    def __init__(self, name: str, compensation: Compensation):
        self.name = name
        self.compensation = compensation
        self.completed_at = datetime.now(timezone.utc)


class PaymentSaga:
    """
    Saga orchestrator for payment processing.

    Usage:
        saga = PaymentSaga(payment_id)

        # Execute step — if it succeeds, register compensation
        result = await some_agent.reserve_liquidity(payment)
        saga.register_compensation(
            "release_liquidity",
            lambda: some_agent.release_liquidity(result.reservation_id)
        )

        # On any failure, call rollback() to undo all completed steps
        await saga.rollback()
    """

    def __init__(self, payment_id: UUID):
        self.payment_id = payment_id
        self._completed_steps: List[SagaStep] = []
        self._rolled_back = False

    def register_compensation(self, step_name: str, compensation: Compensation) -> None:
        """
        Register a compensation for a successfully completed step.

        Compensations are executed in reverse order (LIFO) during rollback.
        """
        step = SagaStep(name=step_name, compensation=compensation)
        self._completed_steps.append(step)
        logger.debug(
            "Saga step completed",
            payment_id=str(self.payment_id),
            step=step_name,
        )

    async def rollback(self) -> None:
        """
        Execute all registered compensations in reverse order.

        Errors during compensation are logged but do not stop the rollback.
        """
        if self._rolled_back:
            logger.warning("Saga already rolled back", payment_id=str(self.payment_id))
            return

        self._rolled_back = True

        if not self._completed_steps:
            logger.info("No saga steps to roll back", payment_id=str(self.payment_id))
            return

        logger.info(
            "Rolling back payment saga",
            payment_id=str(self.payment_id),
            steps=len(self._completed_steps),
        )

        # Compensate in reverse (LIFO)
        for step in reversed(self._completed_steps):
            try:
                logger.info(
                    "Executing compensation",
                    payment_id=str(self.payment_id),
                    step=step.name,
                )
                await step.compensation()
            except Exception as e:
                # Log and continue — we must attempt all compensations
                logger.error(
                    "Compensation failed",
                    payment_id=str(self.payment_id),
                    step=step.name,
                    error=str(e),
                )

        logger.info("Saga rollback complete", payment_id=str(self.payment_id))

    @property
    def completed_step_names(self) -> List[str]:
        return [s.name for s in self._completed_steps]
