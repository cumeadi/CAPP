"""
User repository for database operations

This module provides the UserRepository class for managing user data
with full CRUD operations and authentication support.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

import structlog
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import User as UserModel
from ..models.user import UserStatus, UserRole

logger = structlog.get_logger(__name__)


class UserRepository:
    """
    Repository for user operations

    Provides CRUD operations and specialized queries for user management.
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
        email: str,
        hashed_password: str,
        full_name: str,
        role: UserRole = UserRole.USER,
        phone_number: Optional[str] = None,
        country: Optional[str] = None
    ) -> UserModel:
        """
        Create a new user

        Args:
            email: User email address
            hashed_password: Hashed password
            full_name: User's full name
            role: User role (default: USER)
            phone_number: Optional phone number
            country: Optional country code

        Returns:
            Created user model

        Raises:
            IntegrityError: If email or phone already exists
        """
        user = UserModel(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role.value,
            phone_number=phone_number,
            country=country,
            status=UserStatus.ACTIVE.value,
            is_active=True
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        logger.info("User created", user_id=str(user.id), email=user.email)
        return user

    async def get_by_id(self, user_id: UUID) -> Optional[UserModel]:
        """
        Get user by ID

        Args:
            user_id: User UUID

        Returns:
            User model or None if not found
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[UserModel]:
        """
        Get user by email

        Args:
            email: User email address

        Returns:
            User model or None if not found
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> Optional[UserModel]:
        """
        Get user by phone number

        Args:
            phone_number: User phone number

        Returns:
            User model or None if not found
        """
        result = await self.session.execute(
            select(UserModel).where(UserModel.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        user_id: UUID,
        **kwargs
    ) -> Optional[UserModel]:
        """
        Update user fields

        Args:
            user_id: User UUID
            **kwargs: Fields to update

        Returns:
            Updated user model or None if not found
        """
        # Add updated_at timestamp
        kwargs['updated_at'] = datetime.utcnow()

        result = await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(**kwargs)
            .returning(UserModel)
        )

        await self.session.commit()
        user = result.scalar_one_or_none()

        if user:
            logger.info("User updated", user_id=str(user_id), fields=list(kwargs.keys()))

        return user

    async def update_password(
        self,
        user_id: UUID,
        hashed_password: str
    ) -> bool:
        """
        Update user password

        Args:
            user_id: User UUID
            hashed_password: New hashed password

        Returns:
            True if successful, False otherwise
        """
        result = await self.update(
            user_id,
            hashed_password=hashed_password
        )
        return result is not None

    async def update_last_login(self, user_id: UUID) -> bool:
        """
        Update user's last login timestamp

        Args:
            user_id: User UUID

        Returns:
            True if successful, False otherwise
        """
        result = await self.update(
            user_id,
            last_login=datetime.utcnow(),
            failed_login_attempts=0  # Reset on successful login
        )
        return result is not None

    async def increment_failed_login(self, user_id: UUID) -> Optional[UserModel]:
        """
        Increment failed login attempts

        Args:
            user_id: User UUID

        Returns:
            Updated user model
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        new_attempts = user.failed_login_attempts + 1

        # Suspend account after 5 failed attempts
        update_data = {
            'failed_login_attempts': new_attempts
        }

        if new_attempts >= 5:
            update_data['status'] = UserStatus.SUSPENDED.value
            logger.warning(
                "User account suspended due to failed login attempts",
                user_id=str(user_id)
            )

        return await self.update(user_id, **update_data)

    async def activate(self, user_id: UUID) -> bool:
        """
        Activate user account

        Args:
            user_id: User UUID

        Returns:
            True if successful, False otherwise
        """
        result = await self.update(
            user_id,
            is_active=True,
            status=UserStatus.ACTIVE.value,
            failed_login_attempts=0
        )
        return result is not None

    async def deactivate(self, user_id: UUID) -> bool:
        """
        Deactivate user account

        Args:
            user_id: User UUID

        Returns:
            True if successful, False otherwise
        """
        result = await self.update(
            user_id,
            is_active=False,
            status=UserStatus.INACTIVE.value
        )
        return result is not None

    async def suspend(self, user_id: UUID) -> bool:
        """
        Suspend user account

        Args:
            user_id: User UUID

        Returns:
            True if successful, False otherwise
        """
        result = await self.update(
            user_id,
            status=UserStatus.SUSPENDED.value
        )
        return result is not None

    async def delete(self, user_id: UUID) -> bool:
        """
        Delete user (soft delete by deactivating)

        Args:
            user_id: User UUID

        Returns:
            True if successful, False otherwise
        """
        return await self.deactivate(user_id)

    async def hard_delete(self, user_id: UUID) -> bool:
        """
        Permanently delete user from database

        Warning: This operation cannot be undone!

        Args:
            user_id: User UUID

        Returns:
            True if successful, False otherwise
        """
        result = await self.session.execute(
            delete(UserModel).where(UserModel.id == user_id)
        )
        await self.session.commit()

        deleted = result.rowcount > 0
        if deleted:
            logger.warning("User hard deleted", user_id=str(user_id))

        return deleted

    async def list_users(
        self,
        limit: int = 50,
        offset: int = 0,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        is_active: Optional[bool] = None
    ) -> List[UserModel]:
        """
        List users with filtering

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            role: Filter by role
            status: Filter by status
            is_active: Filter by active status

        Returns:
            List of user models
        """
        query = select(UserModel)

        # Apply filters
        if role is not None:
            query = query.where(UserModel.role == role.value)
        if status is not None:
            query = query.where(UserModel.status == status.value)
        if is_active is not None:
            query = query.where(UserModel.is_active == is_active)

        # Apply pagination
        query = query.limit(limit).offset(offset).order_by(UserModel.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_users(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """
        Count users with filtering

        Args:
            role: Filter by role
            status: Filter by status
            is_active: Filter by active status

        Returns:
            Number of users matching criteria
        """
        from sqlalchemy import func

        query = select(func.count(UserModel.id))

        # Apply filters
        if role is not None:
            query = query.where(UserModel.role == role.value)
        if status is not None:
            query = query.where(UserModel.status == status.value)
        if is_active is not None:
            query = query.where(UserModel.is_active == is_active)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def update_kyc_status(
        self,
        user_id: UUID,
        kyc_status: str
    ) -> Optional[UserModel]:
        """
        Update user KYC status

        Args:
            user_id: User UUID
            kyc_status: New KYC status (pending, verified, rejected)

        Returns:
            Updated user model or None if not found
        """
        update_data = {'kyc_status': kyc_status}

        if kyc_status == "verified":
            update_data['kyc_verified_at'] = datetime.utcnow()

        return await self.update(user_id, **update_data)

    async def exists_by_email(self, email: str) -> bool:
        """
        Check if user exists by email

        Args:
            email: Email address to check

        Returns:
            True if user exists, False otherwise
        """
        result = await self.session.execute(
            select(UserModel.id).where(UserModel.email == email)
        )
        return result.scalar_one_or_none() is not None

    async def exists_by_phone(self, phone_number: str) -> bool:
        """
        Check if user exists by phone number

        Args:
            phone_number: Phone number to check

        Returns:
            True if user exists, False otherwise
        """
        result = await self.session.execute(
            select(UserModel.id).where(UserModel.phone_number == phone_number)
        )
        return result.scalar_one_or_none() is not None
