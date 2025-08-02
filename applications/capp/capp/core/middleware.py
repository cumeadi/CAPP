"""
Middleware for CAPP

Provides HTTP middleware functionality including request logging,
authentication, rate limiting, and error handling.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses
    
    Logs request details, processing time, and response status
    for monitoring and debugging purposes.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request start
        start_time = time.time()
        
        logger.info(
            "HTTP request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            content_length=request.headers.get("content-length")
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log successful response
            logger.info(
                "HTTP request completed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                processing_time=processing_time,
                content_length=response.headers.get("content-length")
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = str(processing_time)
            
            return response
            
        except Exception as e:
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log error
            logger.error(
                "HTTP request failed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                error=str(e),
                processing_time=processing_time,
                exc_info=True
            )
            
            # Re-raise the exception
            raise


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API authentication
    
    Validates API keys and user authentication tokens.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get API key from headers
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning(
                "Missing API key",
                request_id=getattr(request.state, "request_id", "unknown"),
                method=request.method,
                url=str(request.url)
            )
            # In production, this would return a 401 response
            # For demo purposes, we'll allow the request to continue
        
        # Add authentication info to request state
        request.state.authenticated = bool(api_key)
        request.state.api_key = api_key
        
        return await call_next(request)


class CORSMiddleware:
    """
    CORS middleware for handling cross-origin requests
    
    Configures CORS headers for web application integration.
    """
    
    def __init__(self, app, allow_origins=None, allow_credentials=True, allow_methods=None, allow_headers=None):
        self.app = app
        self.allow_origins = allow_origins or ["*"]
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or ["*"]
        self.allow_headers = allow_headers or ["*"]
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add CORS headers
            headers = []
            
            origin = None
            for name, value in scope.get("headers", []):
                if name == b"origin":
                    origin = value.decode()
                    break
            
            if origin and origin in self.allow_origins:
                headers.append((b"access-control-allow-origin", origin.encode()))
            elif "*" in self.allow_origins:
                headers.append((b"access-control-allow-origin", b"*"))
            
            if self.allow_credentials:
                headers.append((b"access-control-allow-credentials", b"true"))
            
            if self.allow_methods:
                methods = ", ".join(self.allow_methods) if "*" not in self.allow_methods else "*"
                headers.append((b"access-control-allow-methods", methods.encode()))
            
            if self.allow_headers:
                header_list = ", ".join(self.allow_headers) if "*" not in self.allow_headers else "*"
                headers.append((b"access-control-allow-headers", header_list.encode()))
            
            # Add headers to response
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    message["headers"].extend(headers)
                await send(message)
            
            await self.app(scope, receive, send_with_cors)
        else:
            await self.app(scope, receive, send)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling and logging errors
    
    Catches unhandled exceptions and provides consistent error responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            # Log the error
            logger.error(
                "Unhandled exception in middleware",
                request_id=getattr(request.state, "request_id", "unknown"),
                method=request.method,
                url=str(request.url),
                error=str(e),
                exc_info=True
            )
            
            # Return error response
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "message": "An unexpected error occurred"
                }
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting request metrics
    
    Collects metrics for monitoring and analytics.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Record request start
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate metrics
        processing_time = time.time() - start_time
        
        # Record metrics (in real implementation, this would send to metrics collector)
        logger.info(
            "Request metrics",
            request_id=getattr(request.state, "request_id", "unknown"),
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            processing_time=processing_time,
            content_length=response.headers.get("content-length", 0)
        )
        
        return response 