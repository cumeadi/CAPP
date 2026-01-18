from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from .. import database
from applications.capp.capp.core.redis import get_redis_client, MockRedisClient
from applications.capp.capp.config.settings import settings
import structlog

router = APIRouter(
    prefix="/system",
    tags=["system"]
)

logger = structlog.get_logger(__name__)

@router.get("/health")
async def health_check(db: Session = Depends(database.get_db)):
    health_status = {
        "status": "healthy",
        "services": {
            "database": "unknown",
            "redis": "unknown",
            "rpc": "unknown"
        }
    }

    # 1. Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = "disconnected"
        health_status["status"] = "degraded"
        logger.error("Health Check: DB Failed", error=str(e))

    # 2. Check Redis
    try:
        redis = get_redis_client()
        await redis.ping()
        is_mock = isinstance(redis, MockRedisClient)
        health_status["services"]["redis"] = "connected (mock)" if is_mock else "connected"
    except Exception as e:
        health_status["services"]["redis"] = "disconnected"
        health_status["status"] = "degraded"
        logger.error("Health Check: Redis Failed", error=str(e))

    # 3. Check RPC Config
    # 3. Check RPC Config
    if settings.POLYGON_RPC_URL and "alchemy" in settings.POLYGON_RPC_URL:
         health_status["services"]["rpc"] = "configured"
    else:
         health_status["services"]["rpc"] = "missing_config"
         # Not critical for app start, but good to know
    
    return health_status

@router.post("/sweep")
async def trigger_sweep():
    """Manually trigger Smart Sweep for testing."""
    from applications.capp.capp.services.yield_service import YieldService
    service = YieldService()
    await service.monitor_idle_funds()
    return {"status": "Sweep Triggered"}
