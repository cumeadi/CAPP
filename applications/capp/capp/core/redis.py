"""
Redis connection management for CAPP
"""

import asyncio
from typing import Optional, Any, List
import json
import pickle
import time

import redis.asyncio as redis
import structlog

from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection"""
    global _redis_client
    
    settings = get_settings()
    
    try:
        # Create Redis client
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
            max_connections=settings.REDIS_POOL_SIZE
        )
        
        # Test connection
        await _redis_client.ping()
        
        logger.info("Redis initialized successfully")
        
    except Exception as e:
        logger.warning("Failed to connect to Redis, using mock client for demo", error=str(e))
        # Create a mock Redis client for demo purposes
        _redis_client = MockRedisClient()
        logger.info("Mock Redis client initialized for demo")


async def close_redis() -> None:
    """Close Redis connection"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


def get_redis_client() -> redis.Redis:
    """Get Redis client"""
    global _redis_client
    if not _redis_client:
        # Lazy initialization fallback
        logger.warning("Redis client not initialized, performing lazy initialization (Mock)")
        _redis_client = MockRedisClient()
        
    return _redis_client


class MockRedisClient:
    """Mock Redis client for demo purposes when Redis is not available"""
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
    
    async def ping(self) -> bool:
        """Mock ping"""
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Mock get"""
        if key in self._data:
            # Check expiry
            if key in self._expiry and self._expiry[key] < time.time():
                del self._data[key]
                del self._expiry[key]
                return None
            return self._data[key]
        return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock set"""
        self._data[key] = value
        if ex:
            self._expiry[key] = time.time() + ex
        return True
    
    async def setex(self, key: str, ex: int, value: str) -> bool:
        """Mock setex"""
        self._data[key] = value
        self._expiry[key] = time.time() + ex
        return True
    
    async def delete(self, key: str) -> int:
        """Mock delete"""
        if key in self._data:
            del self._data[key]
            if key in self._expiry:
                del self._expiry[key]
            return 1
        return 0
    
    async def exists(self, key: str) -> int:
        """Mock exists"""
        return 1 if key in self._data else 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Mock expire"""
        if key in self._data:
            self._expiry[key] = time.time() + ttl
            return True
        return False
    
    async def ttl(self, key: str) -> int:
        """Mock ttl"""
        if key in self._expiry:
            remaining = self._expiry[key] - time.time()
            return max(0, int(remaining))
        return -1
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Mock incr"""
        current = int(self._data.get(key, 0))
        new_value = current + amount
        self._data[key] = str(new_value)
        return new_value
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Mock decr"""
        current = int(self._data.get(key, 0))
        new_value = current - amount
        self._data[key] = str(new_value)
        return new_value
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Mock hget"""
        hash_key = f"{key}:{field}"
        return self._data.get(hash_key)
    
    async def hset(self, key: str, field: str, value: str) -> int:
        """Mock hset"""
        hash_key = f"{key}:{field}"
        self._data[hash_key] = value
        return 1
    
    async def hgetall(self, key: str) -> dict:
        """Mock hgetall"""
        result = {}
        prefix = f"{key}:"
        for k, v in self._data.items():
            if k.startswith(prefix):
                field = k[len(prefix):]
                result[field] = v
        return result
    
    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Mock hincrby"""
        hash_key = f"{key}:{field}"
        current = int(self._data.get(hash_key, 0))
        new_value = current + amount
        self._data[hash_key] = str(new_value)
        return new_value
    
    async def keys(self, pattern: str) -> List[str]:
        """Mock keys"""
        # Simple pattern matching for demo
        if pattern == "*":
            return list(self._data.keys())
        return [k for k in self._data.keys() if pattern.replace("*", "") in k]
    
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Mock lrange"""
        if key in self._data and isinstance(self._data[key], list):
            return self._data[key][start:end+1]
        return []
    
    async def lpush(self, key: str, *values: str) -> int:
        """Mock lpush"""
        if key not in self._data:
            self._data[key] = []
        if not isinstance(self._data[key], list):
            self._data[key] = []
        self._data[key].extend(values)
        return len(self._data[key])
    
    async def rpop(self, key: str) -> Optional[str]:
        """Mock rpop"""
        if key in self._data and isinstance(self._data[key], list) and self._data[key]:
            return self._data[key].pop()
        return None
    
    async def llen(self, key: str) -> int:
        """Mock llen"""
        if key in self._data and isinstance(self._data[key], list):
            return len(self._data[key])
        return 0
    
    async def close(self):
        """Mock close"""
        self._data.clear()
        self._expiry.clear()

    async def setnx(self, key: str, value: str) -> bool:
        """Mock setnx"""
        # DEBUG LOG
        logger.info(f"DEBUG: MockRedis.setnx called", key=key, existing_keys=list(self._data.keys()))
        
        if key in self._data:
            # Check expiry
            if key in self._expiry and self._expiry[key] < time.time():
                logger.info(f"DEBUG: Key {key} expired.")
                del self._data[key]
                del self._expiry[key]
            else:
                logger.info(f"DEBUG: Key {key} EXISTS. Returning False.")
                return False # Key exists
                
        self._data[key] = value
        logger.info(f"DEBUG: Key {key} SET. Returning True.")
        return True


class RedisCache:
    """Redis cache wrapper with serialization support"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return default
            
            # Try to deserialize JSON first, then pickle
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                try:
                    return pickle.loads(value.encode('latin1'))
                except Exception:
                    return value
                    
        except Exception as e:
            logger.warning("Failed to get from cache", key=key, error=str(e))
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            # Try JSON serialization first, fallback to pickle
            try:
                serialized = json.dumps(value)
            except (TypeError, ValueError):
                serialized = pickle.dumps(value).decode('latin1')
            
            if ttl:
                return await self.redis.setex(key, ttl, serialized)
            else:
                return await self.redis.set(key, serialized)
                
        except Exception as e:
            logger.warning("Failed to set cache", key=key, error=str(e))
            return False
            
    async def setnx(self, key: str, value: Any) -> bool:
        """Set value if not exists (Atomic Lock)"""
        try:
            # Try JSON serialization first, fallback to pickle
            try:
                serialized = json.dumps(value)
            except (TypeError, ValueError):
                serialized = str(value)
            
            # Use set(nx=True) which is modern Redis API, or setnx if available
            if hasattr(self.redis, "setnx"):
                # MockRedis or older redis-py
                result = await self.redis.setnx(key, serialized)
            else:
                # Modern redis-py uses set(nx=True)
                result = await self.redis.set(key, serialized, nx=True)
                
            return bool(result)
                
        except Exception as e:
            logger.warning("Failed to setnx cache", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.warning("Failed to delete from cache", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.warning("Failed to check cache existence", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.warning("Failed to set cache expiration", key=key, error=str(e))
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.warning("Failed to get cache TTL", key=key, error=str(e))
            return -1
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return await self.redis.incr(key, amount)
        except Exception as e:
            logger.warning("Failed to increment counter", key=key, error=str(e))
            return 0
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        try:
            return await self.redis.decr(key, amount)
        except Exception as e:
            logger.warning("Failed to decrement counter", key=key, error=str(e))
            return 0
    
    async def hget(self, key: str, field: str, default: Any = None) -> Any:
        """Get hash field"""
        try:
            value = await self.redis.hget(key, field)
            if value is None:
                return default
            
            # Try to deserialize
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.warning("Failed to get hash field", key=key, field=field, error=str(e))
            return default
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Set hash field"""
        try:
            # Try JSON serialization
            try:
                serialized = json.dumps(value)
            except (TypeError, ValueError):
                serialized = str(value)
            
            result = await self.redis.hset(key, field, serialized)
            return result >= 0
            
        except Exception as e:
            logger.warning("Failed to set hash field", key=key, field=field, error=str(e))
            return False
            
    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Increment hash field"""
        try:
            return await self.redis.hincrby(key, field, amount)
        except Exception as e:
            logger.warning("Failed to increment hash field", key=key, field=field, error=str(e))
            return 0
    
    async def hgetall(self, key: str) -> dict:
        """Get all hash fields"""
        try:
            data = await self.redis.hgetall(key)
            result = {}
            
            for field, value in data.items():
                try:
                    result[field] = json.loads(value)
                except json.JSONDecodeError:
                    result[field] = value
            
            return result
            
        except Exception as e:
            logger.warning("Failed to get all hash fields", key=key, error=str(e))
            return {}
    
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to list"""
        try:
            serialized_values = []
            for value in values:
                try:
                    serialized_values.append(json.dumps(value))
                except (TypeError, ValueError):
                    serialized_values.append(str(value))
            
            return await self.redis.lpush(key, *serialized_values)
            
        except Exception as e:
            logger.warning("Failed to push to list", key=key, error=str(e))
            return 0
    
    async def rpop(self, key: str, default: Any = None) -> Any:
        """Pop value from list"""
        try:
            value = await self.redis.rpop(key)
            if value is None:
                return default
            
            # Try to deserialize
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.warning("Failed to pop from list", key=key, error=str(e))
            return default
    
    async def llen(self, key: str) -> int:
        """Get list length"""
        try:
            return await self.redis.llen(key)
        except Exception as e:
            logger.warning("Failed to get list length", key=key, error=str(e))
            return 0
            
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim list"""
        try:
            return await self.redis.ltrim(key, start, end)
        except Exception as e:
            logger.warning("Failed to trim list", key=key, error=str(e))
            return False


# Global cache instance
_cache: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get Redis cache instance"""
    global _cache
    
    if not _cache:
        redis_client = get_redis_client()
        _cache = RedisCache(redis_client)
    
    return _cache 