"""
Unit Tests for Payment Saga and Agent Event Bus
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from applications.capp.capp.agents.payment_saga import PaymentSaga
from applications.capp.capp.agents.event_bus import (
    AgentEventBus, AgentEvent, AgentEventType, agent_event_bus
)


# ─── PaymentSaga tests ────────────────────────────────────────────────────────

class TestPaymentSaga:
    """Tests for the Saga pattern orchestrator."""

    @pytest.fixture
    def payment_id(self):
        return uuid4()

    @pytest.fixture
    def saga(self, payment_id):
        return PaymentSaga(payment_id)

    @pytest.mark.asyncio
    async def test_no_compensations_rollback_is_safe(self, saga):
        """Rolling back a saga with no registered steps should not raise."""
        await saga.rollback()  # Must not raise

    @pytest.mark.asyncio
    async def test_single_compensation_is_executed_on_rollback(self, saga):
        """A single registered compensation must be called during rollback."""
        comp = AsyncMock()
        saga.register_compensation("step_a", comp)
        await saga.rollback()
        comp.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_compensations_run_in_reverse_order(self, saga):
        """Compensations must execute LIFO (last registered, first compensated)."""
        call_order = []

        async def comp_a():
            call_order.append("a")

        async def comp_b():
            call_order.append("b")

        async def comp_c():
            call_order.append("c")

        saga.register_compensation("a", comp_a)
        saga.register_compensation("b", comp_b)
        saga.register_compensation("c", comp_c)

        await saga.rollback()

        assert call_order == ["c", "b", "a"], f"Expected LIFO order, got {call_order}"

    @pytest.mark.asyncio
    async def test_failed_compensation_does_not_stop_rollback(self, saga):
        """If one compensation raises, the others must still execute."""
        executed = []

        async def failing_comp():
            raise RuntimeError("Compensation failure")

        async def ok_comp():
            executed.append("ok")

        saga.register_compensation("failing", failing_comp)
        saga.register_compensation("ok", ok_comp)

        # Should not raise even though one compensation fails
        await saga.rollback()

        assert "ok" in executed

    @pytest.mark.asyncio
    async def test_rollback_is_idempotent(self, saga):
        """Calling rollback twice must only execute compensations once."""
        comp = AsyncMock()
        saga.register_compensation("step", comp)

        await saga.rollback()
        await saga.rollback()  # Second call must be a no-op

        comp.assert_awaited_once()

    def test_completed_step_names_reflects_registered_steps(self, saga):
        """completed_step_names should list all registered step names."""
        saga.register_compensation("reserve_liquidity", AsyncMock())
        saga.register_compensation("lock_rate", AsyncMock())

        assert saga.completed_step_names == ["reserve_liquidity", "lock_rate"]


# ─── AgentEventBus tests ──────────────────────────────────────────────────────

class TestAgentEventBus:
    """Tests for the pub/sub event bus."""

    @pytest.fixture
    def bus(self):
        """Fresh event bus for each test."""
        return AgentEventBus()

    @pytest.fixture
    def payment_id(self):
        return uuid4()

    def _make_event(self, event_type: str, payment_id) -> AgentEvent:
        return AgentEvent(
            event_type=event_type,
            payment_id=payment_id,
            agent_type="test_agent",
        )

    @pytest.mark.asyncio
    async def test_subscriber_receives_published_event(self, bus, payment_id):
        """A subscriber must be called when a matching event is published."""
        received: list = []

        async def handler(event: AgentEvent):
            received.append(event)

        bus.subscribe(AgentEventType.ROUTE_SELECTED, handler)
        event = self._make_event(AgentEventType.ROUTE_SELECTED, payment_id)
        await bus.publish(event)

        assert len(received) == 1
        assert received[0].payment_id == payment_id

    @pytest.mark.asyncio
    async def test_subscriber_only_receives_its_event_type(self, bus, payment_id):
        """Subscribers must not be called for unrelated event types."""
        received: list = []

        async def handler(event: AgentEvent):
            received.append(event)

        bus.subscribe(AgentEventType.COMPLIANCE_PASSED, handler)
        await bus.publish(self._make_event(AgentEventType.ROUTE_SELECTED, payment_id))

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_notified(self, bus, payment_id):
        """All subscribers for an event type must be called concurrently."""
        calls: list = []

        async def h1(event):
            calls.append("h1")

        async def h2(event):
            calls.append("h2")

        bus.subscribe(AgentEventType.SETTLEMENT_COMPLETED, h1)
        bus.subscribe(AgentEventType.SETTLEMENT_COMPLETED, h2)
        await bus.publish(self._make_event(AgentEventType.SETTLEMENT_COMPLETED, payment_id))

        assert set(calls) == {"h1", "h2"}

    @pytest.mark.asyncio
    async def test_failing_handler_does_not_prevent_others(self, bus, payment_id):
        """If one handler raises, others must still be invoked."""
        called: list = []

        async def failing_handler(event):
            raise RuntimeError("handler error")

        async def ok_handler(event):
            called.append("ok")

        bus.subscribe(AgentEventType.PAYMENT_FAILED, failing_handler)
        bus.subscribe(AgentEventType.PAYMENT_FAILED, ok_handler)

        # Must not raise
        await bus.publish(self._make_event(AgentEventType.PAYMENT_FAILED, payment_id))

        assert "ok" in called

    @pytest.mark.asyncio
    async def test_event_history_is_recorded(self, bus, payment_id):
        """Published events must appear in get_payment_events()."""
        await bus.publish(self._make_event(AgentEventType.RATE_LOCKED, payment_id))
        await bus.publish(self._make_event(AgentEventType.COMPLIANCE_PASSED, payment_id))

        events = bus.get_payment_events(payment_id)
        assert len(events) == 2
        event_types = {e.event_type for e in events}
        assert AgentEventType.RATE_LOCKED in event_types
        assert AgentEventType.COMPLIANCE_PASSED in event_types

    @pytest.mark.asyncio
    async def test_get_payment_events_filters_by_payment(self, bus):
        """get_payment_events must only return events for the given payment."""
        pid_a = uuid4()
        pid_b = uuid4()

        await bus.publish(self._make_event(AgentEventType.ROUTE_SELECTED, pid_a))
        await bus.publish(self._make_event(AgentEventType.ROUTE_SELECTED, pid_b))

        assert len(bus.get_payment_events(pid_a)) == 1
        assert len(bus.get_payment_events(pid_b)) == 1

    def test_unsubscribe_removes_handler(self, bus, payment_id):
        """Unsubscribed handlers must not receive future events."""
        calls: list = []

        async def handler(event):
            calls.append("called")

        bus.subscribe(AgentEventType.LIQUIDITY_RESERVED, handler)
        bus.unsubscribe(AgentEventType.LIQUIDITY_RESERVED, handler)

        asyncio.get_event_loop().run_until_complete(
            bus.publish(self._make_event(AgentEventType.LIQUIDITY_RESERVED, payment_id))
        )

        assert calls == []

    def test_clear_history(self, bus, payment_id):
        """clear_history must empty the event log."""
        async def _publish():
            await bus.publish(self._make_event(AgentEventType.PAYMENT_COMPLETED, payment_id))

        asyncio.get_event_loop().run_until_complete(_publish())
        bus.clear_history()
        assert bus.get_payment_events(payment_id) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
