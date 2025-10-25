"""
Authentication endpoints for CAPP API

This module provides authentication endpoints including login, registration,
token refresh, and password management with database integration.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ....config.settings import get_settings
from ....core.auth import (
    hash_password,
    verify_password,
    create_token_pair,
    verify_token,
    InvalidTokenError,
    TokenExpiredError,
)
from ....core.rate_limit import limiter
from ....core.database import get_db
from ....repositories.user import UserRepository
from ....models.user import (
    User,
    UserCreate,
    LoginRequest,
    Token,
    RefreshTokenRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    UserRole,
    UserStatus,
)
from ....api.dependencies.auth import get_current_active_user

logger = structlog.get_logger(__name__)
settings = get_settings()
security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Register a new user

    Rate limit: 5 requests per minute

    Args:
        request: FastAPI request object
        user_data: User registration data
        db: Database session

    Returns:
        Created user object

    Raises:
        HTTPException: If email already exists or validation fails
    """
    try:
        repo = UserRepository(db)

        # Check if user already exists
        existing_user = await repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Check phone number if provided
        if user_data.phone_number:
            existing_phone = await repo.get_by_phone(user_data.phone_number)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Phone number already registered"
                )

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Create user in database
        user_model = await repo.create(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            phone_number=user_data.phone_number,
            role=user_data.role
        )

        logger.info(
            "User registered successfully",
            user_id=str(user_model.id),
            email=user_data.email
        )

        # Return user without sensitive data
        return User(
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

    except HTTPException:
        raise
    except IntegrityError as e:
        logger.error("Database integrity error during registration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or phone already exists"
        )
    except Exception as e:
        logger.error("Registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Authenticate user and return JWT tokens

    Rate limit: 10 requests per minute (prevents brute force attacks)

    Args:
        request: FastAPI request object
        login_data: Login credentials
        db: Database session

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        repo = UserRepository(db)

        # Find user by email
        user = await repo.get_by_email(login_data.email)

        if not user:
            logger.warning(
                "Login attempt with non-existent email",
                email=login_data.email
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            logger.warning(
                "Failed login attempt - incorrect password",
                user_id=str(user.id),
                email=user.email
            )

            # Increment failed login attempts
            await repo.increment_failed_login(user.id)

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if user.status != UserStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status}"
            )

        # Update last login
        await repo.update_last_login(user.id)

        # Generate tokens
        tokens = create_token_pair(
            user.id,
            user.email,
            UserRole(user.role)
        )

        logger.info(
            "User logged in successfully",
            user_id=str(user.id),
            email=user.email
        )

        return Token(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Refresh access token using refresh token

    Args:
        request: FastAPI request object
        refresh_data: Refresh token
        db: Database session

    Returns:
        New JWT access token

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Verify refresh token
        token_data = verify_token(refresh_data.refresh_token, token_type="refresh")

        repo = UserRepository(db)

        # Verify user still exists and is active
        user = await repo.get_by_id(token_data.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if user.status != UserStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status}"
            )

        # Generate new tokens
        tokens = create_token_pair(
            user.id,
            user.email,
            UserRole(user.role)
        )

        logger.info(
            "Token refreshed successfully",
            user_id=str(user.id)
        )

        return Token(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except (TokenExpiredError, InvalidTokenError) as e:
        logger.warning("Invalid refresh token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    Logout user (client should discard tokens)

    Args:
        current_user: Current authenticated user

    Returns:
        Success message

    Note:
        JWT tokens cannot be invalidated server-side without a blacklist.
        Client should discard tokens on logout.
    """
    logger.info(
        "User logged out",
        user_id=str(current_user.id)
    )

    return {"message": "Successfully logged out"}


@router.post("/change-password")
@limiter.limit("5/hour")
async def change_password(
    request: Request,
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Change user password

    Args:
        request: FastAPI request object
        password_data: Old and new password
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If old password is incorrect
    """
    try:
        repo = UserRepository(db)

        # Get user from database
        user = await repo.get_by_id(current_user.id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify old password
        if not verify_password(password_data.old_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password"
            )

        # Hash and update password
        new_hashed_password = hash_password(password_data.new_password)
        await repo.update_password(user.id, new_hashed_password)

        logger.info(
            "Password changed successfully",
            user_id=str(user.id)
        )

        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password change failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user information

    Args:
        current_user: Current authenticated user

    Returns:
        Current user object
    """
    return current_user


@router.post("/password-reset/request")
async def request_password_reset(
    reset_data: PasswordResetRequest
) -> Dict[str, str]:
    """
    Request password reset (sends email with reset link)

    Args:
        reset_data: Email for password reset

    Returns:
        Success message

    Note:
        This is a mock implementation. In production, this would send
        an email with a password reset token.
    """
    logger.info(
        "Password reset requested",
        email=reset_data.email
    )

    # Always return success to prevent email enumeration
    return {
        "message": "If the email exists, a password reset link has been sent"
    }
