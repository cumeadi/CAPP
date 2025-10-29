"""
Agent activity repository for database operations

This module provides the AgentActivityRepository class for tracking and managing
agent activities with full CRUD operations and specialized queries.
"""

from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, timedelta

import structlog
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AgentActivity

logger = structlog.get_logger(__name__)


class AgentActivityRepository:
    """
    Repository for agent activity operations

    Provides CRUD operations and specialized queries for agent activity tracking.
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
        payment_id: UUID,
        agent_type: str,
        agent_id: str,
        action: str,
        status: str = "pending",
        details: Optional[str] = None
    ) -> AgentActivity:
        """
        Create a new agent activity record

        Args:
            payment_id: Payment UUID
            agent_type: Type of agent (routing, liquidity, compliance, settlement, exchange)
            agent_id: Agent identifier
            action: Action performed
            status: Activity status (pending, success, failed, retry)
            details: Optional JSON details

        Returns:
            Created agent activity model
        """
        activity = AgentActivity(
            payment_id=payment_id,
            agent_type=agent_type,
            agent_id=agent_id,
            action=action,
            status=status,
            details=details,
            started_at=datetime.utcnow()
        )

        self.session.add(activity)
        await self.session.commit()
        await self.session.refresh(activity)

        logger.info(
            "Agent activity created",
            payment_id=str(payment_id),
            agent_type=agent_type,
            action=action,
            status=status
        )
        return activity

    async def get_by_id(self, activity_id: UUID) -> Optional[AgentActivity]:
        """
        Get agent activity by ID

        Args:
            activity_id: Activity UUID

        Returns:
            Agent activity model or None if not found
        """
        result = await self.session.execute(
            select(AgentActivity).where(AgentActivity.id == activity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_payment(
        self,
        payment_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[AgentActivity]:
        """
        Get all activities for a payment

        Args:
            payment_id: Payment UUID
            limit: Maximum number of activities
            offset: Number of activities to skip

        Returns:
            List of agent activity models
        """
        result = await self.session.execute(
            select(AgentActivity)
            .where(AgentActivity.payment_id == payment_id)
            .order_by(AgentActivity.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_agent_type(
        self,
        agent_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[AgentActivity]:
        """
        Get all activities for an agent type

        Args:
            agent_type: Agent type
            limit: Maximum number of activities
            offset: Number of activities to skip

        Returns:
            List of agent activity models
        """
        result = await self.session.execute(
            select(AgentActivity)
            .where(AgentActivity.agent_type == agent_type)
            .order_by(AgentActivity.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[AgentActivity]:
        """
        Get activities by status

        Args:
            status: Activity status
            limit: Maximum number of activities
            offset: Number of activities to skip

        Returns:
            List of agent activity models
        """
        result = await self.session.execute(
            select(AgentActivity)
            .where(AgentActivity.status == status)
            .order_by(AgentActivity.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        activity_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> Optional[AgentActivity]:
        """
        Update agent activity status

        Args:
            activity_id: Activity UUID
            status: New status
            error_message: Optional error message
            processing_time_ms: Optional processing time in milliseconds

        Returns:
            Updated agent activity model or None if not found
        """
        update_data = {
            'status': status,
            'completed_at': datetime.utcnow() if status in ['success', 'failed'] else None
        }

        if error_message:
            update_data['error_message'] = error_message
        if processing_time_ms is not None:
            update_data['processing_time_ms'] = processing_time_ms

        result = await self.session.execute(
            update(AgentActivity)
            .where(AgentActivity.id == activity_id)
            .values(**update_data)
            .returning(AgentActivity)
        )

        await self.session.commit()
        activity = result.scalar_one_or_none()

        if activity:
            logger.info(
                "Agent activity status updated",
                activity_id=str(activity_id),
                new_status=status
            )

        return activity

    async def increment_retry_count(self, activity_id: UUID) -> bool:
        """
        Increment retry count for an activity

        Args:
            activity_id: Activity UUID

        Returns:
            True if successful
        """
        await self.session.execute(
            update(AgentActivity)
            .where(AgentActivity.id == activity_id)
            .values(retry_count=AgentActivity.retry_count + 1)
        )
        await self.session.commit()

        logger.info("Agent activity retry count incremented", activity_id=str(activity_id))
        return True

    async def get_failed_activities(
        self,
        agent_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentActivity]:
        """
        Get failed activities that may need retry

        Args:
            agent_type: Optional filter by agent type
            limit: Maximum number of activities

        Returns:
            List of failed agent activities
        """
        query = select(AgentActivity).where(AgentActivity.status == "failed")

        if agent_type:
            query = query.where(AgentActivity.agent_type == agent_type)

        query = query.order_by(AgentActivity.started_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pending_activities(
        self,
        older_than_minutes: Optional[int] = None,
        limit: int = 100
    ) -> List[AgentActivity]:
        """
        Get pending activities

        Args:
            older_than_minutes: Optional filter for activities older than specified minutes
            limit: Maximum number of activities

        Returns:
            List of pending agent activities
        """
        query = select(AgentActivity).where(AgentActivity.status == "pending")

        if older_than_minutes:
            cutoff_time = datetime.utcnow() - timedelta(minutes=older_than_minutes)
            query = query.where(AgentActivity.started_at < cutoff_time)

        query = query.order_by(AgentActivity.started_at.asc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_agent_performance_metrics(
        self,
        agent_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        Get performance metrics for an agent type

        Args:
            agent_type: Agent type
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with performance metrics
        """
        query = select(AgentActivity).where(AgentActivity.agent_type == agent_type)

        if start_date:
            query = query.where(AgentActivity.started_at >= start_date)
        if end_date:
            query = query.where(AgentActivity.started_at <= end_date)

        result = await self.session.execute(query)
        activities = list(result.scalars().all())

        # Calculate metrics
        total_count = len(activities)
        success_count = sum(1 for a in activities if a.status == "success")
        failed_count = sum(1 for a in activities if a.status == "failed")
        pending_count = sum(1 for a in activities if a.status == "pending")

        # Calculate average processing time
        processing_times = [a.processing_time_ms for a in activities if a.processing_time_ms is not None]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0

        # Calculate success rate
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0

        # Get action distribution
        action_counts = {}
        for activity in activities:
            action_counts[activity.action] = action_counts.get(activity.action, 0) + 1

        return {
            "agent_type": agent_type,
            "total_count": total_count,
            "success_count": success_count,
            "failed_count": failed_count,
            "pending_count": pending_count,
            "success_rate": round(success_rate, 2),
            "avg_processing_time_ms": round(avg_processing_time, 2),
            "action_counts": action_counts,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        }

    async def get_payment_activity_timeline(self, payment_id: UUID) -> List[AgentActivity]:
        """
        Get complete activity timeline for a payment

        Args:
            payment_id: Payment UUID

        Returns:
            List of agent activities in chronological order
        """
        result = await self.session.execute(
            select(AgentActivity)
            .where(AgentActivity.payment_id == payment_id)
            .order_by(AgentActivity.started_at.asc())
        )
        return list(result.scalars().all())

    async def delete_old_activities(
        self,
        older_than_days: int = 90
    ) -> int:
        """
        Delete activities older than specified days

        Args:
            older_than_days: Delete activities older than this many days

        Returns:
            Number of activities deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        result = await self.session.execute(
            delete(AgentActivity)
            .where(
                and_(
                    AgentActivity.started_at < cutoff_date,
                    AgentActivity.status.in_(["success", "failed"])
                )
            )
        )
        await self.session.commit()

        deleted_count = result.rowcount
        logger.info(
            "Old agent activities deleted",
            count=deleted_count,
            older_than_days=older_than_days
        )
        return deleted_count

    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        Get overall agent activity statistics

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with activity statistics
        """
        query = select(AgentActivity)

        if start_date:
            query = query.where(AgentActivity.started_at >= start_date)
        if end_date:
            query = query.where(AgentActivity.started_at <= end_date)

        result = await self.session.execute(query)
        activities = list(result.scalars().all())

        # Calculate statistics
        total_count = len(activities)

        status_counts = {}
        agent_type_counts = {}

        for activity in activities:
            status_counts[activity.status] = status_counts.get(activity.status, 0) + 1
            agent_type_counts[activity.agent_type] = agent_type_counts.get(activity.agent_type, 0) + 1

        # Calculate average retry count
        retry_counts = [a.retry_count for a in activities if a.retry_count > 0]
        avg_retry_count = sum(retry_counts) / len(retry_counts) if retry_counts else 0

        return {
            "total_count": total_count,
            "status_counts": status_counts,
            "agent_type_counts": agent_type_counts,
            "avg_retry_count": round(avg_retry_count, 2),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        }
