"""
Redis Client Integration

Universal Redis client for caching, state management, and data storage
with support for serialization, connection pooling, and fallback mechanisms.
"""

import asyncio
import json
import pickle
from typing import Optional, Any, List, Dict, Union
from datetime import datetime, timezone
from enum import Enum

import redis.asyncio as redis
import structlog
from pydantic import BaseModel, Field


logger = structlog.get_logger(__name__)


class SerializationFormat(str, Enum):
    """Data serialization formats"""
    JSON = "json"
    PICKLE = "pickle"
    STRING = "string"
    AUTO = "auto"


class RedisConfig(BaseModel):
    """Configuration for Redis client"""
    url: str = "redis://localhost:6379"
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    username: Optional[str] = None
    
    # Connection settings
    socket_connect_timeout: int = 5
    socket_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    max_connections: int = 10
    
    # Serialization settings
    default_serialization: SerializationFormat = SerializationFormat.AUTO
    enable_compression: bool = False
    
    # Fallback settings
    enable_mock_fallback: bool = True
    mock_fallback_on_error: bool = True


class RedisClient:
    """
    Redis client with advanced features
    
    Provides a unified interface for Redis operations with:
    - Automatic serialization/deserialization
    - Connection pooling and health checks
    - Mock fallback for development
    - Error handling and retry logic
    """
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Redis client
        self._redis_client: Optional[redis.Redis] = None
        self._mock_client: Optional[MockRedisClient] = None
        self._using_mock = False
        
        # Initialize connection
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Redis client"""
        try:
            # Create Redis client
            self._redis_client = redis.from_url(
                self.config.url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_timeout=self.config.socket_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval,
                max_connections=self.config.max_connections
            )
            
            self.logger.info("Redis client initialized", url=self.config.url)
            
        except Exception as e:
            self.logger.warning("Failed to initialize Redis client", error=str(e))
            
            if self.config.enable_mock_fallback:
                self._mock_client = MockRedisClient()
                self._using_mock = True
                self.logger.info("Using mock Redis client as fallback")
    
    async def connect(self) -> bool:
        """Connect to Redis"""
        try:
            if self._using_mock:
                return True
            
            if self._redis_client:
                await self._redis_client.ping()
                self.logger.info("Connected to Redis successfully")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to connect to Redis", error=str(e))
            
            if self.config.enable_mock_fallback and not self._using_mock:
                self._mock_client = MockRedisClient()
                self._using_mock = True
                self.logger.info("Switched to mock Redis client")
                return True
            
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        try:
            if self._redis_client and not self._using_mock:
                await self._redis_client.close()
                self._redis_client = None
                self.logger.info("Disconnected from Redis")
            
            if self._mock_client:
                await self._mock_client.close()
                self._mock_client = None
                self._using_mock = False
                
        except Exception as e:
            self.logger.error("Failed to disconnect from Redis", error=str(e))
    
    def _get_client(self) -> Union[redis.Redis, MockRedisClient]:
        """Get the active Redis client"""
        if self._using_mock and self._mock_client:
            return self._mock_client
        elif self._redis_client:
            return self._redis_client
        else:
            raise RuntimeError("No Redis client available")
    
    def _serialize(self, value: Any, format: SerializationFormat = None) -> str:
        """Serialize value to string"""
        try:
            serialization_format = format or self.config.default_serialization
            
            if serialization_format == SerializationFormat.JSON:
                return json.dumps(value)
            elif serialization_format == SerializationFormat.PICKLE:
                return pickle.dumps(value).decode('latin1')
            elif serialization_format == SerializationFormat.STRING:
                return str(value)
            elif serialization_format == SerializationFormat.AUTO:
                # Try JSON first, fallback to pickle
                try:
                    return json.dumps(value)
                except (TypeError, ValueError):
                    return pickle.dumps(value).decode('latin1')
            else:
                raise ValueError(f"Unknown serialization format: {serialization_format}")
                
        except Exception as e:
            self.logger.error("Failed to serialize value", error=str(e))
            return str(value)
    
    def _deserialize(self, value: str, format: SerializationFormat = None) -> Any:
        """Deserialize value from string"""
        try:
            if value is None:
                return None
            
            serialization_format = format or self.config.default_serialization
            
            if serialization_format == SerializationFormat.JSON:
                return json.loads(value)
            elif serialization_format == SerializationFormat.PICKLE:
                return pickle.loads(value.encode('latin1'))
            elif serialization_format == SerializationFormat.STRING:
                return value
            elif serialization_format == SerializationFormat.AUTO:
                # Try JSON first, fallback to pickle
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    try:
                        return pickle.loads(value.encode('latin1'))
                    except Exception:
                        return value
            else:
                raise ValueError(f"Unknown serialization format: {serialization_format}")
                
        except Exception as e:
            self.logger.error("Failed to deserialize value", error=str(e))
            return value
    
    async def get(self, key: str, default: Any = None, format: SerializationFormat = None) -> Any:
        """Get value from Redis"""
        try:
            client = self._get_client()
            value = await client.get(key)
            
            if value is None:
                return default
            
            return self._deserialize(value, format)
            
        except Exception as e:
            self.logger.warning("Failed to get from Redis", key=key, error=str(e))
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, format: SerializationFormat = None) -> bool:
        """Set value in Redis"""
        try:
            client = self._get_client()
            serialized_value = self._serialize(value, format)
            
            if ttl:
                return await client.setex(key, ttl, serialized_value)
            else:
                return await client.set(key, serialized_value)
                
        except Exception as e:
            self.logger.warning("Failed to set in Redis", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis"""
        try:
            client = self._get_client()
            result = await client.delete(key)
            return result > 0
            
        except Exception as e:
            self.logger.warning("Failed to delete from Redis", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            client = self._get_client()
            return await client.exists(key) > 0
            
        except Exception as e:
            self.logger.warning("Failed to check existence in Redis", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        try:
            client = self._get_client()
            return await client.expire(key, ttl)
            
        except Exception as e:
            self.logger.warning("Failed to set expiration in Redis", key=key, error=str(e))
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        try:
            client = self._get_client()
            return await client.ttl(key)
            
        except Exception as e:
            self.logger.warning("Failed to get TTL from Redis", key=key, error=str(e))
            return -1
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            client = self._get_client()
            return await client.incr(key, amount)
            
        except Exception as e:
            self.logger.warning("Failed to increment in Redis", key=key, error=str(e))
            return 0
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        try:
            client = self._get_client()
            return await client.decr(key, amount)
            
        except Exception as e:
            self.logger.warning("Failed to decrement in Redis", key=key, error=str(e))
            return 0
    
    async def hget(self, key: str, field: str, default: Any = None, format: SerializationFormat = None) -> Any:
        """Get hash field"""
        try:
            client = self._get_client()
            value = await client.hget(key, field)
            
            if value is None:
                return default
            
            return self._deserialize(value, format)
            
        except Exception as e:
            self.logger.warning("Failed to get hash field from Redis", key=key, field=field, error=str(e))
            return default
    
    async def hset(self, key: str, field: str, value: Any, format: SerializationFormat = None) -> bool:
        """Set hash field"""
        try:
            client = self._get_client()
            serialized_value = self._serialize(value, format)
            result = await client.hset(key, field, serialized_value)
            return result >= 0
            
        except Exception as e:
            self.logger.warning("Failed to set hash field in Redis", key=key, field=field, error=str(e))
            return False
    
    async def hgetall(self, key: str, format: SerializationFormat = None) -> Dict[str, Any]:
        """Get all hash fields"""
        try:
            client = self._get_client()
            data = await client.hgetall(key)
            result = {}
            
            for field, value in data.items():
                result[field] = self._deserialize(value, format)
            
            return result
            
        except Exception as e:
            self.logger.warning("Failed to get all hash fields from Redis", key=key, error=str(e))
            return {}
    
    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Increment hash field"""
        try:
            client = self._get_client()
            return await client.hincrby(key, field, amount)
            
        except Exception as e:
            self.logger.warning("Failed to increment hash field in Redis", key=key, field=field, error=str(e))
            return 0
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        try:
            client = self._get_client()
            return await client.keys(pattern)
            
        except Exception as e:
            self.logger.warning("Failed to get keys from Redis", pattern=pattern, error=str(e))
            return []
    
    async def lpush(self, key: str, *values: Any, format: SerializationFormat = None) -> int:
        """Push values to list"""
        try:
            client = self._get_client()
            serialized_values = [self._serialize(value, format) for value in values]
            return await client.lpush(key, *serialized_values)
            
        except Exception as e:
            self.logger.warning("Failed to push to list in Redis", key=key, error=str(e))
            return 0
    
    async def rpop(self, key: str, default: Any = None, format: SerializationFormat = None) -> Any:
        """Pop value from list"""
        try:
            client = self._get_client()
            value = await client.rpop(key)
            
            if value is None:
                return default
            
            return self._deserialize(value, format)
            
        except Exception as e:
            self.logger.warning("Failed to pop from list in Redis", key=key, error=str(e))
            return default
    
    async def llen(self, key: str) -> int:
        """Get list length"""
        try:
            client = self._get_client()
            return await client.llen(key)
            
        except Exception as e:
            self.logger.warning("Failed to get list length from Redis", key=key, error=str(e))
            return 0
    
    async def lrange(self, key: str, start: int, end: int, format: SerializationFormat = None) -> List[Any]:
        """Get range from list"""
        try:
            client = self._get_client()
            values = await client.lrange(key, start, end)
            return [self._deserialize(value, format) for value in values]
            
        except Exception as e:
            self.logger.warning("Failed to get range from list in Redis", key=key, error=str(e))
            return []
    
    async def ping(self) -> bool:
        """Ping Redis server"""
        try:
            client = self._get_client()
            return await client.ping()
            
        except Exception as e:
            self.logger.warning("Failed to ping Redis", error=str(e))
            return False
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get Redis health status"""
        try:
            is_connected = await self.ping()
            
            return {
                "connected": is_connected,
                "using_mock": self._using_mock,
                "url": self.config.url,
                "max_connections": self.config.max_connections,
                "default_serialization": self.config.default_serialization,
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get health status", error=str(e))
            return {"error": str(e)}


class MockRedisClient:
    """Mock Redis client for development and testing"""
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
        self.logger = structlog.get_logger(__name__)
    
    async def ping(self) -> bool:
        """Mock ping"""
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Mock get"""
        if key in self._data:
            # Check expiry
            if key in self._expiry and self._expiry[key] < asyncio.get_event_loop().time():
                del self._data[key]
                del self._expiry[key]
                return None
            return self._data[key]
        return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock set"""
        self._data[key] = value
        if ex:
            self._expiry[key] = asyncio.get_event_loop().time() + ex
        return True
    
    async def setex(self, key: str, ex: int, value: str) -> bool:
        """Mock setex"""
        self._data[key] = value
        self._expiry[key] = asyncio.get_event_loop().time() + ex
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
            self._expiry[key] = asyncio.get_event_loop().time() + ttl
            return True
        return False
    
    async def ttl(self, key: str) -> int:
        """Mock ttl"""
        if key in self._expiry:
            remaining = self._expiry[key] - asyncio.get_event_loop().time()
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
        self.logger.info("Mock Redis client closed") 