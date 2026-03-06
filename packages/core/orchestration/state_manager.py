"""
State Manager

Manages the state of payment processing flows and agents using Redis for persistence.
Implements aioredis (redis.asyncio) directly with JSON serialization.
Falls back to an in-memory store when Redis is unavailable.
"""

import json
import logging
from typing import Any, Dict, Optional

try:
    import redis.asyncio as aioredis
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

_STATE_PREFIX = "capp:state:"
_LOCK_PREFIX = "capp:lock:"


class _InMemoryFallback:
    """Minimal in-memory Redis-alike used when a real Redis server is unreachable."""

    def __init__(self) -> None:
        self._data: Dict[str, str] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._data[key] = value
        return True

    async def set_nx_ex(self, key: str, value: str, ex: int) -> bool:
        """Atomic set-if-not-exists with expiry (single-process simulation)."""
        if key not in self._data:
            self._data[key] = value
            return True
        return False

    async def delete(self, key: str) -> bool:
        existed = key in self._data
        self._data.pop(key, None)
        return existed

    async def ping(self) -> bool:
        return True


class StateManager:
    """
    Manages state for payment processing with Redis-backed persistence.

    All values are JSON-serialized before storage.  When Redis is unreachable the
    manager transparently falls back to a process-local in-memory store so callers
    are not affected during development or unit testing.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = _STATE_PREFIX,
    ):
        self._redis_url = redis_url
        self._prefix = key_prefix
        self._client: Optional[Any] = None  # aioredis.Redis or _InMemoryFallback

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to Redis; falls back to in-memory store on failure."""
        if not _REDIS_AVAILABLE:
            logger.warning("redis package not installed — using in-memory fallback")
            self._client = _InMemoryFallback()
            return True

        try:
            client = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await client.ping()
            self._client = client
            logger.info("StateManager connected to Redis at %s", self._redis_url)
            return True
        except Exception as exc:
            logger.warning(
                "Redis unavailable (%s) — using in-memory fallback", exc
            )
            self._client = _InMemoryFallback()
            return True  # caller can still proceed

    def _ensure_client(self) -> Any:
        if self._client is None:
            # Auto-create fallback so the manager is usable without an explicit connect()
            self._client = _InMemoryFallback()
        return self._client

    def _prefixed(self, key: str) -> str:
        return f"{self._prefix}{key}"

    # ------------------------------------------------------------------
    # State operations
    # ------------------------------------------------------------------

    async def set_state(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Persist *value* as JSON in Redis (or in-memory fallback)."""
        try:
            serialized = json.dumps(value)
            client = self._ensure_client()
            if isinstance(client, _InMemoryFallback):
                return await client.set(self._prefixed(key), serialized)
            if ttl is not None:
                return bool(await client.setex(self._prefixed(key), ttl, serialized))
            return bool(await client.set(self._prefixed(key), serialized))
        except Exception as exc:
            logger.error("set_state failed for key=%s: %s", key, exc)
            return False

    async def get_state(self, key: str) -> Optional[Any]:
        """Retrieve and JSON-deserialize a state value."""
        try:
            client = self._ensure_client()
            raw = await client.get(self._prefixed(key))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.error("get_state failed for key=%s: %s", key, exc)
            return None

    async def delete_state(self, key: str) -> bool:
        """Delete a state entry."""
        try:
            client = self._ensure_client()
            if isinstance(client, _InMemoryFallback):
                return await client.delete(self._prefixed(key))
            result = await client.delete(self._prefixed(key))
            return result > 0
        except Exception as exc:
            logger.error("delete_state failed for key=%s: %s", key, exc)
            return False

    # ------------------------------------------------------------------
    # Distributed locking (SETNX)
    # ------------------------------------------------------------------

    async def acquire_lock(self, lock_key: str, ttl: int = 30) -> bool:
        """Acquire a distributed lock using Redis SETNX.

        Uses the atomic ``SET key value NX EX ttl`` command so the lock expires
        automatically after *ttl* seconds even if the holder crashes.

        Returns ``True`` if the lock was acquired, ``False`` if it is already held.
        """
        full_key = f"{_LOCK_PREFIX}{lock_key}"
        try:
            client = self._ensure_client()
            if isinstance(client, _InMemoryFallback):
                return await client.set_nx_ex(full_key, "1", ttl)
            # Atomic SET NX EX — returns True on success, None if key already exists
            result = await client.set(full_key, "1", nx=True, ex=ttl)
            return result is True
        except Exception as exc:
            logger.error("acquire_lock failed for lock_key=%s: %s", lock_key, exc)
            return False

    async def release_lock(self, lock_key: str) -> bool:
        """Release a previously acquired distributed lock."""
        full_key = f"{_LOCK_PREFIX}{lock_key}"
        try:
            client = self._ensure_client()
            if isinstance(client, _InMemoryFallback):
                return await client.delete(full_key)
            result = await client.delete(full_key)
            return result > 0
        except Exception as exc:
            logger.error("release_lock failed for lock_key=%s: %s", lock_key, exc)
            return False
