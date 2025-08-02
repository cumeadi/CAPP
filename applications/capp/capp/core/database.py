"""
Database layer for CAPP - Core database models and connection management.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Boolean, Text, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID

from .config.settings import get_settings

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


class User(Base):
    """User accounts and KYC information."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    country = Column(String(3), nullable=False, index=True)
    kyc_status = Column(String(50), default="pending", nullable=False)
    kyc_verified_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    payments_sent: Mapped[List["Payment"]] = relationship("Payment", foreign_keys="Payment.sender_id", back_populates="sender")
    payments_received: Mapped[List["Payment"]] = relationship("Payment", foreign_keys="Payment.recipient_id", back_populates="recipient")
    
    __table_args__ = (
        Index("idx_users_country_kyc", "country", "kyc_status"),
        Index("idx_users_created_at", "created_at"),
    )


class Payment(Base):
    """Payment transactions."""
    
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    reference_id = Column(String(255), unique=True, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    from_currency = Column(String(3), nullable=False, index=True)
    to_currency = Column(String(3), nullable=False, index=True)
    exchange_rate = Column(Numeric(15, 6), nullable=True)
    fees = Column(Numeric(15, 2), default=0, nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    
    # User relationships
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Payment details
    sender_name = Column(String(200), nullable=False)
    sender_phone = Column(String(20), nullable=False)
    sender_country = Column(String(3), nullable=False)
    recipient_name = Column(String(200), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    recipient_country = Column(String(3), nullable=False)
    
    # Status and routing
    status = Column(String(50), default="pending", nullable=False, index=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("payment_routes.id"), nullable=True)
    mmo_transaction_id = Column(String(255), nullable=True)
    blockchain_transaction_hash = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    settled_at = Column(DateTime, nullable=True)
    
    # Relationships
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id], back_populates="payments_sent")
    recipient: Mapped["User"] = relationship("User", foreign_keys=[recipient_id], back_populates="payments_received")
    route: Mapped[Optional["PaymentRoute"]] = relationship("PaymentRoute", back_populates="payments")
    agent_activities: Mapped[List["AgentActivity"]] = relationship("AgentActivity", back_populates="payment")
    
    __table_args__ = (
        Index("idx_payments_status_created", "status", "created_at"),
        Index("idx_payments_currencies", "from_currency", "to_currency"),
        Index("idx_payments_sender_country", "sender_country"),
        Index("idx_payments_recipient_country", "recipient_country"),
        CheckConstraint("amount > 0", name="check_positive_amount"),
        CheckConstraint("total_amount > 0", name="check_positive_total"),
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
        CheckConstraint("total_liquidity = available_liquidity + reserved_liquidity", name="check_liquidity_balance"),
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
    user: Mapped["User"] = relationship("User")
    payment: Mapped[Optional["Payment"]] = relationship("Payment")
    
    __table_args__ = (
        Index("idx_compliance_user_type", "user_id", "check_type"),
        Index("idx_compliance_status", "status", "checked_at"),
        Index("idx_compliance_expires", "expires_at"),
    )


# Database session management
async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()


# Repository pattern for data access
class PaymentRepository:
    """Repository for payment operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_payment(self, payment_data: dict) -> Payment:
        """Create a new payment."""
        payment = Payment(**payment_data)
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment
    
    async def get_payment_by_id(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        result = await self.session.execute(
            "SELECT * FROM payments WHERE id = :payment_id",
            {"payment_id": payment_id}
        )
        return result.scalar_one_or_none()
    
    async def get_payment_by_reference(self, reference_id: str) -> Optional[Payment]:
        """Get payment by reference ID."""
        result = await self.session.execute(
            "SELECT * FROM payments WHERE reference_id = :reference_id",
            {"reference_id": reference_id}
        )
        return result.scalar_one_or_none()
    
    async def update_payment_status(self, payment_id: str, status: str, **kwargs) -> Optional[Payment]:
        """Update payment status."""
        payment = await self.get_payment_by_id(payment_id)
        if payment:
            payment.status = status
            payment.updated_at = datetime.utcnow()
            for key, value in kwargs.items():
                if hasattr(payment, key):
                    setattr(payment, key, value)
            await self.session.commit()
            await self.session.refresh(payment)
        return payment
    
    async def get_payments_by_user(self, user_id: str, limit: int = 50) -> List[Payment]:
        """Get payments for a user."""
        result = await self.session.execute(
            """
            SELECT * FROM payments 
            WHERE sender_id = :user_id OR recipient_id = :user_id
            ORDER BY created_at DESC 
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit}
        )
        return result.scalars().all()


class UserRepository:
    """Repository for user operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_user(self, user_data: dict) -> User:
        """Create a new user."""
        user = User(**user_data)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number."""
        result = await self.session.execute(
            "SELECT * FROM users WHERE phone = :phone",
            {"phone": phone}
        )
        return result.scalar_one_or_none()
    
    async def update_kyc_status(self, user_id: str, kyc_status: str) -> Optional[User]:
        """Update user KYC status."""
        result = await self.session.execute(
            """
            UPDATE users 
            SET kyc_status = :kyc_status, kyc_verified_at = :verified_at, updated_at = :updated_at
            WHERE id = :user_id
            RETURNING *
            """,
            {
                "user_id": user_id,
                "kyc_status": kyc_status,
                "verified_at": datetime.utcnow() if kyc_status == "verified" else None,
                "updated_at": datetime.utcnow()
            }
        )
        await self.session.commit()
        return result.scalar_one_or_none()


class LiquidityRepository:
    """Repository for liquidity operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_pool_by_currency(self, currency: str) -> Optional[LiquidityPool]:
        """Get liquidity pool by currency."""
        result = await self.session.execute(
            "SELECT * FROM liquidity_pools WHERE currency = :currency",
            {"currency": currency}
        )
        return result.scalar_one_or_none()
    
    async def reserve_liquidity(self, currency: str, amount: float, payment_id: str, expires_in_minutes: int = 30) -> Optional[LiquidityReservation]:
        """Reserve liquidity for a payment."""
        # Use database transaction to ensure atomicity
        async with self.session.begin():
            # Get pool with lock
            result = await self.session.execute(
                """
                SELECT * FROM liquidity_pools 
                WHERE currency = :currency AND is_active = true
                FOR UPDATE
                """,
                {"currency": currency}
            )
            pool = result.scalar_one_or_none()
            
            if not pool or pool.available_liquidity < amount:
                return None
            
            # Update pool
            pool.available_liquidity -= amount
            pool.reserved_liquidity += amount
            pool.updated_at = datetime.utcnow()
            
            # Create reservation
            reservation = LiquidityReservation(
                pool_id=pool.id,
                payment_id=payment_id,
                amount=amount,
                currency=currency,
                expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes)
            )
            self.session.add(reservation)
            
            await self.session.commit()
            await self.session.refresh(reservation)
            return reservation
    
    async def release_liquidity(self, reservation_id: str) -> bool:
        """Release a liquidity reservation."""
        async with self.session.begin():
            result = await self.session.execute(
                """
                SELECT r.*, p.* FROM liquidity_reservations r
                JOIN liquidity_pools p ON r.pool_id = p.id
                WHERE r.id = :reservation_id AND r.status = 'reserved'
                FOR UPDATE
                """,
                {"reservation_id": reservation_id}
            )
            row = result.fetchone()
            
            if not row:
                return False
            
            # Update pool
            await self.session.execute(
                """
                UPDATE liquidity_pools 
                SET available_liquidity = available_liquidity + :amount,
                    reserved_liquidity = reserved_liquidity - :amount,
                    updated_at = :updated_at
                WHERE id = :pool_id
                """,
                {
                    "amount": row.amount,
                    "pool_id": row.pool_id,
                    "updated_at": datetime.utcnow()
                }
            )
            
            # Update reservation
            await self.session.execute(
                """
                UPDATE liquidity_reservations 
                SET status = 'released', released_at = :released_at
                WHERE id = :reservation_id
                """,
                {
                    "reservation_id": reservation_id,
                    "released_at": datetime.utcnow()
                }
            )
            
            await self.session.commit()
            return True 