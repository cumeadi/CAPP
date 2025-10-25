"""
Input validation middleware and utilities for CAPP

This module provides comprehensive input validation to prevent
injection attacks, malformed requests, and other security threats.
"""

import re
from typing import Optional
import structlog
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger(__name__)

# Maximum request body size (10MB)
MAX_REQUEST_SIZE = 10 * 1024 * 1024

# Allowed content types
ALLOWED_CONTENT_TYPES = [
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
]

# Patterns for common injection attacks
SQL_INJECTION_PATTERN = re.compile(
    r"(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\b--\b|\b;\b)",
    re.IGNORECASE
)

XSS_PATTERN = re.compile(
    r"(<script|javascript:|onerror=|onload=|<iframe|<object|<embed)",
    re.IGNORECASE
)

PATH_TRAVERSAL_PATTERN = re.compile(
    r"(\.\./|\.\.\\|%2e%2e|%252e%252e)",
    re.IGNORECASE
)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for validating incoming requests

    Checks for:
    - Request size limits
    - Content type validation
    - Basic injection attack patterns
    - Path traversal attempts
    """

    async def dispatch(self, request: Request, call_next):
        """
        Validate request before processing

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from next handler

        Raises:
            HTTPException: If validation fails
        """
        # Skip validation for certain paths
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health"]:
            return await call_next(request)

        try:
            # Validate request size
            if "content-length" in request.headers:
                content_length = int(request.headers["content-length"])
                if content_length > MAX_REQUEST_SIZE:
                    logger.warning(
                        "Request too large",
                        size=content_length,
                        max_size=MAX_REQUEST_SIZE,
                        path=request.url.path
                    )
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request too large. Maximum size is {MAX_REQUEST_SIZE} bytes"
                    )

            # Validate content type for POST/PUT/PATCH requests
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("content-type", "").split(";")[0].strip()
                if content_type and content_type not in ALLOWED_CONTENT_TYPES:
                    logger.warning(
                        "Invalid content type",
                        content_type=content_type,
                        path=request.url.path
                    )
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail=f"Content type '{content_type}' not supported"
                    )

            # Validate URL path for traversal attempts
            if PATH_TRAVERSAL_PATTERN.search(str(request.url.path)):
                logger.warning(
                    "Path traversal attempt detected",
                    path=request.url.path,
                    client=request.client.host if request.client else "unknown"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid path"
                )

            # Validate query parameters for injection attempts
            for key, value in request.query_params.items():
                if isinstance(value, str):
                    if SQL_INJECTION_PATTERN.search(value):
                        logger.warning(
                            "Potential SQL injection in query param",
                            param=key,
                            path=request.url.path
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid query parameter"
                        )

                    if XSS_PATTERN.search(value):
                        logger.warning(
                            "Potential XSS in query param",
                            param=key,
                            path=request.url.path
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid query parameter"
                        )

            # Process request
            response = await call_next(request)
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Request validation error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request validation failed"
            )


def validate_no_sql_injection(value: str) -> str:
    """
    Validate that a string doesn't contain SQL injection patterns

    Args:
        value: String to validate

    Returns:
        Original value if safe

    Raises:
        ValueError: If potential SQL injection detected
    """
    if SQL_INJECTION_PATTERN.search(value):
        raise ValueError("Potential SQL injection detected")
    return value


def validate_no_xss(value: str) -> str:
    """
    Validate that a string doesn't contain XSS patterns

    Args:
        value: String to validate

    Returns:
        Original value if safe

    Raises:
        ValueError: If potential XSS detected
    """
    if XSS_PATTERN.search(value):
        raise ValueError("Potential XSS attack detected")
    return value


def validate_safe_filename(filename: str) -> str:
    """
    Validate that a filename is safe (no path traversal)

    Args:
        filename: Filename to validate

    Returns:
        Original filename if safe

    Raises:
        ValueError: If filename contains path traversal patterns
    """
    if PATH_TRAVERSAL_PATTERN.search(filename):
        raise ValueError("Invalid filename - path traversal detected")

    # Also check for null bytes
    if "\x00" in filename:
        raise ValueError("Invalid filename - null byte detected")

    return filename


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize a string for safe usage

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Raises:
        ValueError: If string is too long
    """
    if len(value) > max_length:
        raise ValueError(f"String too long (max {max_length} characters)")

    # Remove null bytes
    value = value.replace("\x00", "")

    # Remove control characters except newlines and tabs
    value = "".join(char for char in value if char.isprintable() or char in "\n\r\t")

    return value.strip()


def validate_email_format(email: str) -> bool:
    """
    Validate email format

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    email_pattern = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    return bool(email_pattern.match(email))


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format (E.164)

    Args:
        phone: Phone number to validate

    Returns:
        True if valid, False otherwise
    """
    phone_pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
    return bool(phone_pattern.match(phone))


def validate_uuid_format(uuid_str: str) -> bool:
    """
    Validate UUID format

    Args:
        uuid_str: UUID string to validate

    Returns:
        True if valid, False otherwise
    """
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_str))
