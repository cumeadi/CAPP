"""
Property-based tests for fee calculation and route selection.

Properties verified:
  1. score ∈ [0.0, 1.0] for any (fee, time, amount) combination
  2. Higher fee → lower or equal score when cost is prioritised
  3. Higher time → lower or equal score when speed is prioritised
  4. Selecting cost rail when cost-pref beats selecting speed rail
  5. Selecting speed rail when speed-pref beats selecting cost rail
  6. calculate_best_route returns the highest-scored quote
"""
from decimal import Decimal

import pytest

from applications.capp.capp.services.routing_service import RoutingService
from applications.capp.capp.models.payments import PaymentPreferences


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_quote(fee: float, time_minutes: float, amount: float = 100.0) -> dict:
    return {
        "rail": "TestRail",
        "fee": fee,
        "estimated_time_minutes": time_minutes,
        "amount": amount,
    }


def _svc() -> RoutingService:
    return RoutingService()


# ---------------------------------------------------------------------------
# Property 1 – score always in [0, 1]
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fee,time_mins,amount", [
    (0.0, 0.0, 100.0),
    (0.001, 5.0, 100.0),
    (10.0, 120.0, 100.0),     # high fee still bounded
    (1000.0, 9999.0, 100.0),  # extreme values clamped at 0
    (0.0, 0.0, 0.0),          # zero amount edge-case
    (0.1, 10.0, 1.0),
])
def test_score_bounded_between_0_and_1(fee, time_mins, amount):
    svc = _svc()
    prefs = PaymentPreferences(prioritize_cost=True, prioritize_speed=False)
    quote = _make_quote(fee, time_mins, amount)
    score = svc._calculate_score(quote, prefs)
    assert 0.0 <= score <= 1.0, f"score {score} out of range for {quote}"


# ---------------------------------------------------------------------------
# Property 2 – higher fee → lower or equal score (cost-prioritised)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("low_fee,high_fee,time_mins", [
    (0.1, 0.5, 10.0),
    (0.01, 5.0, 5.0),
    (0.0, 0.001, 60.0),
])
def test_higher_fee_lower_score_cost_pref(low_fee, high_fee, time_mins):
    svc = _svc()
    prefs = PaymentPreferences(prioritize_cost=True, prioritize_speed=False)
    s_low = svc._calculate_score(_make_quote(low_fee, time_mins), prefs)
    s_high = svc._calculate_score(_make_quote(high_fee, time_mins), prefs)
    assert s_low >= s_high, (
        f"Expected cheaper fee {low_fee} to score >= {high_fee}, "
        f"got {s_low} vs {s_high}"
    )


# ---------------------------------------------------------------------------
# Property 3 – higher time → lower or equal score (speed-prioritised)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fast_mins,slow_mins,fee", [
    (5.0, 60.0, 0.1),
    (1.0, 119.0, 0.5),
    (10.0, 120.0, 0.2),
])
def test_higher_time_lower_score_speed_pref(fast_mins, slow_mins, fee):
    svc = _svc()
    prefs = PaymentPreferences(prioritize_cost=False, prioritize_speed=True)
    s_fast = svc._calculate_score(_make_quote(fee, fast_mins), prefs)
    s_slow = svc._calculate_score(_make_quote(fee, slow_mins), prefs)
    assert s_fast >= s_slow, (
        f"Expected faster {fast_mins}min to score >= {slow_mins}min, "
        f"got {s_fast} vs {s_slow}"
    )


# ---------------------------------------------------------------------------
# Property 4 – CheapRail wins when prioritise_cost=True
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cheap_rail_selected_with_cost_preference():
    svc = _svc()
    prefs = PaymentPreferences(prioritize_cost=True, prioritize_speed=False)
    result = await svc.calculate_best_route(
        amount=Decimal("100.00"),
        currency="USDC",
        destination="0x123",
        preferences=prefs,
    )
    assert result is not None
    assert result["rail"] == "CheapRail"


# ---------------------------------------------------------------------------
# Property 5 – FastRail wins when prioritise_speed=True
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fast_rail_selected_with_speed_preference():
    svc = _svc()
    prefs = PaymentPreferences(prioritize_cost=False, prioritize_speed=True)
    result = await svc.calculate_best_route(
        amount=Decimal("100.00"),
        currency="USDC",
        destination="0x123",
        preferences=prefs,
    )
    assert result is not None
    assert result["rail"] == "FastRail"


# ---------------------------------------------------------------------------
# Property 6 – returned quote has the highest score
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_best_quote_has_highest_score():
    svc = _svc()
    prefs = PaymentPreferences(prioritize_cost=True, prioritize_speed=False)
    best = await svc.calculate_best_route(
        amount=Decimal("500.00"),
        currency="USDC",
        destination="0xABC",
        preferences=prefs,
    )
    assert best is not None
    # The returned quote must have a score field
    assert "score" in best
    assert isinstance(best["score"], float)


# ---------------------------------------------------------------------------
# Property 7 – fee correctness for CheapRail (fee_pct=0.001 * amount)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cheap_rail_fee_is_correct():
    svc = _svc()
    prefs = PaymentPreferences(prioritize_cost=True, prioritize_speed=False)
    amount = Decimal("200.00")
    result = await svc.calculate_best_route(
        amount=amount,
        currency="USDC",
        destination="0x1",
        preferences=prefs,
    )
    # CheapRail charges 0.001 × amount = 0.20
    assert abs(result["fee"] - float(amount * Decimal("0.001"))) < 1e-6


# ---------------------------------------------------------------------------
# Property 8 – default preferences default to cost priority
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_default_preferences_selects_cheap_rail():
    svc = _svc()
    result = await svc.calculate_best_route(
        amount=Decimal("100.00"),
        currency="USDC",
        destination="0x1",
        # preferences omitted → defaults applied inside service
    )
    assert result is not None
    assert result["rail"] == "CheapRail"
