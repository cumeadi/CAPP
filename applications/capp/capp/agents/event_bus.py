"""
Agent Event Bus for CAPP

Provides lightweight pub/sub messaging between agents to enable coordination,
parallel execution, and real-time event-driven workflows.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


# Event types emitted by each agent
class AgentEventType:
    # Route Optimization Agent
    ROUTE_SELECTED = "ROUTE_SELECTED"
    ROUTE_FAILED = "ROUTE_FAILED"

    # Exchange Rate Agent
    RATE_LOCKED = "RATE_LOCKED"
    RATE_UNLOCKED = "RATE_UNLOCKED"
    RATE_LOCK_FAILED = "RATE_LOCK_FAILED"

    # Compliance Agent
    COMPLIANCE_PASSED = "COMPLIANCE_PASSED"
    COMPLIANCE_FAILED = "COMPLIANCE_FAILED"

    # Liquidity Agent
    LIQUIDITY_RESERVED = "LIQUIDITY_RESERVED"
    LIQUIDITY_RELEASED = "LIQUIDITY_RELEASED"
    LIQUIDITY_INSUFFICIENT = "LIQUIDITY_INSUFFICIENT"

    # Settlement Agent
    SETTLEMENT_COMPLETED = "SETTLEMENT_COMPLETED"
    SETTLEMENT_FAILED = "SETTLEMENT_FAILED"

    # Payment lifecycle
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_ROLLED_BACK = "PAYMENT_ROLLED_BACK"


class AgentEvent:
    """An event emitted by an agent during payment processing"""

    def __init__(
        self,
        event_type: str,
        payment_id: UUID,
        agent_type: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        self.event_id = uuid4()
        self.event_type = event_type
        self.payment_id = payment_id
        self.agent_type = agent_type
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"AgentEvent({self.event_type}, payment={self.payment_id}, agent={self.agent_type})"


Handler = Callable[[AgentEvent], Coroutine[Any, Any, None]]


class AgentEventBus:
    """
    Lightweight async pub/sub event bus for agent coordination.

    Agents publish events after completing operations. Other agents or the
    orchestrator subscribe to react asynchronously — enabling parallelism
    and decoupled compensation logic.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Handler]] = defaultdict(list)
        self._event_history: List[AgentEvent] = []

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Register an async handler for a specific event type."""
        self._subscribers[event_type].append(handler)
        logger.debug("Event handler registered", event_type=event_type, handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        """Remove a handler for an event type."""
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: AgentEvent) -> None:
        """
        Publish an event and notify all subscribers concurrently.

        Errors in individual handlers are logged but do not block others.
        """
        self._event_history.append(event)
        logger.info(
            "Event published",
            event_type=event.event_type,
            payment_id=str(event.payment_id),
            agent=event.agent_type,
        )

        handlers = self._subscribers.get(event.event_type, [])
        if not handlers:
            return

        results = await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Event handler failed",
                    event_type=event.event_type,
                    handler=handlers[i].__name__,
                    error=str(result),
                )

    def get_payment_events(self, payment_id: UUID) -> List[AgentEvent]:
        """Return all events emitted for a specific payment."""
        return [e for e in self._event_history if e.payment_id == payment_id]

    def clear_history(self) -> None:
        """Clear event history (useful in tests)."""
        self._event_history.clear()


# Singleton bus shared across the payment pipeline
agent_event_bus = AgentEventBus()
