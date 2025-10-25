"""
Payment repository for database operations

This module provides the PaymentRepository class for managing payment data
with full CRUD operations and complex queries.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import (
    Payment as PaymentModel,
    User as UserModel,
    PaymentRoute,
    AgentActivity
)

logger = structlog.get_logger(__name__)


class PaymentRepository:
    """
    Repository for payment operations

    Provides CRUD operations and specialized queries for payment management.
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
        reference_id: str,
        sender_id: UUID,
        recipient_id: UUID,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        sender_name: str,
        sender_phone: str,
        sender_country: str,
        recipient_name: str,
        recipient_phone: str,
        recipient_country: str,
        payment_type: str,
        payment_method: str,
        total_cost: Decimal,
        fees: Decimal = Decimal("0"),
        description: Optional[str] = None,
        exchange_rate: Optional[Decimal] = None,
        converted_amount: Optional[Decimal] = None
    ) -> PaymentModel:
        """
        Create a new payment

        Args:
            reference_id: Unique payment reference
            sender_id: Sender user ID
            recipient_id: Recipient user ID
            amount: Payment amount
            from_currency: Source currency code
            to_currency: Destination currency code
            sender_name: Sender name
            sender_phone: Sender phone number
            sender_country: Sender country code
            recipient_name: Recipient name
            recipient_phone: Recipient phone number
            recipient_country: Recipient country code
            payment_type: Type of payment
            payment_method: Payment method
            total_cost: Total cost including fees
            fees: Transaction fees
            description: Optional payment description
            exchange_rate: Optional exchange rate
            converted_amount: Optional converted amount

        Returns:
            Created payment model
        """
        payment = PaymentModel(
            reference_id=reference_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
            sender_name=sender_name,
            sender_phone=sender_phone,
            sender_country=sender_country,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            recipient_country=recipient_country,
            payment_type=payment_type,
            payment_method=payment_method,
            total_cost=total_cost,
            fees=fees,
            description=description,
            exchange_rate=exchange_rate,
            converted_amount=converted_amount,
            status="pending"
        )

        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)

        logger.info(
            "Payment created",
            payment_id=str(payment.id),
            reference=reference_id,
            amount=float(amount),
            currency=from_currency
        )
        return payment

    async def get_by_id(self, payment_id: UUID) -> Optional[PaymentModel]:
        """
        Get payment by ID

        Args:
            payment_id: Payment UUID

        Returns:
            Payment model or None if not found
        """
        result = await self.session.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference_id: str) -> Optional[PaymentModel]:
        """
        Get payment by reference ID

        Args:
            reference_id: Payment reference ID

        Returns:
            Payment model or None if not found
        """
        result = await self.session.execute(
            select(PaymentModel).where(PaymentModel.reference_id == reference_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        payment_id: UUID,
        status: str,
        **kwargs
    ) -> Optional[PaymentModel]:
        """
        Update payment status

        Args:
            payment_id: Payment UUID
            status: New status
            **kwargs: Additional fields to update

        Returns:
            Updated payment model or None if not found
        """
        update_data = {'status': status, 'updated_at': datetime.utcnow()}
        update_data.update(kwargs)

        # Set timestamps based on status
        if status == "processing" and "processed_at" not in kwargs:
            update_data['processed_at'] = datetime.utcnow()
        elif status == "completed" and "completed_at" not in kwargs:
            update_data['completed_at'] = datetime.utcnow()
        elif status == "settled" and "settled_at" not in kwargs:
            update_data['settled_at'] = datetime.utcnow()

        result = await self.session.execute(
            update(PaymentModel)
            .where(PaymentModel.id == payment_id)
            .values(**update_data)
            .returning(PaymentModel)
        )

        await self.session.commit()
        payment = result.scalar_one_or_none()

        if payment:
            logger.info(
                "Payment status updated",
                payment_id=str(payment_id),
                old_status=payment.status if hasattr(payment, 'status') else None,
                new_status=status
            )

        return payment

    async def update(
        self,
        payment_id: UUID,
        **kwargs
    ) -> Optional[PaymentModel]:
        """
        Update payment fields

        Args:
            payment_id: Payment UUID
            **kwargs: Fields to update

        Returns:
            Updated payment model or None if not found
        """
        kwargs['updated_at'] = datetime.utcnow()

        result = await self.session.execute(
            update(PaymentModel)
            .where(PaymentModel.id == payment_id)
            .values(**kwargs)
            .returning(PaymentModel)
        )

        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[PaymentModel]:
        """
        Get payments for a user (sent or received)

        Args:
            user_id: User UUID
            limit: Maximum number of payments
            offset: Number of payments to skip
            status: Optional status filter

        Returns:
            List of payment models
        """
        query = select(PaymentModel).where(
            or_(
                PaymentModel.sender_id == user_id,
                PaymentModel.recipient_id == user_id
            )
        )

        if status:
            query = query.where(PaymentModel.status == status)

        query = query.limit(limit).offset(offset).order_by(PaymentModel.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_sender(
        self,
        sender_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[PaymentModel]:
        """
        Get payments sent by a user

        Args:
            sender_id: Sender user ID
            limit: Maximum number of payments
            offset: Number of payments to skip

        Returns:
            List of payment models
        """
        result = await self.session.execute(
            select(PaymentModel)
            .where(PaymentModel.sender_id == sender_id)
            .limit(limit)
            .offset(offset)
            .order_by(PaymentModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_recipient(
        self,
        recipient_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[PaymentModel]:
        """
        Get payments received by a user

        Args:
            recipient_id: Recipient user ID
            limit: Maximum number of payments
            offset: Number of payments to skip

        Returns:
            List of payment models
        """
        result = await self.session.execute(
            select(PaymentModel)
            .where(PaymentModel.recipient_id == recipient_id)
            .limit(limit)
            .offset(offset)
            .order_by(PaymentModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[PaymentModel]:
        """
        Get payments by status

        Args:
            status: Payment status
            limit: Maximum number of payments
            offset: Number of payments to skip

        Returns:
            List of payment models
        """
        result = await self.session.execute(
            select(PaymentModel)
            .where(PaymentModel.status == status)
            .limit(limit)
            .offset(offset)
            .order_by(PaymentModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_corridor(
        self,
        from_country: str,
        to_country: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[PaymentModel]:
        """
        Get payments for a specific corridor

        Args:
            from_country: Source country code
            to_country: Destination country code
            limit: Maximum number of payments
            offset: Number of payments to skip

        Returns:
            List of payment models
        """
        result = await self.session.execute(
            select(PaymentModel)
            .where(
                and_(
                    PaymentModel.sender_country == from_country,
                    PaymentModel.recipient_country == to_country
                )
            )
            .limit(limit)
            .offset(offset)
            .order_by(PaymentModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_payments(
        self,
        older_than_minutes: Optional[int] = None
    ) -> List[PaymentModel]:
        """
        Get all pending payments

        Args:
            older_than_minutes: Only get payments pending longer than this

        Returns:
            List of pending payment models
        """
        query = select(PaymentModel).where(PaymentModel.status == "pending")

        if older_than_minutes:
            cutoff_time = datetime.utcnow() - timedelta(minutes=older_than_minutes)
            query = query.where(PaymentModel.created_at < cutoff_time)

        query = query.order_by(PaymentModel.created_at.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_status(self, status: str) -> int:
        """
        Count payments by status

        Args:
            status: Payment status

        Returns:
            Number of payments
        """
        result = await self.session.execute(
            select(func.count(PaymentModel.id)).where(PaymentModel.status == status)
        )
        return result.scalar_one()

    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get payment statistics

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with payment statistics
        """
        query = select(PaymentModel)

        if start_date:
            query = query.where(PaymentModel.created_at >= start_date)
        if end_date:
            query = query.where(PaymentModel.created_at <= end_date)

        result = await self.session.execute(query)
        payments = list(result.scalars().all())

        # Calculate statistics
        total_count = len(payments)
        total_amount = sum(float(p.amount) for p in payments)
        total_fees = sum(float(p.fees) for p in payments)

        status_counts = {}
        for payment in payments:
            status_counts[payment.status] = status_counts.get(payment.status, 0) + 1

        return {
            "total_count": total_count,
            "total_amount": total_amount,
            "total_fees": total_fees,
            "average_amount": total_amount / total_count if total_count > 0 else 0,
            "status_counts": status_counts,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        }

    async def delete(self, payment_id: UUID) -> bool:
        """
        Delete payment (soft delete by marking as cancelled)

        Args:
            payment_id: Payment UUID

        Returns:
            True if successful, False otherwise
        """
        result = await self.update_status(payment_id, "cancelled")
        return result is not None

    async def hard_delete(self, payment_id: UUID) -> bool:
        """
        Permanently delete payment from database

        Warning: This operation cannot be undone!

        Args:
            payment_id: Payment UUID

        Returns:
            True if successful, False otherwise
        """
        result = await self.session.execute(
            delete(PaymentModel).where(PaymentModel.id == payment_id)
        )
        await self.session.commit()

        deleted = result.rowcount > 0
        if deleted:
            logger.warning("Payment hard deleted", payment_id=str(payment_id))

        return deleted
