"""
Database layer for CAPP - Core database models and connection management.

This module provides SQLAlchemy models, database session management,
and repository pattern for data access.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, BigInteger, Numeric, DateTime, Boolean, Text,
    ForeignKey, Index, UniqueConstraint, CheckConstraint, select
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID
import structlog

from ..config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    future=True
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


class User(Base):
    """
    User accounts with authentication and KYC information.

    Combines authentication features from Phase 1 with payment user data.
    """

    __tablename__ = "users"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=True, index=True)

    # Authentication (Phase 1)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)  # admin, user, operator, agent, readonly
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, inactive, suspended, pending
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # User profile
    full_name = Column(String(200), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    country = Column(String(3), nullable=True, index=True)

    # KYC information
    kyc_status = Column(String(50), default="pending", nullable=False)  # pending, verified, rejected
    kyc_verified_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    payments_sent: Mapped[List["Payment"]] = relationship(
        "Payment",
        foreign_keys="Payment.sender_id",
        back_populates="sender",
        lazy="selectin"
    )
    payments_received: Mapped[List["Payment"]] = relationship(
        "Payment",
        foreign_keys="Payment.recipient_id",
        back_populates="recipient",
        lazy="selectin"
    )
    compliance_records: Mapped[List["ComplianceRecord"]] = relationship(
        "ComplianceRecord",
        back_populates="user",
        lazy="selectin"
    )

    __table_args__ = (
        Index("idx_users_country_kyc", "country", "kyc_status"),
        Index("idx_users_created_at", "created_at"),
        Index("idx_users_role_status", "role", "status"),
    )


class Payment(Base):
    """Payment transactions."""

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    reference_id = Column(String(255), unique=True, nullable=False, index=True)

    # Payment amounts
    amount = Column(Numeric(15, 2), nullable=False)
    from_currency = Column(String(3), nullable=False, index=True)
    to_currency = Column(String(3), nullable=False, index=True)
    exchange_rate = Column(Numeric(15, 6), nullable=True)
    converted_amount = Column(Numeric(15, 2), nullable=True)
    fees = Column(Numeric(15, 2), default=0, nullable=False)
    total_cost = Column(Numeric(15, 2), nullable=False)

    # User relationships
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Payment details (denormalized for performance)
    sender_name = Column(String(200), nullable=False)
    sender_phone = Column(String(20), nullable=False)
    sender_country = Column(String(3), nullable=False)
    recipient_name = Column(String(200), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    recipient_country = Column(String(3), nullable=False)

    # Payment type and method
    payment_type = Column(String(50), nullable=False)  # personal_remittance, business_payment, etc.
    payment_method = Column(String(50), nullable=False)  # mobile_money, bank_transfer, etc.
    description = Column(Text, nullable=True)

    # Status and routing
    status = Column(String(50), default="pending", nullable=False, index=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("payment_routes.id"), nullable=True)
    mmo_transaction_id = Column(String(255), nullable=True)
    blockchain_tx_hash = Column(String(255), nullable=True, index=True)

    # Rail provider tracking (HIFI Africa Rail, etc.)
    direction = Column(String(10), nullable=True)  # payin, payout
    rail_provider = Column(String(50), nullable=True, index=True)  # hifi_africa, mpesa, etc.
    provider_transaction_id = Column(String(255), nullable=True)  # External rail reference

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    settled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id], back_populates="payments_sent")
    recipient: Mapped["User"] = relationship("User", foreign_keys=[recipient_id], back_populates="payments_received")
    route: Mapped[Optional["PaymentRoute"]] = relationship("PaymentRoute", back_populates="payments")
    agent_activities: Mapped[List["AgentActivity"]] = relationship("AgentActivity", back_populates="payment", lazy="selectin")

    __table_args__ = (
        Index("idx_payments_status_created", "status", "created_at"),
        Index("idx_payments_currencies", "from_currency", "to_currency"),
        Index("idx_payments_sender_country", "sender_country"),
        Index("idx_payments_recipient_country", "recipient_country"),
        Index("idx_payments_sender_id", "sender_id"),
        Index("idx_payments_recipient_id", "recipient_id"),
        CheckConstraint("amount > 0", name="check_positive_amount"),
        CheckConstraint("total_cost > 0", name="check_positive_total"),
    )


class PaymentRoute(Base):
    """Optimized payment routes."""

    __tablename__ = "payment_routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    from_country = Column(String(3), nullable=False, index=True)
    to_country = Column(String(3), nullable=False, index=True)
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)

    # Route details
    mmo_provider = Column(String(50), nullable=False)
    mmo_provider_code = Column(String(20), nullable=False)
    estimated_fees = Column(Numeric(15, 2), nullable=False)
    estimated_duration_minutes = Column(Integer, nullable=False)
    success_rate = Column(Numeric(5, 2), nullable=False)  # Percentage
    max_amount = Column(Numeric(15, 2), nullable=True)
    min_amount = Column(Numeric(15, 2), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="route")

    __table_args__ = (
        UniqueConstraint("from_country", "to_country", "mmo_provider_code", name="uq_route_provider"),
        Index("idx_routes_countries", "from_country", "to_country"),
        Index("idx_routes_active", "is_active", "success_rate"),
    )


class LiquidityPool(Base):
    """Liquidity pools for different currencies."""

    __tablename__ = "liquidity_pools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    currency = Column(String(3), unique=True, nullable=False, index=True)
    country = Column(String(3), nullable=False, index=True)

    # Pool balances
    total_liquidity = Column(Numeric(15, 2), default=0, nullable=False)
    available_liquidity = Column(Numeric(15, 2), default=0, nullable=False)
    reserved_liquidity = Column(Numeric(15, 2), default=0, nullable=False)

    # Pool management
    min_balance = Column(Numeric(15, 2), default=0, nullable=False)
    max_balance = Column(Numeric(15, 2), nullable=True)
    rebalance_threshold = Column(Numeric(5, 2), default=0.1, nullable=False)  # 10%

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_rebalanced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    reservations: Mapped[List["LiquidityReservation"]] = relationship("LiquidityReservation", back_populates="pool")

    __table_args__ = (
        Index("idx_pools_currency_country", "currency", "country"),
        Index("idx_pools_available", "is_active", "available_liquidity"),
        CheckConstraint("total_liquidity >= 0", name="check_positive_total_liquidity"),
        CheckConstraint("available_liquidity >= 0", name="check_positive_available_liquidity"),
        CheckConstraint("reserved_liquidity >= 0", name="check_positive_reserved_liquidity"),
    )


class LiquidityReservation(Base):
    """Liquidity reservations for pending payments."""

    __tablename__ = "liquidity_reservations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("liquidity_pools.id"), nullable=False, index=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False, index=True)

    # Reservation details
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(50), default="reserved", nullable=False)  # reserved, used, released, expired

    # Timestamps
    reserved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)

    # Relationships
    pool: Mapped["LiquidityPool"] = relationship("LiquidityPool", back_populates="reservations")
    payment: Mapped["Payment"] = relationship("Payment")

    __table_args__ = (
        Index("idx_reservations_status_expires", "status", "expires_at"),
        Index("idx_reservations_payment", "payment_id"),
        CheckConstraint("amount > 0", name="check_positive_reservation_amount"),
    )


class AgentActivity(Base):
    """Log of agent activities and decisions."""

    __tablename__ = "agent_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False, index=True)

    # Agent details
    agent_type = Column(String(50), nullable=False, index=True)  # routing, liquidity, compliance, settlement, exchange
    agent_id = Column(String(100), nullable=False)

    # Activity details
    action = Column(String(100), nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # pending, success, failed, retry
    details = Column(Text, nullable=True)  # JSON details
    error_message = Column(Text, nullable=True)

    # Performance metrics
    processing_time_ms = Column(Integer, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    payment: Mapped["Payment"] = relationship("Payment", back_populates="agent_activities")

    __table_args__ = (
        Index("idx_agent_activities_payment_agent", "payment_id", "agent_type"),
        Index("idx_agent_activities_status", "status", "started_at"),
        Index("idx_agent_activities_agent_type", "agent_type", "started_at"),
    )


class ExchangeRate(Base):
    """Exchange rate history and current rates."""

    __tablename__ = "exchange_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    from_currency = Column(String(3), nullable=False, index=True)
    to_currency = Column(String(3), nullable=False, index=True)

    # Rate details
    rate = Column(Numeric(15, 6), nullable=False)
    source = Column(String(50), nullable=False)  # forex_api, mmo_provider, manual
    is_locked = Column(Boolean, default=False, nullable=False)  # For rate locking
    lock_expires_at = Column(DateTime, nullable=True)

    # Timestamps
    effective_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", "effective_at", name="uq_rate_currency_time"),
        Index("idx_exchange_rates_currencies", "from_currency", "to_currency"),
        Index("idx_exchange_rates_effective", "effective_at"),
        CheckConstraint("rate > 0", name="check_positive_rate"),
    )


class ComplianceRecord(Base):
    """Compliance and KYC records."""

    __tablename__ = "compliance_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True, index=True)

    # Compliance details
    check_type = Column(String(50), nullable=False)  # kyc, aml, sanctions, pep
    status = Column(String(50), nullable=False)  # passed, failed, pending, manual_review
    risk_score = Column(Integer, nullable=True)  # 0-100
    details = Column(Text, nullable=True)  # JSON details

    # Timestamps
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="compliance_records")
    payment: Mapped[Optional["Payment"]] = relationship("Payment")

    __table_args__ = (
        Index("idx_compliance_user_type", "user_id", "check_type"),
        Index("idx_compliance_status", "status", "checked_at"),
        Index("idx_compliance_expires", "expires_at"),
    )


class DeveloperAccount(Base):
    """Developer billing accounts — persisted replacement for the in-memory BillingService."""

    __tablename__ = "developer_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(String(20), unique=True, nullable=False, index=True)  # acc_<hex8>
    name = Column(String(255), nullable=False)
    balance_usd = Column(Numeric(15, 2), default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    api_keys: Mapped[List["DeveloperApiKey"]] = relationship(
        "DeveloperApiKey", back_populates="account", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_dev_accounts_active", "is_active", "created_at"),
        CheckConstraint("balance_usd >= 0", name="check_non_negative_balance"),
    )


class DeveloperApiKey(Base):
    """API keys issued to developer accounts."""

    __tablename__ = "developer_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    key = Column(String(64), unique=True, nullable=False, index=True)  # pk_live_<hex16>
    account_id = Column(String(20), ForeignKey("developer_accounts.account_id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    account: Mapped["DeveloperAccount"] = relationship("DeveloperAccount", back_populates="api_keys")

    __table_args__ = (
        Index("idx_dev_api_keys_account_active", "account_id", "is_active"),
    )


class HifiKYCSubmission(Base):
    """HIFI Africa Rail KYC/KYB submission records."""

    __tablename__ = "hifi_kyc_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    submission_type = Column(String(10), nullable=False)  # individual, business

    # Status
    status = Column(String(50), default="pending", nullable=False)  # pending, approved, rejected
    hifi_kyc_reference_id = Column(String(255), nullable=True)

    # Individual KYC fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    id_type = Column(String(50), nullable=True)  # DRIVERS, ID_CARD, PASSPORT, RESIDENCE_PERMIT
    id_number = Column(String(100), nullable=True)
    additional_id_type = Column(String(50), nullable=True)  # Nigeria-specific
    additional_id_number = Column(String(100), nullable=True)  # Nigeria-specific

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province_region = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(3), nullable=True)

    # Business KYB fields
    business_name = Column(String(255), nullable=True)
    tax_identification_number = Column(String(100), nullable=True)

    # Timestamps
    submitted_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("idx_hifi_kyc_user_type", "user_id", "submission_type"),
        Index("idx_hifi_kyc_status", "status"),
    )


class Settlement(Base):
    """
    On-chain settlement record for a completed payment.

    Lifecycle: pending → confirmed (happy path) | failed (on-chain error).
    A payment should have at most one *confirmed* settlement.
    """

    __tablename__ = "settlements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False, index=True)

    # On-chain identity
    blockchain_tx_hash = Column(String(255), unique=True, nullable=False, index=True)
    blockchain_network = Column(String(50), nullable=False)

    # Financial amounts
    settlement_amount = Column(Numeric(15, 2), nullable=False)
    settlement_currency = Column(String(3), nullable=False)

    # Lifecycle — values: pending | confirmed | failed
    status = Column(String(50), default="pending", nullable=False)

    # On-chain confirmation details (populated once confirmed)
    block_number = Column(BigInteger, nullable=True)
    gas_used = Column(BigInteger, nullable=True)

    # Timestamps
    settled_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    payment: Mapped["Payment"] = relationship("Payment")
    refunds: Mapped[List["Refund"]] = relationship("Refund", back_populates="settlement")

    __table_args__ = (
        Index("idx_settlements_payment_id", "payment_id"),
        Index("idx_settlements_status", "status", "settled_at"),
        Index("idx_settlements_network", "blockchain_network"),
        CheckConstraint("settlement_amount > 0", name="check_positive_settlement_amount"),
    )


class Refund(Base):
    """
    Refund (compensating transaction) record for a payment.

    Created by the PaymentWatchdog for stuck payments or by other refund
    triggers (manual request, compliance hold, etc.).  Stores the saga
    rollback outcome so operators can audit which steps were reversed.
    """

    __tablename__ = "refunds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False, index=True)

    # Optional link to the settlement being reversed
    settlement_id = Column(UUID(as_uuid=True), ForeignKey("settlements.id"), nullable=True, index=True)

    # On-chain refund transaction (None until submitted)
    refund_tx_hash = Column(String(255), nullable=True, index=True)

    # Financial amounts
    refund_amount = Column(Numeric(15, 2), nullable=False)
    refund_currency = Column(String(3), nullable=False)

    # Why the refund was initiated
    # Values: PAYMENT_TIMEOUT | SETTLEMENT_FAILED | MANUAL_REQUEST | COMPLIANCE_HOLD
    reason = Column(String(100), nullable=False)

    # Lifecycle — values: pending | processing | completed | failed
    status = Column(String(50), default="pending", nullable=False)

    # Who / what triggered the refund — values: watchdog | user | admin
    initiated_by = Column(String(50), default="watchdog", nullable=False)

    # Saga rollback outcome stored as JSON text arrays
    # Use the helpers below to access as Python lists.
    _rolled_back_steps = Column("rolled_back_steps", Text, nullable=True)
    _failed_rollbacks = Column("failed_rollbacks", Text, nullable=True)

    # Timestamps
    initiated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    payment: Mapped["Payment"] = relationship("Payment")
    settlement: Mapped[Optional["Settlement"]] = relationship(
        "Settlement", back_populates="refunds"
    )

    __table_args__ = (
        Index("idx_refunds_payment_id", "payment_id"),
        Index("idx_refunds_status", "status", "initiated_at"),
        Index("idx_refunds_reason", "reason"),
        Index("idx_refunds_initiated_by", "initiated_by", "initiated_at"),
        CheckConstraint("refund_amount > 0", name="check_positive_refund_amount"),
    )

    # ------------------------------------------------------------------
    # Convenience helpers for the JSON text columns
    # ------------------------------------------------------------------

    @property
    def rolled_back_steps(self) -> List[str]:
        """Return the list of successfully rolled-back step IDs."""
        if self._rolled_back_steps is None:
            return []
        try:
            return json.loads(self._rolled_back_steps)
        except (json.JSONDecodeError, TypeError):
            return []

    @rolled_back_steps.setter
    def rolled_back_steps(self, value: List[str]) -> None:
        self._rolled_back_steps = json.dumps(value) if value is not None else None

    @property
    def failed_rollbacks(self) -> List[str]:
        """Return the list of step IDs whose rollback failed."""
        if self._failed_rollbacks is None:
            return []
        try:
            return json.loads(self._failed_rollbacks)
        except (json.JSONDecodeError, TypeError):
            return []

    @failed_rollbacks.setter
    def failed_rollbacks(self, value: List[str]) -> None:
        self._failed_rollbacks = json.dumps(value) if value is not None else None


# Database session management
async def get_db() -> AsyncSession:
    """
    Get database session.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    logger.info("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        # We don't raise here to allow the app to start even if DB is down/unavailable
        # Subsequent DB operations will fail, but the API will be up.


async def close_db():
    """Close database connections."""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("Database connections closed")


async def check_db_connection() -> bool:
    """
    Check if database connection is healthy.

    Returns:
        bool: True if connection is healthy
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(1))
            return True
    except Exception as e:
        logger.error("Database connection check failed", error=str(e))
        return False
