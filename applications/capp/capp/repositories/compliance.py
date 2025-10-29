"""
Compliance repository for database operations

This module provides the ComplianceRecordRepository class for managing compliance records
with full CRUD operations and specialized queries.
"""

from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, timedelta

import structlog
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import ComplianceRecord

logger = structlog.get_logger(__name__)


class ComplianceRecordRepository:
    """
    Repository for compliance record operations

    Provides CRUD operations and specialized queries for compliance management.
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
        user_id: UUID,
        check_type: str,
        status: str,
        risk_score: Optional[int] = None,
        details: Optional[str] = None,
        payment_id: Optional[UUID] = None,
        expires_at: Optional[datetime] = None
    ) -> ComplianceRecord:
        """
        Create a new compliance record

        Args:
            user_id: User UUID
            check_type: Type of check (kyc, aml, sanctions, pep)
            status: Check status (passed, failed, pending, manual_review)
            risk_score: Risk score (0-100)
            details: JSON details
            payment_id: Optional payment UUID
            expires_at: Optional expiry datetime

        Returns:
            Created compliance record model
        """
        record = ComplianceRecord(
            user_id=user_id,
            payment_id=payment_id,
            check_type=check_type,
            status=status,
            risk_score=risk_score,
            details=details,
            checked_at=datetime.utcnow(),
            expires_at=expires_at
        )

        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)

        logger.info(
            "Compliance record created",
            user_id=str(user_id),
            check_type=check_type,
            status=status,
            risk_score=risk_score
        )
        return record

    async def get_by_id(self, record_id: UUID) -> Optional[ComplianceRecord]:
        """
        Get compliance record by ID

        Args:
            record_id: Record UUID

        Returns:
            Compliance record model or None if not found
        """
        result = await self.session.execute(
            select(ComplianceRecord).where(ComplianceRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID,
        check_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ComplianceRecord]:
        """
        Get compliance records for a user

        Args:
            user_id: User UUID
            check_type: Optional filter by check type
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of compliance record models
        """
        query = select(ComplianceRecord).where(ComplianceRecord.user_id == user_id)

        if check_type:
            query = query.where(ComplianceRecord.check_type == check_type)

        query = query.order_by(ComplianceRecord.checked_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_payment(self, payment_id: UUID) -> List[ComplianceRecord]:
        """
        Get compliance records for a payment

        Args:
            payment_id: Payment UUID

        Returns:
            List of compliance record models
        """
        result = await self.session.execute(
            select(ComplianceRecord)
            .where(ComplianceRecord.payment_id == payment_id)
            .order_by(ComplianceRecord.checked_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest_check(
        self,
        user_id: UUID,
        check_type: str
    ) -> Optional[ComplianceRecord]:
        """
        Get latest compliance check for user and type

        Args:
            user_id: User UUID
            check_type: Type of check

        Returns:
            Latest compliance record model or None if not found
        """
        result = await self.session.execute(
            select(ComplianceRecord)
            .where(
                and_(
                    ComplianceRecord.user_id == user_id,
                    ComplianceRecord.check_type == check_type
                )
            )
            .order_by(ComplianceRecord.checked_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def is_user_compliant(
        self,
        user_id: UUID,
        check_type: str,
        max_age_days: int = 90
    ) -> bool:
        """
        Check if user has valid compliance check

        Args:
            user_id: User UUID
            check_type: Type of check
            max_age_days: Maximum age of check in days

        Returns:
            True if user has valid compliance check
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

        result = await self.session.execute(
            select(ComplianceRecord)
            .where(
                and_(
                    ComplianceRecord.user_id == user_id,
                    ComplianceRecord.check_type == check_type,
                    ComplianceRecord.status == "passed",
                    ComplianceRecord.checked_at >= cutoff_date,
                    or_(
                        ComplianceRecord.expires_at.is_(None),
                        ComplianceRecord.expires_at > datetime.utcnow()
                    )
                )
            )
            .limit(1)
        )

        return result.scalar_one_or_none() is not None

    async def get_pending_reviews(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[ComplianceRecord]:
        """
        Get all compliance records pending manual review

        Args:
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of compliance records pending review
        """
        result = await self.session.execute(
            select(ComplianceRecord)
            .where(ComplianceRecord.status == "manual_review")
            .order_by(ComplianceRecord.checked_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_high_risk_users(
        self,
        risk_threshold: int = 70,
        limit: int = 100
    ) -> List[ComplianceRecord]:
        """
        Get users with high risk scores

        Args:
            risk_threshold: Minimum risk score (0-100)
            limit: Maximum number of records

        Returns:
            List of high-risk compliance records
        """
        result = await self.session.execute(
            select(ComplianceRecord)
            .where(ComplianceRecord.risk_score >= risk_threshold)
            .order_by(ComplianceRecord.risk_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        record_id: UUID,
        status: str,
        details: Optional[str] = None
    ) -> Optional[ComplianceRecord]:
        """
        Update compliance record status

        Args:
            record_id: Record UUID
            status: New status
            details: Optional details

        Returns:
            Updated compliance record model or None if not found
        """
        update_data = {'status': status}
        if details:
            update_data['details'] = details

        result = await self.session.execute(
            update(ComplianceRecord)
            .where(ComplianceRecord.id == record_id)
            .values(**update_data)
            .returning(ComplianceRecord)
        )

        await self.session.commit()
        record = result.scalar_one_or_none()

        if record:
            logger.info(
                "Compliance record status updated",
                record_id=str(record_id),
                new_status=status
            )

        return record

    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        Get compliance statistics

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with compliance statistics
        """
        query = select(ComplianceRecord)

        if start_date:
            query = query.where(ComplianceRecord.checked_at >= start_date)
        if end_date:
            query = query.where(ComplianceRecord.checked_at <= end_date)

        result = await self.session.execute(query)
        records = list(result.scalars().all())

        # Calculate statistics
        total_count = len(records)
        status_counts = {}
        check_type_counts = {}

        for record in records:
            status_counts[record.status] = status_counts.get(record.status, 0) + 1
            check_type_counts[record.check_type] = check_type_counts.get(record.check_type, 0) + 1

        # Calculate average risk score
        risk_scores = [r.risk_score for r in records if r.risk_score is not None]
        avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0

        return {
            "total_count": total_count,
            "status_counts": status_counts,
            "check_type_counts": check_type_counts,
            "avg_risk_score": avg_risk_score,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        }

    async def cleanup_expired_records(self) -> int:
        """
        Delete expired compliance records

        Returns:
            Number of records deleted
        """
        result = await self.session.execute(
            delete(ComplianceRecord)
            .where(
                and_(
                    ComplianceRecord.expires_at.isnot(None),
                    ComplianceRecord.expires_at < datetime.utcnow()
                )
            )
        )
        await self.session.commit()

        deleted_count = result.rowcount
        logger.info("Expired compliance records deleted", count=deleted_count)
        return deleted_count

    async def get_user_risk_profile(self, user_id: UUID) -> Dict[str, any]:
        """
        Get user's overall risk profile based on compliance checks

        Args:
            user_id: User UUID

        Returns:
            Dictionary with risk profile information
        """
        result = await self.session.execute(
            select(ComplianceRecord)
            .where(ComplianceRecord.user_id == user_id)
            .order_by(ComplianceRecord.checked_at.desc())
        )
        records = list(result.scalars().all())

        if not records:
            return {
                "user_id": str(user_id),
                "total_checks": 0,
                "risk_level": "unknown",
                "avg_risk_score": 0
            }

        # Calculate risk profile
        risk_scores = [r.risk_score for r in records if r.risk_score is not None]
        avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0

        # Determine risk level
        if avg_risk_score >= 70:
            risk_level = "high"
        elif avg_risk_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Count checks by type
        check_counts = {}
        for record in records:
            check_counts[record.check_type] = check_counts.get(record.check_type, 0) + 1

        # Get latest status for each check type
        latest_checks = {}
        for check_type in check_counts.keys():
            for record in records:
                if record.check_type == check_type:
                    latest_checks[check_type] = record.status
                    break

        return {
            "user_id": str(user_id),
            "total_checks": len(records),
            "risk_level": risk_level,
            "avg_risk_score": avg_risk_score,
            "check_counts": check_counts,
            "latest_checks": latest_checks
        }
