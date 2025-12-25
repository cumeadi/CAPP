"""
Fraud Detection Service

Analyzes transaction patterns to detect suspicious activity.
Features:
- Velocity Checks (frequency of transactions)
- Structuring Detection (smurfing/split payments)
- Anomaly Detection
"""

import asyncio
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import structlog
import json

from ..core.redis import get_cache
from ..config.settings import get_settings

logger = structlog.get_logger(__name__)

class FraudDetectionService:
    """Service for detecting fraudulent transaction patterns"""
    
    def __init__(self):
        self.logger = logger
        self.cache = get_cache()
        self.settings = get_settings()
        
        # Configuration
        self.MAX_DAILY_VELOCITY = 10  # Max tx per day
        self.REPORTING_THRESHOLD = 10000.0
        self.STRUCTURING_RANGE = (9000.0, 9999.99) # Range suspicious of evading $10k limit
        
    async def analyze_transaction(self, 
                                user_id: str, 
                                amount: float, 
                                ip_address: Optional[str] = None) -> Dict[str, any]:
        """
        Analyze a transaction for risk factors.
        """
        risk_score = 0.0
        flags = []
        
        # 1. Structuring / Smurfing Check
        # Attempting to stay just below reporting limits
        if self.STRUCTURING_RANGE[0] <= amount <= self.STRUCTURING_RANGE[1]:
            risk_score += 0.6
            flags.append("STRUCTURING_SUSPICION_AMOUNT_RANGE")
            
        # 2. Maximum Amount Check
        if amount > self.REPORTING_THRESHOLD:
            # Not necessarily fraud, but high risk requiring enhanced due diligence (EDD)
            risk_score += 0.3
            flags.append("LARGE_TRANSACTION_EDD_REQUIRED")
            
        # 3. Velocity Check (Redis)
        # We track usage using a simple counter key pattern: fraud:velocity:user_id:date
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            key = f"fraud:velocity:{user_id}:{today}"
            
            # Increment and get new value
            count = await self.cache.incr(key)
            if count == 1:
                # Set expiry for 24 hours
                await self.cache.expire(key, 86400)
                
            if count > self.MAX_DAILY_VELOCITY:
                risk_score += 0.8
                flags.append(f"HIGH_VELOCITY_DAILY_LIMIT_EXCEEDED ({count}/{self.MAX_DAILY_VELOCITY})")
            elif count > (self.MAX_DAILY_VELOCITY * 0.7):
                risk_score += 0.2 # Warning territory
                
        except Exception as e:
            self.logger.warning("Redis velocity check failed, skipping", error=str(e))
            
        # Normalize Score (0.0 to 1.0)
        risk_score = min(risk_score, 1.0)
        
        return {
            "risk_score": risk_score,
            "is_high_risk": risk_score > 0.7,
            "flags": flags
        }
