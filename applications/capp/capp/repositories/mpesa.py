"""
M-Pesa repository for database operations

This module provides the MpesaRepository class for managing M-Pesa
transaction data with full CRUD operations, callback handling, and
transaction lifecycle management.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
import json

import structlog
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import (
    MpesaTransaction,
    MpesaCallback,
    Payment as PaymentModel
)

logger = structlog.get_logger(__name__)


class MpesaRepository:
    """
    Repository for M-Pesa transaction operations

    Provides CRUD operations and specialized queries for M-Pesa
    transaction management, callback processing, and reconciliation.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # =================================================================
    # M-Pesa Transaction CRUD Operations
    # =================================================================

    async def create_transaction(
        self,
        transaction_type: str,
        phone_number: str,
        amount: Decimal,
        payment_id: Optional[UUID] = None,
        checkout_request_id: Optional[str] = None,
        merchant_request_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        account_reference: Optional[str] = None,
        transaction_desc: Optional[str] = None,
        request_payload: Optional[Dict[str, Any]] = None
    ) -> MpesaTransaction:
        """
        Create a new M-Pesa transaction

        Args:
            transaction_type: Type of transaction (stk_push, b2c, c2b, etc.)
            phone_number: Phone number
            amount: Transaction amount
            payment_id: Optional payment ID
            checkout_request_id: M-Pesa checkout request ID
            merchant_request_id: M-Pesa merchant request ID
            conversation_id: M-Pesa conversation ID
            account_reference: Account reference
            transaction_desc: Transaction description
            request_payload: JSON request payload

        Returns:
            Created M-Pesa transaction
        """
        transaction = MpesaTransaction(
            payment_id=payment_id,
            transaction_type=transaction_type,
            phone_number=phone_number,
            amount=amount,
            checkout_request_id=checkout_request_id,
            merchant_request_id=merchant_request_id,
            conversation_id=conversation_id,
            account_reference=account_reference,
            transaction_desc=transaction_desc,
            request_payload=json.dumps(request_payload) if request_payload else None,
            status="pending"
        )

        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)

        logger.info(
            "M-Pesa transaction created",
            transaction_id=str(transaction.id),
            type=transaction_type,
            checkout_request_id=checkout_request_id
        )

        return transaction

    async def get_by_id(self, transaction_id: UUID) -> Optional[MpesaTransaction]:
        """Get M-Pesa transaction by ID"""
        result = await self.session.execute(
            select(MpesaTransaction).where(MpesaTransaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def get_by_checkout_request_id(
        self, checkout_request_id: str
    ) -> Optional[MpesaTransaction]:
        """Get M-Pesa transaction by checkout request ID"""
        result = await self.session.execute(
            select(MpesaTransaction).where(
                MpesaTransaction.checkout_request_id == checkout_request_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_merchant_request_id(
        self, merchant_request_id: str
    ) -> Optional[MpesaTransaction]:
        """Get M-Pesa transaction by merchant request ID"""
        result = await self.session.execute(
            select(MpesaTransaction).where(
                MpesaTransaction.merchant_request_id == merchant_request_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_conversation_id(
        self, conversation_id: str
    ) -> Optional[MpesaTransaction]:
        """Get M-Pesa transaction by conversation ID"""
        result = await self.session.execute(
            select(MpesaTransaction).where(
                MpesaTransaction.conversation_id == conversation_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_receipt_number(
        self, receipt_number: str
    ) -> Optional[MpesaTransaction]:
        """Get M-Pesa transaction by M-Pesa receipt number"""
        result = await self.session.execute(
            select(MpesaTransaction).where(
                MpesaTransaction.mpesa_receipt_number == receipt_number
            )
        )
        return result.scalar_one_or_none()

    async def get_by_payment_id(self, payment_id: UUID) -> List[MpesaTransaction]:
        """Get all M-Pesa transactions for a payment"""
        result = await self.session.execute(
            select(MpesaTransaction)
            .where(MpesaTransaction.payment_id == payment_id)
            .order_by(MpesaTransaction.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_transaction(
        self,
        transaction_id: UUID,
        status: Optional[str] = None,
        result_code: Optional[int] = None,
        result_description: Optional[str] = None,
        mpesa_receipt_number: Optional[str] = None,
        transaction_date: Optional[datetime] = None,
        response_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Optional[MpesaTransaction]:
        """
        Update M-Pesa transaction

        Args:
            transaction_id: Transaction ID
            status: New status
            result_code: M-Pesa result code
            result_description: M-Pesa result description
            mpesa_receipt_number: M-Pesa receipt number
            transaction_date: Transaction date
            response_payload: JSON response payload
            error_message: Error message

        Returns:
            Updated transaction or None
        """
        transaction = await self.get_by_id(transaction_id)
        if not transaction:
            return None

        if status is not None:
            transaction.status = status
        if result_code is not None:
            transaction.result_code = result_code
        if result_description is not None:
            transaction.result_description = result_description
        if mpesa_receipt_number is not None:
            transaction.mpesa_receipt_number = mpesa_receipt_number
        if transaction_date is not None:
            transaction.transaction_date = transaction_date
        if response_payload is not None:
            transaction.response_payload = json.dumps(response_payload)
        if error_message is not None:
            transaction.error_message = error_message

        # Update completion status
        if status in ["completed", "failed", "cancelled", "timeout"]:
            transaction.completed_at = datetime.utcnow()

        # Update callback received timestamp if processing
        if status == "processing":
            transaction.callback_received_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(transaction)

        logger.info(
            "M-Pesa transaction updated",
            transaction_id=str(transaction_id),
            status=status,
            result_code=result_code
        )

        return transaction

    async def increment_retry_count(self, transaction_id: UUID) -> Optional[MpesaTransaction]:
        """Increment retry count for a transaction"""
        transaction = await self.get_by_id(transaction_id)
        if not transaction:
            return None

        transaction.retry_count += 1
        transaction.last_retry_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(transaction)

        return transaction

    # =================================================================
    # M-Pesa Callback Operations
    # =================================================================

    async def create_callback(
        self,
        callback_type: str,
        callback_data: Dict[str, Any],
        checkout_request_id: Optional[str] = None,
        merchant_request_id: Optional[str] = None,
        mpesa_transaction_id: Optional[UUID] = None,
        signature: Optional[str] = None,
        callback_metadata: Optional[Dict[str, Any]] = None
    ) -> MpesaCallback:
        """
        Create a new M-Pesa callback record

        Args:
            callback_type: Type of callback
            callback_data: Callback payload
            checkout_request_id: Checkout request ID
            merchant_request_id: Merchant request ID
            mpesa_transaction_id: M-Pesa transaction ID
            signature: Callback signature
            callback_metadata: Additional metadata

        Returns:
            Created callback
        """
        callback = MpesaCallback(
            mpesa_transaction_id=mpesa_transaction_id,
            checkout_request_id=checkout_request_id,
            merchant_request_id=merchant_request_id,
            callback_type=callback_type,
            callback_data=json.dumps(callback_data),
            callback_metadata=json.dumps(callback_metadata) if callback_metadata else None,
            signature=signature,
            signature_verified=False,
            processed=False
        )

        self.session.add(callback)
        await self.session.commit()
        await self.session.refresh(callback)

        logger.info(
            "M-Pesa callback created",
            callback_id=str(callback.id),
            type=callback_type,
            checkout_request_id=checkout_request_id
        )

        return callback

    async def get_callback_by_id(self, callback_id: UUID) -> Optional[MpesaCallback]:
        """Get callback by ID"""
        result = await self.session.execute(
            select(MpesaCallback).where(MpesaCallback.id == callback_id)
        )
        return result.scalar_one_or_none()

    async def get_callbacks_by_transaction(
        self, transaction_id: UUID
    ) -> List[MpesaCallback]:
        """Get all callbacks for a transaction"""
        result = await self.session.execute(
            select(MpesaCallback)
            .where(MpesaCallback.mpesa_transaction_id == transaction_id)
            .order_by(MpesaCallback.received_at.desc())
        )
        return list(result.scalars().all())

    async def mark_callback_processed(
        self,
        callback_id: UUID,
        success: bool = True,
        error: Optional[str] = None
    ) -> Optional[MpesaCallback]:
        """Mark callback as processed"""
        callback = await self.get_callback_by_id(callback_id)
        if not callback:
            return None

        callback.processed = success
        callback.processed_at = datetime.utcnow()
        callback.processing_attempts += 1

        if error:
            callback.processing_error = error

        await self.session.commit()
        await self.session.refresh(callback)

        return callback

    async def verify_callback_signature(
        self, callback_id: UUID, verified: bool
    ) -> Optional[MpesaCallback]:
        """Mark callback signature as verified"""
        callback = await self.get_callback_by_id(callback_id)
        if not callback:
            return None

        callback.signature_verified = verified

        await self.session.commit()
        await self.session.refresh(callback)

        return callback

    # =================================================================
    # Query and Analytics Methods
    # =================================================================

    async def get_pending_transactions(
        self, minutes_old: int = 5
    ) -> List[MpesaTransaction]:
        """
        Get pending transactions older than specified minutes

        Args:
            minutes_old: Minutes since transaction creation

        Returns:
            List of pending transactions
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_old)

        result = await self.session.execute(
            select(MpesaTransaction)
            .where(
                and_(
                    MpesaTransaction.status == "pending",
                    MpesaTransaction.created_at < cutoff_time
                )
            )
            .order_by(MpesaTransaction.created_at)
        )
        return list(result.scalars().all())

    async def get_unprocessed_callbacks(
        self, limit: int = 100
    ) -> List[MpesaCallback]:
        """Get unprocessed callbacks"""
        result = await self.session.execute(
            select(MpesaCallback)
            .where(MpesaCallback.processed == False)
            .order_by(MpesaCallback.received_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_transaction_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get M-Pesa transaction statistics

        Args:
            start_date: Start date for statistics
            end_date: End date for statistics

        Returns:
            Dictionary with statistics
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Total transactions
        total_result = await self.session.execute(
            select(func.count(MpesaTransaction.id))
            .where(
                and_(
                    MpesaTransaction.created_at >= start_date,
                    MpesaTransaction.created_at <= end_date
                )
            )
        )
        total_transactions = total_result.scalar()

        # Status breakdown
        status_result = await self.session.execute(
            select(
                MpesaTransaction.status,
                func.count(MpesaTransaction.id).label("count")
            )
            .where(
                and_(
                    MpesaTransaction.created_at >= start_date,
                    MpesaTransaction.created_at <= end_date
                )
            )
            .group_by(MpesaTransaction.status)
        )
        status_breakdown = {row[0]: row[1] for row in status_result.all()}

        # Total amount
        amount_result = await self.session.execute(
            select(func.sum(MpesaTransaction.amount))
            .where(
                and_(
                    MpesaTransaction.created_at >= start_date,
                    MpesaTransaction.created_at <= end_date,
                    MpesaTransaction.status == "completed"
                )
            )
        )
        total_amount = amount_result.scalar() or Decimal("0")

        # Success rate
        completed_result = await self.session.execute(
            select(func.count(MpesaTransaction.id))
            .where(
                and_(
                    MpesaTransaction.created_at >= start_date,
                    MpesaTransaction.created_at <= end_date,
                    MpesaTransaction.status == "completed"
                )
            )
        )
        completed_count = completed_result.scalar()
        success_rate = (completed_count / total_transactions * 100) if total_transactions > 0 else 0

        return {
            "total_transactions": total_transactions,
            "completed_transactions": completed_count,
            "total_amount": float(total_amount),
            "success_rate": success_rate,
            "status_breakdown": status_breakdown,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

    async def get_transactions_by_phone(
        self,
        phone_number: str,
        limit: int = 50
    ) -> List[MpesaTransaction]:
        """Get transactions by phone number"""
        result = await self.session.execute(
            select(MpesaTransaction)
            .where(MpesaTransaction.phone_number == phone_number)
            .order_by(MpesaTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_failed_transactions(
        self,
        start_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[MpesaTransaction]:
        """Get failed transactions for reconciliation"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)

        result = await self.session.execute(
            select(MpesaTransaction)
            .where(
                and_(
                    MpesaTransaction.status.in_(["failed", "timeout", "cancelled"]),
                    MpesaTransaction.created_at >= start_date
                )
            )
            .order_by(MpesaTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
