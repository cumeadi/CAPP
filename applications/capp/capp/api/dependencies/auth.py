"""
Authentication dependencies for FastAPI routes

This module provides dependency functions for authenticating and authorizing
users in FastAPI endpoints.
"""

from typing import Optional, List
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...core.auth import verify_token, InvalidTokenError, TokenExpiredError
from ...models.user import User, UserRole, TokenData, UserStatus

logger = structlog.get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


# In-memory user store (temporary - replace with database)
# This is a mock implementation until the database layer is ready
MOCK_USERS_DB = {}


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
    token_data: TokenData = Depends(get_current_user_from_token)
) -> User:
    """
    Get current authenticated user

    Args:
        token_data: Token data from JWT

    Returns:
        User object

    Raises:
        HTTPException: If user not found or inactive
    """
    # Mock user lookup - replace with database query
    # For now, create a user object from token data
    user = User(
        id=token_data.user_id,
        email=token_data.email,
        full_name=f"User {token_data.email}",
        role=token_data.role,
        is_active=True,
        status=UserStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # TODO: Replace with actual database lookup
    # user = await user_service.get_user_by_id(token_data.user_id)
    # if user is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="User not found"
    #     )

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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None

    This is useful for endpoints that work with or without authentication.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        token_data = verify_token(credentials.credentials, token_type="access")

        # Mock user creation - replace with database lookup
        user = User(
            id=token_data.user_id,
            email=token_data.email,
            full_name=f"User {token_data.email}",
            role=token_data.role,
            is_active=True,
            status=UserStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
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


# Import datetime for mock user creation
from datetime import datetime
