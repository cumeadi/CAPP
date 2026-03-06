"""
Integration tests for the complete payment state-machine:
    PENDING → PROCESSING → SETTLING → COMPLETED

and the main failure branches:
    PENDING → FAILED (compliance, liquidity, exchange-rate, MMO, settlement)
    PENDING → COMPLIANCE_REVIEW
"""
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# `capp.*` path is added by tests/conftest.py
from capp.services.payment_orchestration import PaymentOrchestrationService
from capp.models.payments import PaymentStatus, PaymentResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(payment_id: str, status: PaymentStatus = PaymentStatus.PROCESSING) -> PaymentResult:
    return PaymentResult(success=True, payment_id=payment_id, status=status, message="ok")


def _fail(payment_id: str, code: str = "ERR") -> PaymentResult:
    return PaymentResult(
        success=False, payment_id=payment_id,
        status=PaymentStatus.FAILED, message="fail", error_code=code
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def svc(fake_cache, mocker):
    """Return a PaymentOrchestrationService with all I/O mocked."""
    # Patch agent_registry so _initialize_agents does not blow up
    mocker.patch(
        "capp.services.payment_orchestration.agent_registry",
        new=MagicMock(
            register_agent_type=MagicMock(),
            get_agents_by_type=MagicMock(return_value=[]),
        )
    )

    service = PaymentOrchestrationService.__new__(PaymentOrchestrationService)
    from capp.config.settings import get_settings
    service.settings = get_settings()
    service.cache = fake_cache
    service.logger = MagicMock()

    # Stub out sub-services
    service.payment_service = MagicMock()
    service.exchange_rate_service = MagicMock()
    service.compliance_service = MagicMock()
    service.mmo_availability_service = MagicMock()
    service.metrics_collector = MagicMock()
    service.yield_service = MagicMock()

    # Default metric recorder → no-op
    service.metrics_collector.record_payment_metrics = AsyncMock(return_value=None)

    return service


# ---------------------------------------------------------------------------
# Shared compliance stubs (all-clear by default)
# ---------------------------------------------------------------------------

class _OkCompliance:
    is_compliant = True
    risk_score = 0.1
    risk_level = "low"
    violations = []
    required_actions = []
    country_specific_requirements = {}


@pytest.fixture()
def compliance_ok(svc):
    """Wire compliance service to pass all checks."""
    svc.compliance_service.check_kyc_compliance = AsyncMock(return_value=_OkCompliance())
    svc.compliance_service.check_sanctions = AsyncMock(return_value=_OkCompliance())
    svc.compliance_service.check_travel_rule = AsyncMock(return_value=True)
    return svc


# ---------------------------------------------------------------------------
# Happy-path: PENDING → PROCESSING → SETTLING → COMPLETED
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_payment_flow_completed(
    valid_payment_request, compliance_ok, mocker
):
    svc = compliance_ok
    mocker.patch("asyncio.sleep", new=AsyncMock())   # skip network delays

    # Exchange rate available
    svc.exchange_rate_service.get_exchange_rate = AsyncMock(return_value=Decimal("130.0"))

    # Liquidity available
    svc.yield_service.request_liquidity = AsyncMock(return_value=True)

    # MMO available (no selected_route → availability check is skipped)
    svc.mmo_availability_service.is_available = AsyncMock(return_value=True)

    # Route optimisation returns success
    async def fake_optimize(payment):
        return _ok(payment.payment_id, PaymentStatus.PROCESSING)

    svc._optimize_route = fake_optimize

    result = await svc.process_payment_flow(valid_payment_request)

    assert result.success is True
    assert result.status == PaymentStatus.COMPLETED


# ---------------------------------------------------------------------------
# Failure: unsupported corridor → FAILED at creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_fails_unsupported_corridor(valid_payment_request, svc, mocker):
    mocker.patch("asyncio.sleep", new=AsyncMock())

    # Both parties in a corridor we don't support
    req = dict(valid_payment_request)
    req["sender_country"] = "US"
    req["recipient_country"] = "FR"

    result = await svc.process_payment_flow(req)

    assert result.success is False
    assert result.status == PaymentStatus.FAILED


# ---------------------------------------------------------------------------
# Failure: route optimization fails
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_fails_route_optimization(
    valid_payment_request, compliance_ok, mocker
):
    svc = compliance_ok
    mocker.patch("asyncio.sleep", new=AsyncMock())
    svc.yield_service.request_liquidity = AsyncMock(return_value=True)
    svc.exchange_rate_service.get_exchange_rate = AsyncMock(return_value=Decimal("130.0"))

    async def bad_route(payment):
        return _fail(payment.payment_id, "ROUTE_ERR")

    svc._optimize_route = bad_route

    result = await svc.process_payment_flow(valid_payment_request)

    assert result.success is False
    assert result.status == PaymentStatus.FAILED


# ---------------------------------------------------------------------------
# Compliance → COMPLIANCE_REVIEW branch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_paused_compliance_review(valid_payment_request, svc, mocker):
    mocker.patch("asyncio.sleep", new=AsyncMock())

    class _MediumRisk:
        is_compliant = False
        risk_score = 0.6
        risk_level = "medium"
        violations = ["medium_risk_transaction"]
        required_actions = ["manual_review"]
        country_specific_requirements = {}

    svc.compliance_service.check_kyc_compliance = AsyncMock(return_value=_MediumRisk())
    svc.compliance_service.check_sanctions = AsyncMock(return_value=_MediumRisk())
    svc.compliance_service.check_travel_rule = AsyncMock(return_value=True)

    async def ok_route(payment):
        return _ok(payment.payment_id)

    svc._optimize_route = ok_route

    result = await svc.process_payment_flow(valid_payment_request)

    assert result.success is False
    assert result.status == PaymentStatus.COMPLIANCE_REVIEW


# ---------------------------------------------------------------------------
# Failure: compliance sanctions hard-fail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_fails_sanctions(valid_payment_request, svc, mocker):
    mocker.patch("asyncio.sleep", new=AsyncMock())

    class _LowRiskKycOk:
        is_compliant = True
        risk_score = 0.1
        risk_level = "low"
        violations = []
        required_actions = []
        country_specific_requirements = {}

    class _SanctionsHit:
        is_compliant = False
        risk_score = 1.0
        risk_level = "high"
        violations = ["sanctioned_country"]
        required_actions = []
        country_specific_requirements = {}

    svc.compliance_service.check_kyc_compliance = AsyncMock(return_value=_LowRiskKycOk())
    svc.compliance_service.check_sanctions = AsyncMock(return_value=_SanctionsHit())
    svc.compliance_service.check_travel_rule = AsyncMock(return_value=True)

    async def ok_route(payment):
        return _ok(payment.payment_id)

    svc._optimize_route = ok_route

    result = await svc.process_payment_flow(valid_payment_request)

    assert result.success is False
    assert result.status == PaymentStatus.FAILED
    assert result.error_code == "PAYMENT_FAILED"


# ---------------------------------------------------------------------------
# Failure: insufficient liquidity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_fails_liquidity(
    valid_payment_request, compliance_ok, mocker
):
    svc = compliance_ok
    mocker.patch("asyncio.sleep", new=AsyncMock())

    svc.yield_service.request_liquidity = AsyncMock(return_value=False)

    async def ok_route(payment):
        return _ok(payment.payment_id)

    svc._optimize_route = ok_route

    result = await svc.process_payment_flow(valid_payment_request)

    assert result.success is False
    assert result.status == PaymentStatus.FAILED


# ---------------------------------------------------------------------------
# Failure: exchange rate unavailable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_fails_exchange_rate(
    valid_payment_request, compliance_ok, mocker
):
    svc = compliance_ok
    mocker.patch("asyncio.sleep", new=AsyncMock())

    svc.yield_service.request_liquidity = AsyncMock(return_value=True)
    svc.exchange_rate_service.get_exchange_rate = AsyncMock(return_value=None)

    async def ok_route(payment):
        return _ok(payment.payment_id)

    svc._optimize_route = ok_route

    result = await svc.process_payment_flow(valid_payment_request)

    assert result.success is False
    assert result.status == PaymentStatus.FAILED


# ---------------------------------------------------------------------------
# Status: travel-rule missing → COMPLIANCE_REVIEW
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payment_travel_rule_review(valid_payment_request, svc, mocker):
    mocker.patch("asyncio.sleep", new=AsyncMock())

    class _KycOk:
        is_compliant = True
        risk_score = 0.1
        risk_level = "low"
        violations = []
        required_actions = []
        country_specific_requirements = {}

    svc.compliance_service.check_kyc_compliance = AsyncMock(return_value=_KycOk())
    svc.compliance_service.check_sanctions = AsyncMock(return_value=_KycOk())
    svc.compliance_service.check_travel_rule = AsyncMock(return_value=False)  # missing info

    async def ok_route(payment):
        return _ok(payment.payment_id)

    svc._optimize_route = ok_route

    result = await svc.process_payment_flow(valid_payment_request)

    assert result.success is False
    assert result.status == PaymentStatus.COMPLIANCE_REVIEW
