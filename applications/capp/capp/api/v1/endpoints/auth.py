"""
Authentication endpoints for CAPP API

This module provides authentication endpoints including login, registration,
token refresh, and password management.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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
from ....models.user import (
    User,
    UserCreate,
    LoginRequest,
    Token,
    RefreshTokenRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    UserInDB,
    UserStatus,
    UserRole,
)
from ....api.dependencies.auth import get_current_active_user

logger = structlog.get_logger(__name__)
settings = get_settings()
security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Mock user database (replace with actual database)
MOCK_USERS_DB: Dict[str, UserInDB] = {}


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserCreate) -> User:
    """
    Register a new user

    Rate limit: 5 requests per minute

    Args:
        request: FastAPI request object
        user_data: User registration data

    Returns:
        Created user object

    Raises:
        HTTPException: If email already exists
    """
    try:
        # Check if user already exists
        existing_user = next(
            (u for u in MOCK_USERS_DB.values() if u.email == user_data.email),
            None
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Create new user
        user_id = uuid4()
        hashed_password = hash_password(user_data.password)

        user_in_db = UserInDB(
            id=user_id,
            email=user_data.email,
            full_name=user_data.full_name,
            phone_number=user_data.phone_number,
            role=user_data.role,
            is_active=user_data.is_active,
            hashed_password=hashed_password,
            status=UserStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Store user (mock - replace with database)
        MOCK_USERS_DB[str(user_id)] = user_in_db

        logger.info(
            "User registered successfully",
            user_id=str(user_id),
            email=user_data.email
        )

        # Return user without sensitive data
        return User(
            id=user_in_db.id,
            email=user_in_db.email,
            full_name=user_in_db.full_name,
            phone_number=user_in_db.phone_number,
            role=user_in_db.role,
            is_active=user_in_db.is_active,
            status=user_in_db.status,
            created_at=user_in_db.created_at,
            updated_at=user_in_db.updated_at,
            last_login=user_in_db.last_login,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, login_data: LoginRequest) -> Token:
    """
    Authenticate user and return JWT tokens

    Rate limit: 10 requests per minute (prevents brute force attacks)

    Args:
        request: FastAPI request object
        login_data: Login credentials

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    try:
        # Find user by email
        user = next(
            (u for u in MOCK_USERS_DB.values() if u.email == login_data.email),
            None
        )

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
            user.failed_login_attempts += 1

            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.status = UserStatus.SUSPENDED
                logger.warning(
                    "User account suspended due to failed login attempts",
                    user_id=str(user.id)
                )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status.value}"
            )

        # Reset failed login attempts
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()

        # Generate tokens
        tokens = create_token_pair(user.id, user.email, user.role)

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
async def refresh_token(
    refresh_data: RefreshTokenRequest
) -> Token:
    """
    Refresh access token using refresh token

    Args:
        refresh_data: Refresh token

    Returns:
        New JWT access token

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Verify refresh token
        token_data = verify_token(refresh_data.refresh_token, token_type="refresh")

        # Verify user still exists and is active
        user = MOCK_USERS_DB.get(str(token_data.user_id))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status.value}"
            )

        # Generate new tokens
        tokens = create_token_pair(user.id, user.email, user.role)

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
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    Change user password

    Args:
        password_data: Old and new password
        current_user: Current authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If old password is incorrect
    """
    try:
        # Get user from database
        user = MOCK_USERS_DB.get(str(current_user.id))

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
        user.hashed_password = hash_password(password_data.new_password)
        user.updated_at = datetime.utcnow()

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
    # Find user by email
    user = next(
        (u for u in MOCK_USERS_DB.values() if u.email == reset_data.email),
        None
    )

    # Always return success to prevent email enumeration
    logger.info(
        "Password reset requested",
        email=reset_data.email,
        user_found=user is not None
    )

    return {
        "message": "If the email exists, a password reset link has been sent"
    }
