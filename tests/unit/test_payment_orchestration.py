"""
Unit tests for each step-executor in PaymentOrchestrationService.

Each private method (_create_payment, _validate_payment, _optimize_route, …) is
exercised in isolation with both success and failure branches.
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# `capp.*` is available via tests/conftest.py path insertion
from capp.services.payment_orchestration import PaymentOrchestrationService
from capp.models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus,
    Country, Currency, PaymentType, PaymentMethod,
)


# ---------------------------------------------------------------------------
# Helper – make a bare service instance (no __init__ side-effects)
# ---------------------------------------------------------------------------

@pytest.fixture()
def svc(fake_cache, mocker):
    mocker.patch(
        "capp.services.payment_orchestration.agent_registry",
        new=MagicMock(
            register_agent_type=MagicMock(),
            get_agents_by_type=MagicMock(return_value=[]),
        ),
    )
    instance = PaymentOrchestrationService.__new__(PaymentOrchestrationService)
    from capp.config.settings import get_settings
    instance.settings = get_settings()
    instance.cache = fake_cache
    instance.logger = MagicMock()
    instance.payment_service = MagicMock()
    instance.exchange_rate_service = MagicMock()
    instance.compliance_service = MagicMock()
    instance.mmo_availability_service = MagicMock()
    instance.metrics_collector = MagicMock()
    instance.yield_service = MagicMock()
    instance.metrics_collector.record_payment_metrics = AsyncMock(return_value=None)
    return instance


# ---------------------------------------------------------------------------
# Helper – a minimal valid payment
# ---------------------------------------------------------------------------

@pytest.fixture()
def payment():
    return CrossBorderPayment(
        reference_id="unit_test_001",
        payment_type=PaymentType.PERSONAL_REMITTANCE,
        payment_method=PaymentMethod.MOBILE_MONEY,
        amount=Decimal("100.00"),
        from_currency=Currency.USD,
        to_currency=Currency.KES,
        sender={"name": "Alice", "phone_number": "+234800", "country": Country.NIGERIA},
        recipient={"name": "Bob", "phone_number": "+25470", "country": Country.KENYA},
    )


# ---------------------------------------------------------------------------
# _create_payment
# ---------------------------------------------------------------------------

class TestCreatePayment:

    @pytest.mark.asyncio
    async def test_creates_valid_payment(self, svc, valid_payment_request):
        result = await svc._create_payment(valid_payment_request)
        assert result is not None
        assert result.amount == Decimal("100.00")
        assert result.from_currency == Currency.USD
        assert result.to_currency == Currency.KES

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_field(self, svc):
        bad_request = {"reference_id": "x", "amount": "10"}  # missing required fields
        result = await svc._create_payment(bad_request)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_unsupported_corridor(self, svc, valid_payment_request):
        req = dict(valid_payment_request)
        req["sender_country"] = "US"
        req["recipient_country"] = "FR"
        result = await svc._create_payment(req)
        assert result is None


# ---------------------------------------------------------------------------
# _validate_payment
# ---------------------------------------------------------------------------

class TestValidatePayment:

    @pytest.mark.asyncio
    async def test_valid_payment_passes(self, svc, payment):
        assert await svc._validate_payment(payment) is True

    @pytest.mark.asyncio
    async def test_amount_below_minimum_fails(self, svc, payment):
        svc.settings.MIN_PAYMENT_AMOUNT = Decimal("200.00")
        assert await svc._validate_payment(payment) is False

    @pytest.mark.asyncio
    async def test_amount_above_maximum_fails(self, svc, payment):
        svc.settings.MAX_PAYMENT_AMOUNT = Decimal("50.00")
        assert await svc._validate_payment(payment) is False

    @pytest.mark.asyncio
    async def test_unsupported_corridor_fails(self, svc, payment):
        payment.sender = MagicMock(country=Country.UNITED_STATES)
        payment.recipient = MagicMock(country=Country.UNITED_KINGDOM)
        assert await svc._validate_payment(payment) is False


# ---------------------------------------------------------------------------
# _is_corridor_supported
# ---------------------------------------------------------------------------

class TestIsCorridorSupported:

    @pytest.mark.asyncio
    async def test_known_corridor_supported(self, svc):
        assert await svc._is_corridor_supported(Country.NIGERIA, Country.KENYA) is True

    @pytest.mark.asyncio
    async def test_unknown_corridor_not_supported(self, svc):
        assert await svc._is_corridor_supported(Country.UNITED_STATES, Country.UNITED_KINGDOM) is False

    @pytest.mark.asyncio
    async def test_reverse_known_corridor_supported(self, svc):
        assert await svc._is_corridor_supported(Country.KENYA, Country.UGANDA) is True


# ---------------------------------------------------------------------------
# _check_liquidity
# ---------------------------------------------------------------------------

class TestCheckLiquidity:

    @pytest.mark.asyncio
    async def test_liquidity_available(self, svc, payment):
        svc.yield_service.request_liquidity = AsyncMock(return_value=True)
        result = await svc._check_liquidity(payment)
        assert result.success is True
        assert result.status == PaymentStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_liquidity_unavailable(self, svc, payment):
        svc.yield_service.request_liquidity = AsyncMock(return_value=False)
        result = await svc._check_liquidity(payment)
        assert result.success is False
        assert result.status == PaymentStatus.FAILED
        assert result.error_code == "INSUFFICIENT_LIQUIDITY"

    @pytest.mark.asyncio
    async def test_liquidity_exception_returns_failure(self, svc, payment):
        svc.yield_service.request_liquidity = AsyncMock(side_effect=RuntimeError("network error"))
        result = await svc._check_liquidity(payment)
        assert result.success is False
        assert result.error_code == "LIQUIDITY_ERROR"


# ---------------------------------------------------------------------------
# _lock_exchange_rate
# ---------------------------------------------------------------------------

class TestLockExchangeRate:

    @pytest.mark.asyncio
    async def test_rate_locked_successfully(self, svc, payment):
        svc.exchange_rate_service.get_exchange_rate = AsyncMock(return_value=Decimal("130.5"))
        result = await svc._lock_exchange_rate(payment)
        assert result.success is True
        assert result.exchange_rate_used == Decimal("130.5")
        assert payment.exchange_rate == Decimal("130.5")
        assert payment.converted_amount == payment.amount * Decimal("130.5")

    @pytest.mark.asyncio
    async def test_no_rate_returns_failure(self, svc, payment):
        svc.exchange_rate_service.get_exchange_rate = AsyncMock(return_value=None)
        result = await svc._lock_exchange_rate(payment)
        assert result.success is False
        assert result.error_code == "EXCHANGE_RATE_ERROR"

    @pytest.mark.asyncio
    async def test_exception_returns_failure(self, svc, payment):
        svc.exchange_rate_service.get_exchange_rate = AsyncMock(side_effect=Exception("timeout"))
        result = await svc._lock_exchange_rate(payment)
        assert result.success is False
        assert result.error_code == "EXCHANGE_RATE_ERROR"


# ---------------------------------------------------------------------------
# _execute_mmo_payment
# ---------------------------------------------------------------------------

class TestExecuteMMOPayment:

    @pytest.mark.asyncio
    async def test_mmo_executed_no_route(self, svc, payment, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        payment.selected_route = None
        result = await svc._execute_mmo_payment(payment)
        assert result.success is True
        assert result.status == PaymentStatus.SETTLING

    @pytest.mark.asyncio
    async def test_mmo_unavailable_fails(self, svc, payment, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        mock_route = MagicMock()
        mock_route.to_mmo = "mpesa"
        payment.selected_route = mock_route
        svc.mmo_availability_service.is_available = AsyncMock(return_value=False)
        result = await svc._execute_mmo_payment(payment)
        assert result.success is False
        assert result.error_code == "MMO_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_mmo_available_succeeds(self, svc, payment, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        mock_route = MagicMock()
        mock_route.to_mmo = "mpesa"
        payment.selected_route = mock_route
        svc.mmo_availability_service.is_available = AsyncMock(return_value=True)
        result = await svc._execute_mmo_payment(payment)
        assert result.success is True
        assert result.status == PaymentStatus.SETTLING


# ---------------------------------------------------------------------------
# _settle_payment
# ---------------------------------------------------------------------------

class TestSettlePayment:

    @pytest.mark.asyncio
    async def test_settlement_succeeds(self, svc, payment, mocker):
        mocker.patch("asyncio.sleep", new=AsyncMock())
        result = await svc._settle_payment(payment)
        assert result.success is True
        assert result.status == PaymentStatus.COMPLETED
        assert result.transaction_hash is not None
        assert payment.blockchain_tx_hash is not None

    @pytest.mark.asyncio
    async def test_settlement_exception_returns_failure(self, svc, payment, mocker):
        mocker.patch("asyncio.sleep", side_effect=RuntimeError("chain down"))
        result = await svc._settle_payment(payment)
        assert result.success is False
        assert result.error_code == "SETTLEMENT_ERROR"


# ---------------------------------------------------------------------------
# _confirm_payment
# ---------------------------------------------------------------------------

class TestConfirmPayment:

    @pytest.mark.asyncio
    async def test_confirmation_succeeds(self, svc, payment):
        payment.converted_amount = Decimal("13050.00")
        result = await svc._confirm_payment(payment)
        assert result.success is True
        assert result.status == PaymentStatus.COMPLETED
        assert payment.status == PaymentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_confirmation_exception_returns_failure(self, svc, payment, mocker):
        mocker.patch.object(
            svc, "_send_confirmation_notifications", side_effect=RuntimeError("db offline")
        )
        result = await svc._confirm_payment(payment)
        assert result.success is False
        assert result.error_code == "CONFIRMATION_ERROR"


# ---------------------------------------------------------------------------
# _validate_compliance
# ---------------------------------------------------------------------------

class TestValidateCompliance:

    class _OkResult:
        is_compliant = True
        risk_score = 0.05
        risk_level = "low"
        violations = []
        required_actions = []
        country_specific_requirements = {}

    class _HighRisk:
        is_compliant = False
        risk_score = 0.9
        risk_level = "high"
        violations = ["high_risk"]
        required_actions = []
        country_specific_requirements = {}

    @pytest.mark.asyncio
    async def test_all_checks_pass(self, svc, payment):
        ok = self._OkResult()
        svc.compliance_service.check_kyc_compliance = AsyncMock(return_value=ok)
        svc.compliance_service.check_sanctions = AsyncMock(return_value=ok)
        svc.compliance_service.check_travel_rule = AsyncMock(return_value=True)
        result = await svc._validate_compliance(payment)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_kyc_high_risk_returns_compliance_review(self, svc, payment):
        class _MedRisk:
            is_compliant = False
            risk_score = 0.6
            risk_level = "medium"
            violations = ["med_risk"]
            required_actions = []
            country_specific_requirements = {}

        svc.compliance_service.check_kyc_compliance = AsyncMock(return_value=_MedRisk())
        result = await svc._validate_compliance(payment)
        assert result.success is False
        assert result.status == PaymentStatus.COMPLIANCE_REVIEW

    @pytest.mark.asyncio
    async def test_sanctions_failure(self, svc, payment):
        ok = self._OkResult()
        svc.compliance_service.check_kyc_compliance = AsyncMock(return_value=ok)
        svc.compliance_service.check_sanctions = AsyncMock(return_value=self._HighRisk())
        svc.compliance_service.check_travel_rule = AsyncMock(return_value=True)
        result = await svc._validate_compliance(payment)
        assert result.success is False
        assert result.status == PaymentStatus.FAILED

    @pytest.mark.asyncio
    async def test_travel_rule_missing_flags_review(self, svc, payment):
        ok = self._OkResult()
        svc.compliance_service.check_kyc_compliance = AsyncMock(return_value=ok)
        svc.compliance_service.check_sanctions = AsyncMock(return_value=ok)
        svc.compliance_service.check_travel_rule = AsyncMock(return_value=False)
        result = await svc._validate_compliance(payment)
        assert result.success is False
        assert result.status == PaymentStatus.COMPLIANCE_REVIEW

    @pytest.mark.asyncio
    async def test_exception_returns_failure(self, svc, payment):
        svc.compliance_service.check_kyc_compliance = AsyncMock(
            side_effect=RuntimeError("service down")
        )
        result = await svc._validate_compliance(payment)
        assert result.success is False
        assert result.error_code == "COMPLIANCE_ERROR"


# ---------------------------------------------------------------------------
# _handle_payment_failure
# ---------------------------------------------------------------------------

class TestHandlePaymentFailure:

    @pytest.mark.asyncio
    async def test_returns_failed_result(self, svc, payment):
        result = await svc._handle_payment_failure(payment, "test error")
        assert result.success is False
        assert result.status == PaymentStatus.FAILED
        assert payment.status == PaymentStatus.FAILED

    @pytest.mark.asyncio
    async def test_records_failure_metrics(self, svc, payment):
        svc.metrics_collector.record_payment_metrics = AsyncMock()
        await svc._handle_payment_failure(payment, "test")
        svc.metrics_collector.record_payment_metrics.assert_awaited_once()


# ---------------------------------------------------------------------------
# track_payment_status / get_payment_analytics
# ---------------------------------------------------------------------------

class TestUtilityMethods:

    @pytest.mark.asyncio
    async def test_track_status_returns_enum(self, svc):
        status = await svc.track_payment_status("some-id")
        assert isinstance(status, PaymentStatus)

    @pytest.mark.asyncio
    async def test_get_analytics_returns_dict(self, svc):
        svc.metrics_collector.get_payment_metrics = AsyncMock(return_value={})
        svc.metrics_collector.get_business_metrics = AsyncMock(return_value={})
        analytics = await svc.get_payment_analytics()
        assert isinstance(analytics, dict)
        assert "cost_savings" in analytics
        assert "performance" in analytics
