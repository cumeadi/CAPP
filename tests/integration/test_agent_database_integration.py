"""
Integration Tests for Agent Database Operations

Tests all agent database integrations including:
- Exchange Rate Agent
- Liquidity Management Agent
- Compliance Agent
- Settlement Agent
- Route Optimization Agent

Prerequisites:
- PostgreSQL running on localhost:5432
- Database 'capp_test' created
- Alembic migrations run: alembic upgrade head

Run with: pytest tests/integration/test_agent_database_integration.py -v
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

from applications.capp.capp.core.database import AsyncSessionLocal, Base, async_engine
from applications.capp.capp.repositories.exchange_rate import ExchangeRateRepository
from applications.capp.capp.repositories.liquidity import (
    LiquidityPoolRepository,
    LiquidityReservationRepository
)
from applications.capp.capp.repositories.compliance import ComplianceRecordRepository
from applications.capp.capp.repositories.agent_activity import AgentActivityRepository
from applications.capp.capp.repositories.payment import PaymentRepository


# Test Fixtures
@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def setup_database():
    """Set up test database"""
    # Create all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Create database session for tests"""
    async with AsyncSessionLocal() as session:
        yield session


# ============================================================================
# Exchange Rate Repository Tests
# ============================================================================

@pytest.mark.asyncio
async def test_exchange_rate_create_and_fetch(db_session):
    """Test creating and fetching exchange rates"""
    repo = ExchangeRateRepository(db_session)

    # Create rate
    rate = await repo.create(
        from_currency="USD",
        to_currency="KES",
        rate=Decimal("150.50"),
        source="exchangerate_api"
    )

    assert rate.id is not None
    assert rate.from_currency == "USD"
    assert rate.to_currency == "KES"
    assert rate.rate == Decimal("150.50")
    assert rate.source == "exchangerate_api"

    # Fetch latest rate
    latest_rate = await repo.get_latest_rate("USD", "KES")
    assert latest_rate is not None
    assert latest_rate.rate == Decimal("150.50")


@pytest.mark.asyncio
async def test_exchange_rate_lock(db_session):
    """Test rate locking for payments"""
    repo = ExchangeRateRepository(db_session)

    # Create a rate first
    await repo.create(
        from_currency="NGN",
        to_currency="GHS",
        rate=Decimal("0.012"),
        source="exchangerate_api"
    )

    # Lock the rate
    locked_rate = await repo.lock_rate("NGN", "GHS", lock_duration_minutes=15)

    assert locked_rate is not None
    assert locked_rate.is_locked is True
    assert locked_rate.lock_expires_at is not None
    assert locked_rate.lock_expires_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_exchange_rate_bulk_create(db_session):
    """Test bulk creation of exchange rates"""
    repo = ExchangeRateRepository(db_session)

    rates_data = [
        {"from_currency": "USD", "to_currency": "NGN", "rate": Decimal("750.0")},
        {"from_currency": "USD", "to_currency": "ZAR", "rate": Decimal("18.5")},
        {"from_currency": "EUR", "to_currency": "KES", "rate": Decimal("165.0")},
    ]

    rates = await repo.bulk_create(rates_data, source="exchangerate_api")

    assert len(rates) == 3
    assert all(r.source == "exchangerate_api" for r in rates)


@pytest.mark.asyncio
async def test_exchange_rate_statistics(db_session):
    """Test exchange rate statistics"""
    repo = ExchangeRateRepository(db_session)

    # Create multiple rates over time
    for i in range(5):
        await repo.create(
            from_currency="KES",
            to_currency="UGX",
            rate=Decimal(f"0.02{i}"),
            source="exchangerate_api"
        )

    # Get statistics
    stats = await repo.get_statistics("KES", "UGX", days=30)

    assert stats["total_count"] == 5
    assert stats["avg_rate"] > 0
    assert stats["min_rate"] > 0
    assert stats["max_rate"] > 0


# ============================================================================
# Liquidity Pool Repository Tests
# ============================================================================

@pytest.mark.asyncio
async def test_liquidity_pool_create(db_session):
    """Test creating liquidity pool"""
    repo = LiquidityPoolRepository(db_session)

    pool = await repo.create(
        currency="KES",
        country="KE",
        total_liquidity=Decimal("1000000.00"),
        min_balance=Decimal("100000.00")
    )

    assert pool.id is not None
    assert pool.currency == "KES"
    assert pool.total_liquidity == Decimal("1000000.00")
    assert pool.available_liquidity == Decimal("1000000.00")
    assert pool.reserved_liquidity == Decimal("0")


@pytest.mark.asyncio
async def test_liquidity_reserve_and_release(db_session):
    """Test reserving and releasing liquidity"""
    pool_repo = LiquidityPoolRepository(db_session)

    # Create pool
    pool = await pool_repo.create(
        currency="NGN",
        country="NG",
        total_liquidity=Decimal("5000000.00")
    )

    # Reserve liquidity
    success = await pool_repo.reserve_liquidity("NGN", Decimal("100000.00"))
    assert success is True

    # Check pool state
    updated_pool = await pool_repo.get_by_currency("NGN")
    assert updated_pool.available_liquidity == Decimal("4900000.00")
    assert updated_pool.reserved_liquidity == Decimal("100000.00")

    # Release liquidity
    success = await pool_repo.release_liquidity("NGN", Decimal("100000.00"))
    assert success is True

    # Check pool state
    updated_pool = await pool_repo.get_by_currency("NGN")
    assert updated_pool.available_liquidity == Decimal("5000000.00")
    assert updated_pool.reserved_liquidity == Decimal("0")


@pytest.mark.asyncio
async def test_liquidity_reservation_lifecycle(db_session):
    """Test complete reservation lifecycle"""
    pool_repo = LiquidityPoolRepository(db_session)
    reservation_repo = LiquidityReservationRepository(db_session)

    # Create pool
    pool = await pool_repo.create(
        currency="ZAR",
        country="ZA",
        total_liquidity=Decimal("2000000.00")
    )

    # Reserve liquidity
    await pool_repo.reserve_liquidity("ZAR", Decimal("50000.00"))

    # Create reservation
    payment_id = uuid4()
    reservation = await reservation_repo.create(
        pool_id=pool.id,
        payment_id=payment_id,
        amount=Decimal("50000.00"),
        currency="ZAR",
        expiry_minutes=15
    )

    assert reservation.status == "reserved"
    assert reservation.expires_at > datetime.now(timezone.utc)

    # Use reservation
    success = await reservation_repo.use_reservation(reservation.id)
    assert success is True

    # Verify pool was decremented
    await pool_repo.use_liquidity("ZAR", Decimal("50000.00"))
    updated_pool = await pool_repo.get_by_currency("ZAR")
    assert updated_pool.total_liquidity == Decimal("1950000.00")


# ============================================================================
# Compliance Record Repository Tests
# ============================================================================

@pytest.mark.asyncio
async def test_compliance_record_create(db_session):
    """Test creating compliance records"""
    repo = ComplianceRecordRepository(db_session)

    user_id = uuid4()

    # Create KYC record
    record = await repo.create(
        user_id=user_id,
        check_type="kyc",
        status="passed",
        risk_score=15
    )

    assert record.id is not None
    assert record.user_id == user_id
    assert record.check_type == "kyc"
    assert record.status == "passed"
    assert record.risk_score == 15


@pytest.mark.asyncio
async def test_compliance_user_compliant_check(db_session):
    """Test checking if user is compliant"""
    repo = ComplianceRecordRepository(db_session)

    user_id = uuid4()

    # Create passing compliance checks
    await repo.create(
        user_id=user_id,
        check_type="kyc",
        status="passed",
        risk_score=10
    )

    await repo.create(
        user_id=user_id,
        check_type="aml",
        status="passed",
        risk_score=20
    )

    # Check compliance
    is_kyc_compliant = await repo.is_user_compliant(user_id, "kyc", max_age_days=30)
    is_aml_compliant = await repo.is_user_compliant(user_id, "aml", max_age_days=30)

    assert is_kyc_compliant is True
    assert is_aml_compliant is True


@pytest.mark.asyncio
async def test_compliance_risk_profile(db_session):
    """Test getting user risk profile"""
    repo = ComplianceRecordRepository(db_session)

    user_id = uuid4()

    # Create multiple compliance checks
    await repo.create(user_id=user_id, check_type="kyc", status="passed", risk_score=15)
    await repo.create(user_id=user_id, check_type="aml", status="passed", risk_score=25)
    await repo.create(user_id=user_id, check_type="sanctions", status="passed", risk_score=10)

    # Get risk profile
    profile = await repo.get_user_risk_profile(user_id)

    assert profile["total_checks"] == 3
    assert profile["risk_level"] in ["low", "medium", "high"]
    assert "kyc" in profile["check_counts"]
    assert "aml" in profile["check_counts"]


@pytest.mark.asyncio
async def test_compliance_high_risk_users(db_session):
    """Test fetching high-risk users"""
    repo = ComplianceRecordRepository(db_session)

    # Create high-risk user
    high_risk_user = uuid4()
    await repo.create(
        user_id=high_risk_user,
        check_type="aml",
        status="manual_review",
        risk_score=85
    )

    # Create low-risk user
    low_risk_user = uuid4()
    await repo.create(
        user_id=low_risk_user,
        check_type="aml",
        status="passed",
        risk_score=15
    )

    # Get high-risk users
    high_risk_records = await repo.get_high_risk_users(risk_threshold=70)

    assert len(high_risk_records) >= 1
    assert any(r.user_id == high_risk_user for r in high_risk_records)


# ============================================================================
# Agent Activity Repository Tests
# ============================================================================

@pytest.mark.asyncio
async def test_agent_activity_create(db_session):
    """Test creating agent activity"""
    repo = AgentActivityRepository(db_session)

    payment_id = uuid4()

    activity = await repo.create(
        payment_id=payment_id,
        agent_type="routing",
        agent_id="route_opt_001",
        action="select_route",
        status="success"
    )

    assert activity.id is not None
    assert activity.payment_id == payment_id
    assert activity.agent_type == "routing"
    assert activity.action == "select_route"


@pytest.mark.asyncio
async def test_agent_activity_performance_metrics(db_session):
    """Test agent performance metrics"""
    repo = AgentActivityRepository(db_session)

    payment_id = uuid4()

    # Create multiple activities
    for i in range(10):
        status = "success" if i < 8 else "failed"
        await repo.create(
            payment_id=uuid4(),
            agent_type="settlement",
            agent_id=f"settlement_{i}",
            action="settle_payment",
            status=status
        )

    # Get performance metrics
    metrics = await repo.get_agent_performance_metrics("settlement")

    assert metrics["total_count"] == 10
    assert metrics["success_count"] == 8
    assert metrics["failed_count"] == 2
    assert metrics["success_rate"] == 80.0


@pytest.mark.asyncio
async def test_agent_activity_payment_timeline(db_session):
    """Test getting payment activity timeline"""
    repo = AgentActivityRepository(db_session)

    payment_id = uuid4()

    # Create activities in order
    await repo.create(
        payment_id=payment_id,
        agent_type="routing",
        agent_id="route_1",
        action="select_route",
        status="success"
    )

    await repo.create(
        payment_id=payment_id,
        agent_type="liquidity",
        agent_id="liq_1",
        action="reserve_liquidity",
        status="success"
    )

    await repo.create(
        payment_id=payment_id,
        agent_type="settlement",
        agent_id="settle_1",
        action="settle_payment",
        status="success"
    )

    # Get timeline
    timeline = await repo.get_payment_activity_timeline(payment_id)

    assert len(timeline) == 3
    assert timeline[0].agent_type == "routing"
    assert timeline[1].agent_type == "liquidity"
    assert timeline[2].agent_type == "settlement"


# ============================================================================
# Cross-Repository Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_complete_payment_flow_database_integration(db_session):
    """Test complete payment flow with all repository interactions"""

    # Create repositories
    exchange_repo = ExchangeRateRepository(db_session)
    liquidity_pool_repo = LiquidityPoolRepository(db_session)
    liquidity_res_repo = LiquidityReservationRepository(db_session)
    compliance_repo = ComplianceRecordRepository(db_session)
    activity_repo = AgentActivityRepository(db_session)

    # IDs
    payment_id = uuid4()
    user_id = uuid4()

    # 1. Route Optimization - Get exchange rate
    rate = await exchange_repo.create(
        from_currency="KES",
        to_currency="UGX",
        rate=Decimal("0.025"),
        source="exchangerate_api"
    )

    await activity_repo.create(
        payment_id=payment_id,
        agent_type="routing",
        agent_id="route_kes_ugx",
        action="select_route",
        status="success",
        details='{"exchange_rate": 0.025, "fees": 2.50}'
    )

    # 2. Compliance - Run checks
    await compliance_repo.create(
        user_id=user_id,
        payment_id=payment_id,
        check_type="kyc",
        status="passed",
        risk_score=15
    )

    await compliance_repo.create(
        user_id=user_id,
        payment_id=payment_id,
        check_type="aml",
        status="passed",
        risk_score=20
    )

    await activity_repo.create(
        payment_id=payment_id,
        agent_type="compliance",
        agent_id="comp_001",
        action="validate_compliance",
        status="success"
    )

    # 3. Liquidity - Reserve
    pool = await liquidity_pool_repo.create(
        currency="UGX",
        country="UG",
        total_liquidity=Decimal("1000000.00")
    )

    await liquidity_pool_repo.reserve_liquidity("UGX", Decimal("5000.00"))

    reservation = await liquidity_res_repo.create(
        pool_id=pool.id,
        payment_id=payment_id,
        amount=Decimal("5000.00"),
        currency="UGX"
    )

    await activity_repo.create(
        payment_id=payment_id,
        agent_type="liquidity",
        agent_id=str(reservation.id),
        action="reserve_liquidity",
        status="success"
    )

    # 4. Settlement - Complete
    await liquidity_res_repo.use_reservation(reservation.id)
    await liquidity_pool_repo.use_liquidity("UGX", Decimal("5000.00"))

    await activity_repo.create(
        payment_id=payment_id,
        agent_type="settlement",
        agent_id="settle_001",
        action="settle_payment",
        status="success",
        details='{"tx_hash": "0x123abc", "gas_used": 50000}'
    )

    # Verify complete timeline
    timeline = await activity_repo.get_payment_activity_timeline(payment_id)

    assert len(timeline) == 4
    assert timeline[0].agent_type == "routing"
    assert timeline[1].agent_type == "compliance"
    assert timeline[2].agent_type == "liquidity"
    assert timeline[3].agent_type == "settlement"
    assert all(a.status == "success" for a in timeline)

    # Verify compliance
    is_compliant = await compliance_repo.is_user_compliant(user_id, "kyc")
    assert is_compliant is True

    # Verify liquidity pool state
    updated_pool = await liquidity_pool_repo.get_by_currency("UGX")
    assert updated_pool.total_liquidity == Decimal("995000.00")
    assert updated_pool.reserved_liquidity == Decimal("0")


if __name__ == "__main__":
    print("Run with: pytest tests/integration/test_agent_database_integration.py -v")
