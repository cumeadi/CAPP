
from slowapi import Limiter
from slowapi.util import get_remote_address
from applications.capp.capp.config.settings import settings
import redis

# Initialize Redis connection for Rate Limiter (if needed for storage)
# SlowAPI supports memory or Redis. For production, Redis is preferred.
# We will use the generic entrypoint.

def get_limiter_storage():
    """Return storage URI for limiter"""
    return settings.REDIS_URL

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
)
