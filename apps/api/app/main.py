from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog
import asyncio
import sys
import os

from applications.capp.capp.config.settings import settings
from applications.capp.capp.core.limiter import limiter
from applications.capp.capp.core.redis import init_redis
from applications.capp.capp.core.aptos import init_aptos_client
from applications.capp.capp.core.polygon import init_polygon_client
from applications.capp.capp.services.chain_listener import ChainListenerService

from .database import engine, Base
from .routers import wallet, agents, chain_data, bridge, starknet, routing, system, admin_dlq, identity, compliance

logger = structlog.get_logger(__name__)

# Fix path to allow importing from applications (Legacy support)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# Create DB Tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("system_startup")
    try:
        await init_redis()
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))
    
    await init_aptos_client()
    await init_polygon_client()
    
    # Background Tasks
    listener = ChainListenerService()
    asyncio.create_task(listener.start_listening())
    logger.info("chain_listener_started")
    
    yield
    # Shutdown
    logger.info("system_shutdown")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Register Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Register Routers
app.include_router(wallet.router)
app.include_router(agents.router)
app.include_router(chain_data.router)
app.include_router(bridge.router)
app.include_router(starknet.router)
app.include_router(routing.router)
app.include_router(system.router)
app.include_router(admin_dlq.router)
app.include_router(identity.router)
app.include_router(compliance.router)

@app.get("/")
async def root():
    return {"message": "Welcome to CAPP Wallet API. System Online.", "environment": settings.ENVIRONMENT}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}
