"""
Error Handler Middleware for CAPP

Provides centralized error handling for all API endpoints.
"""

from typing import Callable, Any
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

from .exceptions import (
    CAPPException,
    RecordNotFoundException,
    DuplicateRecordException,
    DatabaseConnectionException,
    PaymentNotFoundException,
    InsufficientFundsException,
    InvalidPaymentStatusException,
    NoRoutesAvailableException,
    KYCVerificationException,
    AMLCheckException,
    SanctionsCheckException,
    SuspiciousActivityException,
    InvalidCredentialsException,
    TokenExpiredException,
    InvalidTokenException,
    AuthorizationException,
    ValidationException,
    RateLimitException,
    ConfigurationException,
    MMOIntegrationException,
    BankIntegrationException,
    ExchangeRateException,
)

logger = structlog.get_logger(__name__)


# Exception to HTTP status code mapping
EXCEPTION_STATUS_CODES = {
    # Not Found exceptions
    RecordNotFoundException: status.HTTP_404_NOT_FOUND,
    PaymentNotFoundException: status.HTTP_404_NOT_FOUND,

    # Conflict exceptions
    DuplicateRecordException: status.HTTP_409_CONFLICT,
    InvalidPaymentStatusException: status.HTTP_409_CONFLICT,

    # Bad Request exceptions
    ValidationException: status.HTTP_400_BAD_REQUEST,
    NoRoutesAvailableException: status.HTTP_400_BAD_REQUEST,
    InsufficientFundsException: status.HTTP_400_BAD_REQUEST,

    # Unauthorized exceptions
    InvalidCredentialsException: status.HTTP_401_UNAUTHORIZED,
    TokenExpiredException: status.HTTP_401_UNAUTHORIZED,
    InvalidTokenException: status.HTTP_401_UNAUTHORIZED,

    # Forbidden exceptions
    AuthorizationException: status.HTTP_403_FORBIDDEN,
    KYCVerificationException: status.HTTP_403_FORBIDDEN,
    AMLCheckException: status.HTTP_403_FORBIDDEN,
    SanctionsCheckException: status.HTTP_403_FORBIDDEN,
    SuspiciousActivityException: status.HTTP_403_FORBIDDEN,

    # Too Many Requests
    RateLimitException: status.HTTP_429_TOO_MANY_REQUESTS,

    # Service Unavailable exceptions
    DatabaseConnectionException: status.HTTP_503_SERVICE_UNAVAILABLE,
    MMOIntegrationException: status.HTTP_503_SERVICE_UNAVAILABLE,
    BankIntegrationException: status.HTTP_503_SERVICE_UNAVAILABLE,
    ExchangeRateException: status.HTTP_503_SERVICE_UNAVAILABLE,

    # Internal Server Error exceptions
    ConfigurationException: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def get_status_code_for_exception(exception: Exception) -> int:
    """
    Get the appropriate HTTP status code for an exception.

    Args:
        exception: The exception to get status code for

    Returns:
        int: HTTP status code
    """
    # Check exact exception type
    exception_type = type(exception)
    if exception_type in EXCEPTION_STATUS_CODES:
        return EXCEPTION_STATUS_CODES[exception_type]

    # Check if it's a subclass of any mapped exception
    for exc_class, status_code in EXCEPTION_STATUS_CODES.items():
        if isinstance(exception, exc_class):
            return status_code

    # Default to 500 for CAPPException
    if isinstance(exception, CAPPException):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    # Unknown exception types
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def capp_exception_handler(request: Request, exc: CAPPException) -> JSONResponse:
    """
    Handle CAPP-specific exceptions and convert to JSON responses.

    Args:
        request: The incoming request
        exc: The CAPP exception

    Returns:
        JSONResponse: JSON error response
    """
    status_code = get_status_code_for_exception(exc)

    logger.error(
        "CAPP exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        status_code=status_code,
        path=request.url.path,
        method=request.method,
    )

    response_data = exc.to_dict()

    # Add retry_after header for rate limit exceptions
    headers = {}
    if isinstance(exc, RateLimitException) and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])

    return JSONResponse(
        status_code=status_code,
        content=response_data,
        headers=headers if headers else None
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: The incoming request
        exc: The validation error

    Returns:
        JSONResponse: JSON error response
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        "Validation error occurred",
        errors=errors,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {
                "errors": errors
            }
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions.

    Args:
        request: The incoming request
        exc: The HTTP exception

    Returns:
        JSONResponse: JSON error response
    """
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": {}
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected/generic exceptions.

    Args:
        request: The incoming request
        exc: The exception

    Returns:
        JSONResponse: JSON error response
    """
    logger.error(
        "Unexpected exception occurred",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )

    # Don't expose internal error details in production
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            "details": {}
        }
    )


def register_error_handlers(app: Any) -> None:
    """
    Register all error handlers with the FastAPI application.

    Args:
        app: The FastAPI application instance
    """
    # CAPP-specific exceptions
    app.add_exception_handler(CAPPException, capp_exception_handler)

    # FastAPI/Pydantic validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Generic/unexpected exceptions
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Error handlers registered successfully")
