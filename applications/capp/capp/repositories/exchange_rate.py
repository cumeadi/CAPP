"""
Exchange rate repository for database operations

This module provides the ExchangeRateRepository class for managing exchange rate data
with full CRUD operations and specialized queries.
"""

from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import ExchangeRate

logger = structlog.get_logger(__name__)


class ExchangeRateRepository:
    """
    Repository for exchange rate operations

    Provides CRUD operations and specialized queries for exchange rate management.
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
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        source: str,
        is_locked: bool = False,
        lock_expires_at: Optional[datetime] = None,
        effective_at: Optional[datetime] = None
    ) -> ExchangeRate:
        """
        Create a new exchange rate record

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate: Exchange rate value
            source: Rate source (forex_api, mmo_provider, manual)
            is_locked: Whether rate is locked
            lock_expires_at: When lock expires
            effective_at: When rate becomes effective

        Returns:
            Created exchange rate model
        """
        exchange_rate = ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            source=source,
            is_locked=is_locked,
            lock_expires_at=lock_expires_at,
            effective_at=effective_at or datetime.utcnow()
        )

        self.session.add(exchange_rate)
        await self.session.commit()
        await self.session.refresh(exchange_rate)

        logger.info(
            "Exchange rate created",
            from_currency=from_currency,
            to_currency=to_currency,
            rate=float(rate),
            source=source
        )
        return exchange_rate

    async def get_by_id(self, rate_id: UUID) -> Optional[ExchangeRate]:
        """
        Get exchange rate by ID

        Args:
            rate_id: Exchange rate UUID

        Returns:
            Exchange rate model or None if not found
        """
        result = await self.session.execute(
            select(ExchangeRate).where(ExchangeRate.id == rate_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_rate(
        self,
        from_currency: str,
        to_currency: str
    ) -> Optional[ExchangeRate]:
        """
        Get latest exchange rate for currency pair

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Latest exchange rate model or None if not found
        """
        result = await self.session.execute(
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.effective_at <= datetime.utcnow()
                )
            )
            .order_by(desc(ExchangeRate.effective_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_rate_at_time(
        self,
        from_currency: str,
        to_currency: str,
        at_time: datetime
    ) -> Optional[ExchangeRate]:
        """
        Get exchange rate at specific time

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            at_time: Time to get rate for

        Returns:
            Exchange rate model or None if not found
        """
        result = await self.session.execute(
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.effective_at <= at_time
                )
            )
            .order_by(desc(ExchangeRate.effective_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_rates_by_currency(
        self,
        from_currency: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ExchangeRate]:
        """
        Get all rates for a source currency

        Args:
            from_currency: Source currency code
            limit: Maximum number of rates
            offset: Number of rates to skip

        Returns:
            List of exchange rate models
        """
        result = await self.session.execute(
            select(ExchangeRate)
            .where(ExchangeRate.from_currency == from_currency)
            .order_by(desc(ExchangeRate.effective_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_rate_history(
        self,
        from_currency: str,
        to_currency: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ExchangeRate]:
        """
        Get exchange rate history for currency pair

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum number of rates

        Returns:
            List of exchange rate models
        """
        query = select(ExchangeRate).where(
            and_(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency
            )
        )

        if start_date:
            query = query.where(ExchangeRate.effective_at >= start_date)
        if end_date:
            query = query.where(ExchangeRate.effective_at <= end_date)

        query = query.order_by(desc(ExchangeRate.effective_at)).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def lock_rate(
        self,
        from_currency: str,
        to_currency: str,
        lock_duration_minutes: int = 15
    ) -> Optional[ExchangeRate]:
        """
        Lock current exchange rate for specified duration

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            lock_duration_minutes: Duration to lock rate

        Returns:
            Locked exchange rate model or None if not found
        """
        # Get latest rate
        latest_rate = await self.get_latest_rate(from_currency, to_currency)
        if not latest_rate:
            return None

        # Create locked rate
        lock_expires_at = datetime.utcnow() + timedelta(minutes=lock_duration_minutes)

        locked_rate = ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=latest_rate.rate,
            source=latest_rate.source,
            is_locked=True,
            lock_expires_at=lock_expires_at,
            effective_at=datetime.utcnow()
        )

        self.session.add(locked_rate)
        await self.session.commit()
        await self.session.refresh(locked_rate)

        logger.info(
            "Exchange rate locked",
            from_currency=from_currency,
            to_currency=to_currency,
            rate=float(locked_rate.rate),
            expires_at=lock_expires_at.isoformat()
        )
        return locked_rate

    async def get_locked_rate(
        self,
        from_currency: str,
        to_currency: str
    ) -> Optional[ExchangeRate]:
        """
        Get currently locked rate if available and not expired

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Locked exchange rate model or None if no valid lock
        """
        result = await self.session.execute(
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.is_locked == True,
                    ExchangeRate.lock_expires_at > datetime.utcnow()
                )
            )
            .order_by(desc(ExchangeRate.effective_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def bulk_create(
        self,
        rates: List[Dict[str, any]],
        source: str
    ) -> List[ExchangeRate]:
        """
        Bulk create exchange rates

        Args:
            rates: List of rate dictionaries with from_currency, to_currency, rate
            source: Rate source

        Returns:
            List of created exchange rate models
        """
        exchange_rates = []
        for rate_data in rates:
            exchange_rate = ExchangeRate(
                from_currency=rate_data['from_currency'],
                to_currency=rate_data['to_currency'],
                rate=rate_data['rate'],
                source=source,
                effective_at=rate_data.get('effective_at', datetime.utcnow())
            )
            exchange_rates.append(exchange_rate)
            self.session.add(exchange_rate)

        await self.session.commit()

        for rate in exchange_rates:
            await self.session.refresh(rate)

        logger.info(
            "Bulk exchange rates created",
            count=len(exchange_rates),
            source=source
        )
        return exchange_rates

    async def delete_old_rates(
        self,
        older_than_days: int = 90
    ) -> int:
        """
        Delete exchange rates older than specified days

        Args:
            older_than_days: Delete rates older than this many days

        Returns:
            Number of rates deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        result = await self.session.execute(
            delete(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.effective_at < cutoff_date,
                    ExchangeRate.is_locked == False
                )
            )
        )
        await self.session.commit()

        deleted_count = result.rowcount
        logger.info(
            "Old exchange rates deleted",
            count=deleted_count,
            older_than_days=older_than_days
        )
        return deleted_count

    async def get_statistics(
        self,
        from_currency: str,
        to_currency: str,
        days: int = 30
    ) -> Dict[str, any]:
        """
        Get exchange rate statistics for currency pair

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            days: Number of days to analyze

        Returns:
            Dictionary with rate statistics
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(
                func.avg(ExchangeRate.rate).label('avg_rate'),
                func.min(ExchangeRate.rate).label('min_rate'),
                func.max(ExchangeRate.rate).label('max_rate'),
                func.count(ExchangeRate.id).label('total_count')
            )
            .where(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.effective_at >= start_date
                )
            )
        )

        stats = result.one()

        return {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "period_days": days,
            "avg_rate": float(stats.avg_rate) if stats.avg_rate else 0,
            "min_rate": float(stats.min_rate) if stats.min_rate else 0,
            "max_rate": float(stats.max_rate) if stats.max_rate else 0,
            "total_count": stats.total_count or 0
        }
