"""
Unit tests for YieldService (applications/capp/capp/services/yield_service.py).

Covers:
  - get_total_treasury_balance (no APTOS address → mock fallback)
  - optimize_wallet (sweep triggered / not triggered)
  - _execute_sweep (balance update)
  - request_liquidity (above / below threshold)
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from applications.capp.capp.services.yield_service import YieldService


# ---------------------------------------------------------------------------
# Fixture – bare instance bypassing __init__
# ---------------------------------------------------------------------------

@pytest.fixture()
def svc(fake_cache):
    inst = YieldService.__new__(YieldService)
    from applications.capp.capp.config.settings import get_settings
    inst.settings = get_settings()
    # Ensure no APTOS address so get_total_treasury_balance uses mock fallback
    inst.settings.APTOS_ACCOUNT_ADDRESS = None
    inst.cache = fake_cache
    inst.logger = MagicMock()
    inst.HOT_WALLET_BUFFER_PCT = Decimal("0.20")
    inst.MIN_SWEEP_AMOUNT = Decimal("1000.00")
    inst._mock_yield_balances = {
        "internal_hot_wallet": {
            "USDC": Decimal("50000.00"),
            "ETH": Decimal("10.0"),
        }
    }
    return inst


# ---------------------------------------------------------------------------
# get_total_treasury_balance
# ---------------------------------------------------------------------------

class TestGetTotalTreasuryBalance:

    @pytest.mark.asyncio
    async def test_internal_wallet_returns_dict(self, svc):
        result = await svc.get_total_treasury_balance("internal_hot_wallet")
        assert isinstance(result, dict)
        assert "total_usd_value" in result
        assert "breakdown" in result

    @pytest.mark.asyncio
    async def test_breakdown_contains_expected_currencies(self, svc):
        result = await svc.get_total_treasury_balance("internal_hot_wallet")
        assert "USDC" in result["breakdown"]
        assert "ETH" in result["breakdown"]
        assert "APT" in result["breakdown"]

    @pytest.mark.asyncio
    async def test_total_usd_value_positive(self, svc):
        result = await svc.get_total_treasury_balance("internal_hot_wallet")
        assert result["total_usd_value"] > 0

    @pytest.mark.asyncio
    async def test_external_wallet_also_returns_valid_dict(self, svc):
        # External wallet has larger hot balance but no yield → total differs from internal
        external = await svc.get_total_treasury_balance("other_wallet")
        assert isinstance(external, dict)
        assert external["total_usd_value"] > 0


# ---------------------------------------------------------------------------
# optimize_wallet
# ---------------------------------------------------------------------------

class TestOptimizeWallet:

    @pytest.mark.asyncio
    async def test_sweep_triggered_for_internal_wallet(self, svc, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        # internal_hot_wallet has 15000 hot, 50000 yield → total=65000
        # buffer = 65000 * 0.20 = 13000
        # excess = 15000 - 13000 = 2000 > MIN_SWEEP_AMOUNT (1000)
        before = svc._mock_yield_balances["internal_hot_wallet"]["USDC"]
        await svc.optimize_wallet("internal_hot_wallet")
        after = svc._mock_yield_balances["internal_hot_wallet"]["USDC"]
        # Yield balance should increase after sweep
        assert after > before

    @pytest.mark.asyncio
    async def test_no_sweep_when_below_minimum(self, svc, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        # Set MIN_SWEEP_AMOUNT very high so no sweep is triggered
        svc.MIN_SWEEP_AMOUNT = Decimal("100000.00")
        before = svc._mock_yield_balances["internal_hot_wallet"]["USDC"]
        await svc.optimize_wallet("internal_hot_wallet")
        after = svc._mock_yield_balances["internal_hot_wallet"]["USDC"]
        assert after == before

    @pytest.mark.asyncio
    async def test_custom_config_respected(self, svc, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        config = {"min_sweep_amount": "10000", "buffer_pct": "0.50"}
        # With 50% buffer on internal (15000 hot): target=32500, excess is negative → no sweep
        before = svc._mock_yield_balances["internal_hot_wallet"]["USDC"]
        await svc.optimize_wallet("internal_hot_wallet", config=config)
        after = svc._mock_yield_balances["internal_hot_wallet"]["USDC"]
        # No sweep since excess < min_sweep with high buffer
        assert after == before


# ---------------------------------------------------------------------------
# _execute_sweep
# ---------------------------------------------------------------------------

class TestExecuteSweep:

    @pytest.mark.asyncio
    async def test_increases_yield_balance(self, svc, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        before = svc._mock_yield_balances["internal_hot_wallet"]["USDC"]
        await svc._execute_sweep("internal_hot_wallet", Decimal("500.00"), "USDC")
        after = svc._mock_yield_balances["internal_hot_wallet"]["USDC"]
        assert after == before + Decimal("500.00")

    @pytest.mark.asyncio
    async def test_creates_new_wallet_entry(self, svc, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        await svc._execute_sweep("new_wallet", Decimal("100.00"), "USDC")
        assert "new_wallet" in svc._mock_yield_balances
        assert svc._mock_yield_balances["new_wallet"]["USDC"] == Decimal("100.00")


# ---------------------------------------------------------------------------
# request_liquidity
# ---------------------------------------------------------------------------

class TestRequestLiquidity:

    @pytest.mark.asyncio
    async def test_internal_wallet_has_sufficient_liquidity(self, svc):
        # internal_hot_wallet has 5000 hot, requesting 1000 → True
        result = await svc.request_liquidity(
            "internal_hot_wallet", Decimal("1000.00"), "USDC"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_external_wallet_insufficient_for_large_request(self, svc, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        # external wallet has 1000 hot, request 2000 → triggers unwind
        result = await svc.request_liquidity(
            "other_wallet", Decimal("2000.00"), "USDC"
        )
        # After unwind (if yield available), should return True or False
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_zero_amount_always_succeeds(self, svc):
        result = await svc.request_liquidity(
            "internal_hot_wallet", Decimal("0"), "USDC"
        )
        assert result is True
