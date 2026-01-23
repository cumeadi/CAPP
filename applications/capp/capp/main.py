"""
Main FastAPI application for CAPP

This module initializes the FastAPI application with all necessary
middleware, routes, and startup/shutdown events.
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .config.settings import settings
from .api.v1.router import api_router
from .core.rate_limit import limiter, rate_limit_exceeded_handler
from .core.validation import RequestValidationMiddleware
from .core.security_headers import SecurityHeadersMiddleware
from .core.secrets import validate_all_secrets_on_startup
from .core.error_handlers import register_error_handlers
from .core.redis import init_redis, close_redis
from .core.database import init_db, close_db
from .core.aptos import init_aptos_client, close_aptos_client
from .core.polygon import init_polygon_client

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="CAPP - Canza Autonomous Payment Protocol",
    description="AI-powered payment system for African cross-border commerce",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter state
app.state.limiter = limiter

# Register error handlers (handles all application exceptions)
register_error_handlers(app)

# Add rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add security headers middleware (first to ensure all responses have security headers)
app.add_middleware(SecurityHeadersMiddleware)

# Add validation middleware (processes requests before other middleware)
app.add_middleware(RequestValidationMiddleware)

# Add CORS middleware
origins = settings.ALLOWED_ORIGINS
# Force add development origins to ensure connectivity
if True: # Always ensure these are present for now
    origins.extend(["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(origins)),  # Environment-based whitelist + dev defaults
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-API-Key"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("Starting CAPP application...")
    logger.info(f"Allowed Origins: {settings.ALLOWED_ORIGINS}")

    # Initialize Redis
    await init_redis()

    # Initialize Database
    await init_db()

    # Initialize Blockchain Clients
    await init_aptos_client()
    await init_polygon_client()

    # Validate secrets on startup
    validate_all_secrets_on_startup()

    logger.info("CAPP application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Shutting down CAPP application...")
    
    # Close Redis
    await close_redis()

    # Close Database
    await close_db()

    # Close Blockchain Clients
    await close_aptos_client()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CAPP - Canza Autonomous Payment Protocol",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "capp",
        "version": "1.0.0"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    import traceback
    traceback.print_exc()
    logger.error(
        "Unhandled exception",
        error=str(exc),
        url=str(request.url),
        method=request.method
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 