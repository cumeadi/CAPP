"""
Unit tests for ExchangeRateService (applications/capp/capp/services/exchange_rates.py).

Covers:
  - _is_pair_supported (pure function)
  - _get_supported_pairs (pure function)
  - _get_rate_from_african_banks (mock-rate dict lookup)
  - _get_rate_from_fixer_api (returns None)
  - get_exchange_rate (cache hit, unsupported pair, african-bank fallback)
  - convert_amount
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from applications.capp.capp.services.exchange_rates import ExchangeRateService
from applications.capp.capp.models.payments import Currency


# ---------------------------------------------------------------------------
# Fixture – bare instance with injected fake_cache
# ---------------------------------------------------------------------------

@pytest.fixture()
def svc(fake_cache):
    inst = ExchangeRateService.__new__(ExchangeRateService)
    from applications.capp.capp.config.settings import get_settings
    inst.settings = get_settings()
    inst.cache = fake_cache
    inst.cache_ttl = 300
    inst.logger = MagicMock()
    inst.supported_pairs = inst._get_supported_pairs()
    return inst


# ---------------------------------------------------------------------------
# _get_supported_pairs
# ---------------------------------------------------------------------------

class TestGetSupportedPairs:

    def test_returns_dict(self, svc):
        pairs = svc._get_supported_pairs()
        assert isinstance(pairs, dict)
        assert len(pairs) > 0

    def test_usd_has_african_targets(self, svc):
        usd_targets = svc._get_supported_pairs().get("USD", [])
        assert "NGN" in usd_targets
        assert "KES" in usd_targets

    def test_ngn_has_usd(self, svc):
        ngn_targets = svc._get_supported_pairs().get("NGN", [])
        assert "USD" in ngn_targets


# ---------------------------------------------------------------------------
# _is_pair_supported
# ---------------------------------------------------------------------------

class TestIsPairSupported:

    def test_usd_to_ngn_supported(self, svc):
        assert svc._is_pair_supported(Currency.USD, Currency.NGN) is True

    def test_usd_to_kes_supported(self, svc):
        assert svc._is_pair_supported(Currency.USD, Currency.KES) is True

    def test_kes_to_ugx_supported(self, svc):
        assert svc._is_pair_supported(Currency.KES, Currency.UGX) is True

    def test_unsupported_pair_returns_false(self, svc):
        # ETH to NGN - crypto to fiat pair not in supported_pairs
        assert svc._is_pair_supported(Currency.ETH, Currency.NGN) is False


# ---------------------------------------------------------------------------
# _get_rate_from_african_banks
# ---------------------------------------------------------------------------

class TestGetRateFromAfricanBanks:

    @pytest.mark.asyncio
    async def test_known_pair_returns_rate(self, svc):
        rate = await svc._get_rate_from_african_banks(Currency.USD, Currency.NGN)
        assert rate is not None
        assert rate > 0

    @pytest.mark.asyncio
    async def test_usd_to_kes_returns_rate(self, svc):
        rate = await svc._get_rate_from_african_banks(Currency.USD, Currency.KES)
        assert rate == Decimal("150.0")

    @pytest.mark.asyncio
    async def test_unknown_pair_returns_none(self, svc):
        rate = await svc._get_rate_from_african_banks(Currency.GHS, Currency.TZS)
        assert rate is None


# ---------------------------------------------------------------------------
# _get_rate_from_fixer_api (always returns None – stub)
# ---------------------------------------------------------------------------

class TestGetRateFromFixerApi:

    @pytest.mark.asyncio
    async def test_returns_none(self, svc):
        rate = await svc._get_rate_from_fixer_api(Currency.USD, Currency.NGN)
        assert rate is None


# ---------------------------------------------------------------------------
# get_exchange_rate
# ---------------------------------------------------------------------------

class TestGetExchangeRate:

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_rate(self, svc):
        # Pre-populate cache
        await svc.cache.set("exchange_rate:USD:NGN", "755.0")
        rate = await svc.get_exchange_rate(Currency.USD, Currency.NGN)
        assert rate == Decimal("755.0")

    @pytest.mark.asyncio
    async def test_unsupported_pair_returns_none(self, svc):
        # ETH → NGN is not in supported_pairs
        rate = await svc.get_exchange_rate(Currency.ETH, Currency.NGN)
        assert rate is None

    @pytest.mark.asyncio
    async def test_supported_pair_gets_rate_from_sources(self, svc):
        rate = await svc.get_exchange_rate(Currency.USD, Currency.KES)
        # African banks returns 150.0 for USD→KES
        assert rate is not None
        assert rate > 0

    @pytest.mark.asyncio
    async def test_rate_is_cached_after_fetch(self, svc):
        await svc.get_exchange_rate(Currency.USD, Currency.ZAR)
        cached = await svc.cache.get("exchange_rate:USD:ZAR")
        assert cached is not None


# ---------------------------------------------------------------------------
# convert_amount
# ---------------------------------------------------------------------------

class TestConvertAmount:

    @pytest.mark.asyncio
    async def test_converts_correctly(self, svc):
        # Pre-seed cache with a known rate
        await svc.cache.set("exchange_rate:USD:KES", "130.0")
        converted = await svc.convert_amount(Decimal("10.00"), Currency.USD, Currency.KES)
        assert converted == Decimal("1300.00")

    @pytest.mark.asyncio
    async def test_unsupported_pair_returns_none(self, svc):
        result = await svc.convert_amount(Decimal("10.00"), Currency.ETH, Currency.NGN)
        assert result is None

    @pytest.mark.asyncio
    async def test_zero_amount_converts_to_zero(self, svc):
        await svc.cache.set("exchange_rate:USD:KES", "130.0")
        converted = await svc.convert_amount(Decimal("0"), Currency.USD, Currency.KES)
        assert converted == Decimal("0.00")
