
import structlog
from typing import Dict, Optional, Any
from enum import Enum
from datetime import datetime

logger = structlog.get_logger(__name__)

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class OracleService:
    _instance: Optional['OracleService'] = None
    
import json
from applications.capp.capp.core.redis import get_redis_client

class OracleService:
    _instance: Optional['OracleService'] = None
    
    def __init__(self):
        # Redis Key Prefix
        self.KEY_PREFIX = "oracle:tx:"
        self.TTL_SECONDS = 60 * 60 * 24 * 30 # 30 Days
        self.logger = structlog.get_logger(__name__)

    @classmethod
    def get_instance(cls) -> 'OracleService':
        if cls._instance is None:
            cls._instance = OracleService()
        return cls._instance

    def _get_redis(self):
        """Helper to get redis client lazily or handle mock context"""
        try:
            return get_redis_client()
        except RuntimeError:
            # Fallback for tests if init_redis() wasn't called (though it should be)
            self.logger.warning("Redis client not initialized, using in-memory mock dict for safety.")
            if not hasattr(self, "_mock_store"): self._mock_store = {}
            return None

    async def update_index(self, tx_hash: str, status: TransactionStatus, meta: Optional[Dict] = None):
        """
        Internal Hook: Updates the status of a transaction in the index (Redis).
        """
        redis = self._get_redis()
        
        entry = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat(),
            "meta": meta or {}
        }
        
        # Merge if exists
        key = f"{self.KEY_PREFIX}{tx_hash}"
        
        if redis: # Redis Mode
            raw_existing = await redis.get(key)
            if raw_existing:
                existing = json.loads(raw_existing)
                entry["meta"] = {**existing.get("meta", {}), **entry["meta"]}
            
            await redis.setex(key, self.TTL_SECONDS, json.dumps(entry))
            
        else: # Mock Mode
            if key in self._mock_store:
                existing = self._mock_store[key]
                entry["meta"] = {**existing.get("meta", {}), **entry["meta"]}
            self._mock_store[key] = entry
            
        self.logger.info(f"Oracle Index Updated: {tx_hash} -> {status}", meta=entry["meta"])

    async def get_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Public SDK Hook: Query the status of a transaction.
        """
        redis = self._get_redis()
        key = f"{self.KEY_PREFIX}{tx_hash}"
        
        if redis:
            raw = await redis.get(key)
            if raw:
                return json.loads(raw)
        else:
            if key in self._mock_store:
                return self._mock_store[key]
                
        return {"status": "UNKNOWN", "message": "Transaction not found in Oracle Index."}

    def get_all_transactions(self) -> Dict[str, Dict[str, Any]]:
        """Debug helper - Scan not efficient for Redis but okay for debug"""
        return {} # Disable scan for now to avoid perf issues

