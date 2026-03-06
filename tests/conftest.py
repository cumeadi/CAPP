"""
Shared test fixtures and helpers for CAPP test suite.
"""
import os
import sys
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

# Make `capp.*` importable (used by payment_orchestration.py and others)
_app_root = os.path.join(os.path.dirname(__file__), "..", "applications", "capp")
if _app_root not in sys.path:
    sys.path.insert(0, os.path.abspath(_app_root))

# ---------------------------------------------------------------------------
# Exclude SDK/agent test files that require 'canza_agents' (not installed
# in the CAPP dev environment — tested separately via SDK CI).
# ---------------------------------------------------------------------------
collect_ignore = [
    "integration/test_sdk_framework.py",
    "performance/test_sdk_performance.py",
    "test_capp.py",
    "unit/test_payment_optimizer_agent.py",
]


# ---------------------------------------------------------------------------
# Reusable payment-request fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def valid_payment_request():
    return {
        "reference_id": "test_ref_001",
        "payment_type": "personal_remittance",
        "payment_method": "mobile_money",
        "amount": "100.00",
        "from_currency": "USD",
        "to_currency": "KES",
        "sender_name": "Alice",
        "sender_phone": "+2348000000001",
        "sender_country": "NG",
        "recipient_name": "Bob",
        "recipient_phone": "+2547000000001",
        "recipient_country": "KE",
        "description": "family support",
    }


# ---------------------------------------------------------------------------
# Mock cache that behaves like MockRedisClient but is lightweight
# ---------------------------------------------------------------------------

class _FakeCache:
    """In-memory stand-in for the Redis MockRedisClient used in tests."""

    def __init__(self):
        self._store: dict = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self._store[key] = value
        return True

    async def setex(self, key, ex, value):
        self._store[key] = value
        return True

    async def delete(self, *keys):
        deleted = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                deleted += 1
            # Also remove composite hash sub-keys (hash simulation: key:field)
            prefix = f"{k}:"
            composite = [ck for ck in list(self._store.keys()) if ck.startswith(prefix)]
            for ck in composite:
                del self._store[ck]
            deleted += len(composite)
        return deleted

    async def ping(self):
        return True

    async def info(self, section=None):
        return {"redis_version": "7.0.0-mock"}

    async def hincrby(self, key, field, amount=1):
        composite = f"{key}:{field}"
        val = int(self._store.get(composite, 0)) + amount
        self._store[composite] = str(val)
        return val

    async def hget(self, key, field):
        return self._store.get(f"{key}:{field}")

    async def hgetall(self, key):
        prefix = f"{key}:"
        return {k[len(prefix):]: v for k, v in self._store.items() if k.startswith(prefix)}

    async def lpush(self, key, *values):
        lst = self._store.setdefault(key, [])
        for v in values:
            lst.insert(0, v)
        return len(lst)

    async def ltrim(self, key, start, end):
        if key in self._store:
            self._store[key] = self._store[key][start: end + 1 if end >= 0 else None]
        return True

    async def lrange(self, key, start, end):
        lst = self._store.get(key, [])
        return lst[start: end + 1 if end >= 0 else None]

    async def keys(self, pattern="*"):
        if pattern == "*":
            return list(self._store.keys())
        stem = pattern.replace("*", "")
        return [k for k in self._store.keys() if stem in k]

    async def exists(self, key):
        return int(key in self._store)


@pytest.fixture()
def fake_cache():
    return _FakeCache()
