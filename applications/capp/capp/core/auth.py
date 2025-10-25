"""
Authentication utilities for CAPP

This module provides utilities for password hashing, JWT token generation,
and token validation for secure authentication.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config.settings import get_settings
from ..models.user import TokenData, UserRole

logger = structlog.get_logger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(Exception):
    """Base authentication error"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials error"""
    pass


class TokenExpiredError(AuthenticationError):
    """Token expired error"""
    pass


class InvalidTokenError(AuthenticationError):
    """Invalid token error"""
    pass


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error("Password verification failed", error=str(e))
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta (default: 7 days)

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)  # Refresh tokens last 7 days

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token to verify
        token_type: Type of token ("access" or "refresh")

    Returns:
        TokenData object with decoded token data

    Raises:
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token is expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != token_type:
            raise InvalidTokenError(f"Invalid token type. Expected {token_type}")

        # Extract user data
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")

        if user_id is None or email is None:
            raise InvalidTokenError("Token missing required claims")

        token_data = TokenData(
            user_id=UUID(user_id),
            email=email,
            role=UserRole(role) if role else UserRole.USER,
            exp=datetime.fromtimestamp(payload.get("exp")) if payload.get("exp") else None
        )

        return token_data

    except jwt.ExpiredSignatureError:
        logger.warning("Token expired", token_type=token_type)
        raise TokenExpiredError("Token has expired")

    except JWTError as e:
        logger.error("JWT validation failed", error=str(e), token_type=token_type)
        raise InvalidTokenError(f"Invalid token: {str(e)}")

    except ValueError as e:
        logger.error("Token data validation failed", error=str(e))
        raise InvalidTokenError(f"Invalid token data: {str(e)}")


def create_token_pair(user_id: UUID, email: str, role: UserRole) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a user

    Args:
        user_id: User ID
        email: User email
        role: User role

    Returns:
        Dictionary containing access_token and refresh_token
    """
    token_data = {
        "sub": str(user_id),
        "email": email,
        "role": role.value
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }


def decode_token_without_verification(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token without verification (for debugging/logging only)

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload or None if invalid

    Warning:
        This should NEVER be used for authentication! Only for debugging.
    """
    try:
        return jwt.decode(
            token,
            options={"verify_signature": False}
        )
    except Exception as e:
        logger.error("Failed to decode token", error=str(e))
        return None
