import structlog
from typing import Optional
from applications.capp.capp.core.redis import get_cache

logger = structlog.get_logger(__name__)

class IdempotencyService:
    """
    Service to handle idempotency keys preventing double-spending.
    Stores keys in Redis with a TTL.
    """
    def __init__(self, ttl_seconds: int = 86400): # Default 24h
        self.cache = get_cache()
        self.ttl = ttl_seconds

    async def check_lock(self, key: str) -> bool:
        """
        Check if key exists. If not, set it (acquire lock).
        Returns True if lock acquired (new request).
        Returns False if key exists (duplicate request).
        """
        try:
            redis_key = f"idempotency:{key}"
            # SETNX equivalent: set only if not exists
            is_new = await self.cache.setnx(redis_key, "LOCKED")
            
            if is_new:
                # Set Expiry
                await self.cache.expire(redis_key, self.ttl)
                return True
            else:
                logger.warning("Idempotency violation detected", key=key)
                return False
                
        except Exception as e:
            logger.error("Idempotency check failed (failing open)", error=str(e))
            # Fail Open or Closed?
            # For payments, Fail CLOSED is safer (deny if Redis down) to prevent double spend.
            # But for this MVP, we might log and allow if critical? 
            # SRE Decision: Fail CLOSED.
            return False

    async def release_lock(self, key: str):
        """Release lock (e.g. if transaction failed validation before submission)"""
        try:
            redis_key = f"idempotency:{key}"
            await self.cache.delete(redis_key)
        except Exception as e:
            logger.error("Failed to release idempotency lock", key=key, error=str(e))
