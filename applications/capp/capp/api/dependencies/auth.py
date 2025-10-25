"""
Authentication dependencies for FastAPI routes

This module provides dependency functions for authenticating and authorizing
users in FastAPI endpoints with database integration.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import verify_token, InvalidTokenError, TokenExpiredError
from ...core.database import get_db
from ...repositories.user import UserRepository
from ...models.user import User, UserRole, UserStatus, TokenData

logger = structlog.get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenData:
    """
    Extract and verify user from JWT token

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        TokenData from verified token

    Raises:
        HTTPException: If token is invalid or missing
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = verify_token(credentials.credentials, token_type="access")
        return token_data

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except InvalidTokenError as e:
        logger.warning("Invalid token attempt", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token_data: TokenData = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from database

    Args:
        token_data: Token data from JWT
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If user not found or inactive
    """
    repo = UserRepository(db)

    # Get user from database
    user_model = await repo.get_by_id(token_data.user_id)

    if user_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Convert database model to Pydantic model
    user = User(
        id=user_model.id,
        email=user_model.email,
        full_name=user_model.full_name,
        phone_number=user_model.phone_number,
        role=UserRole(user_model.role),
        is_active=user_model.is_active,
        status=UserStatus(user_model.status),
        created_at=user_model.created_at,
        updated_at=user_model.updated_at,
        last_login=user_model.last_login,
    )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user

    Args:
        current_user: Current user from token

    Returns:
        User object if active

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active or current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None

    This is useful for endpoints that work with or without authentication.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        token_data = verify_token(credentials.credentials, token_type="access")

        repo = UserRepository(db)
        user_model = await repo.get_by_id(token_data.user_id)

        if user_model is None:
            return None

        # Convert to Pydantic model
        user = User(
            id=user_model.id,
            email=user_model.email,
            full_name=user_model.full_name,
            phone_number=user_model.phone_number,
            role=UserRole(user_model.role),
            is_active=user_model.is_active,
            status=UserStatus(user_model.status),
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
            last_login=user_model.last_login,
        )

        return user

    except (TokenExpiredError, InvalidTokenError):
        return None


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based authorization

    Args:
        *allowed_roles: Roles that are allowed to access the endpoint

    Returns:
        Dependency function that checks user role

    Example:
        @app.get("/admin")
        async def admin_endpoint(
            user: User = Depends(require_role(UserRole.ADMIN))
        ):
            return {"message": "Admin access granted"}
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                "Unauthorized role access attempt",
                user_id=str(current_user.id),
                user_role=current_user.role,
                required_roles=[role.value for role in allowed_roles]
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency for admin-only endpoints

    Args:
        current_user: Current authenticated user

    Returns:
        User object if admin

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "Unauthorized admin access attempt",
            user_id=str(current_user.id),
            user_role=current_user.role
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user
