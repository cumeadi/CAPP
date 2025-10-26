"""
Liquidity management repositories for database operations

This module provides repository classes for managing liquidity pools and reservations
with full CRUD operations and specialized queries.
"""

from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import LiquidityPool, LiquidityReservation

logger = structlog.get_logger(__name__)


class LiquidityPoolRepository:
    """
    Repository for liquidity pool operations

    Provides CRUD operations and specialized queries for liquidity pool management.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        currency: str,
        country: str,
        total_liquidity: Decimal = Decimal("0"),
        min_balance: Decimal = Decimal("0"),
        max_balance: Optional[Decimal] = None,
        rebalance_threshold: Decimal = Decimal("0.1")
    ) -> LiquidityPool:
        """
        Create a new liquidity pool

        Args:
            currency: Currency code
            country: Country code
            total_liquidity: Initial total liquidity
            min_balance: Minimum balance threshold
            max_balance: Maximum balance threshold
            rebalance_threshold: Rebalance threshold percentage

        Returns:
            Created liquidity pool model
        """
        pool = LiquidityPool(
            currency=currency,
            country=country,
            total_liquidity=total_liquidity,
            available_liquidity=total_liquidity,
            reserved_liquidity=Decimal("0"),
            min_balance=min_balance,
            max_balance=max_balance,
            rebalance_threshold=rebalance_threshold,
            is_active=True
        )

        self.session.add(pool)
        await self.session.commit()
        await self.session.refresh(pool)

        logger.info(
            "Liquidity pool created",
            currency=currency,
            country=country,
            total_liquidity=float(total_liquidity)
        )
        return pool

    async def get_by_id(self, pool_id: UUID) -> Optional[LiquidityPool]:
        """
        Get liquidity pool by ID

        Args:
            pool_id: Pool UUID

        Returns:
            Liquidity pool model or None if not found
        """
        result = await self.session.execute(
            select(LiquidityPool).where(LiquidityPool.id == pool_id)
        )
        return result.scalar_one_or_none()

    async def get_by_currency(self, currency: str) -> Optional[LiquidityPool]:
        """
        Get liquidity pool by currency

        Args:
            currency: Currency code

        Returns:
            Liquidity pool model or None if not found
        """
        result = await self.session.execute(
            select(LiquidityPool).where(LiquidityPool.currency == currency)
        )
        return result.scalar_one_or_none()

    async def get_all_active(self) -> List[LiquidityPool]:
        """
        Get all active liquidity pools

        Returns:
            List of active liquidity pool models
        """
        result = await self.session.execute(
            select(LiquidityPool)
            .where(LiquidityPool.is_active == True)
            .order_by(LiquidityPool.currency)
        )
        return list(result.scalars().all())

    async def check_availability(
        self,
        currency: str,
        amount: Decimal
    ) -> bool:
        """
        Check if sufficient liquidity is available

        Args:
            currency: Currency code
            amount: Amount needed

        Returns:
            True if sufficient liquidity available
        """
        pool = await self.get_by_currency(currency)
        if not pool:
            return False

        return pool.available_liquidity >= amount and pool.is_active

    async def reserve_liquidity(
        self,
        currency: str,
        amount: Decimal
    ) -> bool:
        """
        Reserve liquidity from pool

        Args:
            currency: Currency code
            amount: Amount to reserve

        Returns:
            True if reservation successful
        """
        pool = await self.get_by_currency(currency)
        if not pool or pool.available_liquidity < amount:
            return False

        await self.session.execute(
            update(LiquidityPool)
            .where(LiquidityPool.currency == currency)
            .values(
                available_liquidity=LiquidityPool.available_liquidity - amount,
                reserved_liquidity=LiquidityPool.reserved_liquidity + amount,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()

        logger.info(
            "Liquidity reserved",
            currency=currency,
            amount=float(amount)
        )
        return True

    async def release_liquidity(
        self,
        currency: str,
        amount: Decimal
    ) -> bool:
        """
        Release reserved liquidity back to pool

        Args:
            currency: Currency code
            amount: Amount to release

        Returns:
            True if release successful
        """
        pool = await self.get_by_currency(currency)
        if not pool:
            return False

        await self.session.execute(
            update(LiquidityPool)
            .where(LiquidityPool.currency == currency)
            .values(
                available_liquidity=LiquidityPool.available_liquidity + amount,
                reserved_liquidity=LiquidityPool.reserved_liquidity - amount,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()

        logger.info(
            "Liquidity released",
            currency=currency,
            amount=float(amount)
        )
        return True

    async def use_liquidity(
        self,
        currency: str,
        amount: Decimal
    ) -> bool:
        """
        Use reserved liquidity (decreases both reserved and total)

        Args:
            currency: Currency code
            amount: Amount to use

        Returns:
            True if use successful
        """
        pool = await self.get_by_currency(currency)
        if not pool or pool.reserved_liquidity < amount:
            return False

        await self.session.execute(
            update(LiquidityPool)
            .where(LiquidityPool.currency == currency)
            .values(
                total_liquidity=LiquidityPool.total_liquidity - amount,
                reserved_liquidity=LiquidityPool.reserved_liquidity - amount,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()

        logger.info(
            "Liquidity used",
            currency=currency,
            amount=float(amount)
        )
        return True

    async def add_liquidity(
        self,
        currency: str,
        amount: Decimal
    ) -> bool:
        """
        Add liquidity to pool

        Args:
            currency: Currency code
            amount: Amount to add

        Returns:
            True if add successful
        """
        pool = await self.get_by_currency(currency)
        if not pool:
            return False

        await self.session.execute(
            update(LiquidityPool)
            .where(LiquidityPool.currency == currency)
            .values(
                total_liquidity=LiquidityPool.total_liquidity + amount,
                available_liquidity=LiquidityPool.available_liquidity + amount,
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()

        logger.info(
            "Liquidity added",
            currency=currency,
            amount=float(amount)
        )
        return True

    async def get_pools_needing_rebalance(self) -> List[LiquidityPool]:
        """
        Get pools that need rebalancing

        Returns:
            List of pools needing rebalance
        """
        result = await self.session.execute(
            select(LiquidityPool)
            .where(
                and_(
                    LiquidityPool.is_active == True,
                    or_(
                        LiquidityPool.available_liquidity < LiquidityPool.min_balance,
                        LiquidityPool.available_liquidity / LiquidityPool.total_liquidity < LiquidityPool.rebalance_threshold
                    )
                )
            )
        )
        return list(result.scalars().all())

    async def mark_rebalanced(self, pool_id: UUID) -> bool:
        """
        Mark pool as rebalanced

        Args:
            pool_id: Pool UUID

        Returns:
            True if successful
        """
        await self.session.execute(
            update(LiquidityPool)
            .where(LiquidityPool.id == pool_id)
            .values(
                last_rebalanced_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        await self.session.commit()
        return True


class LiquidityReservationRepository:
    """
    Repository for liquidity reservation operations

    Provides CRUD operations for managing liquidity reservations.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(
        self,
        pool_id: UUID,
        payment_id: UUID,
        amount: Decimal,
        currency: str,
        expiry_minutes: int = 15
    ) -> LiquidityReservation:
        """
        Create a new liquidity reservation

        Args:
            pool_id: Pool UUID
            payment_id: Payment UUID
            amount: Amount to reserve
            currency: Currency code
            expiry_minutes: Minutes until reservation expires

        Returns:
            Created liquidity reservation model
        """
        reservation = LiquidityReservation(
            pool_id=pool_id,
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            status="reserved",
            reserved_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes)
        )

        self.session.add(reservation)
        await self.session.commit()
        await self.session.refresh(reservation)

        logger.info(
            "Liquidity reservation created",
            payment_id=str(payment_id),
            amount=float(amount),
            currency=currency
        )
        return reservation

    async def get_by_id(self, reservation_id: UUID) -> Optional[LiquidityReservation]:
        """
        Get liquidity reservation by ID

        Args:
            reservation_id: Reservation UUID

        Returns:
            Liquidity reservation model or None if not found
        """
        result = await self.session.execute(
            select(LiquidityReservation).where(LiquidityReservation.id == reservation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_payment(self, payment_id: UUID) -> Optional[LiquidityReservation]:
        """
        Get liquidity reservation by payment ID

        Args:
            payment_id: Payment UUID

        Returns:
            Liquidity reservation model or None if not found
        """
        result = await self.session.execute(
            select(LiquidityReservation)
            .where(LiquidityReservation.payment_id == payment_id)
            .order_by(LiquidityReservation.reserved_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def use_reservation(self, reservation_id: UUID) -> bool:
        """
        Mark reservation as used

        Args:
            reservation_id: Reservation UUID

        Returns:
            True if successful
        """
        await self.session.execute(
            update(LiquidityReservation)
            .where(LiquidityReservation.id == reservation_id)
            .values(
                status="used",
                used_at=datetime.utcnow()
            )
        )
        await self.session.commit()

        logger.info("Liquidity reservation used", reservation_id=str(reservation_id))
        return True

    async def release_reservation(self, reservation_id: UUID) -> bool:
        """
        Release reservation back to pool

        Args:
            reservation_id: Reservation UUID

        Returns:
            True if successful
        """
        await self.session.execute(
            update(LiquidityReservation)
            .where(LiquidityReservation.id == reservation_id)
            .values(
                status="released",
                released_at=datetime.utcnow()
            )
        )
        await self.session.commit()

        logger.info("Liquidity reservation released", reservation_id=str(reservation_id))
        return True

    async def get_expired_reservations(self) -> List[LiquidityReservation]:
        """
        Get all expired reservations that haven't been released

        Returns:
            List of expired reservation models
        """
        result = await self.session.execute(
            select(LiquidityReservation)
            .where(
                and_(
                    LiquidityReservation.status == "reserved",
                    LiquidityReservation.expires_at < datetime.utcnow()
                )
            )
        )
        return list(result.scalars().all())

    async def cleanup_expired_reservations(self) -> int:
        """
        Mark expired reservations as expired

        Returns:
            Number of reservations marked as expired
        """
        result = await self.session.execute(
            update(LiquidityReservation)
            .where(
                and_(
                    LiquidityReservation.status == "reserved",
                    LiquidityReservation.expires_at < datetime.utcnow()
                )
            )
            .values(status="expired", released_at=datetime.utcnow())
        )
        await self.session.commit()

        expired_count = result.rowcount
        logger.info("Expired reservations cleaned up", count=expired_count)
        return expired_count
