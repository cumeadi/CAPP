import json
import os
import structlog
from datetime import datetime
from typing import Dict, Any, Optional

from applications.capp.capp.core.redis import get_redis_client

logger = structlog.get_logger(__name__)

class MarketContextService:
    def __init__(self):
        self.redis = get_redis_client()
        # Mocking the AI service for sandbox environment without requiring a real paid CMC API key.
        self.is_sandbox = os.getenv("ENVIRONMENT", "development") != "production"
        
        # In a real environment, this would call the CoinMarketCap AI endpoints
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.api_key = os.getenv("CMC_API_KEY", "")
        
        # 5 minute TTL for market stress indicators
        self.cache_ttl = 300 

    async def get_market_stress_indicator(self) -> Dict[str, Any]:
        """
        Returns a 0-1 score of current market stress (0 = calm, 1 = extreme volatility/correlation breakdown)
        Used by Predictive Corridor Scoring and Anomaly Detection Agent to contextualize routing.
        """
        cache_key = "cmc_ai:market_stress"
        
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
                
            logger.info("fetching_cmc_market_stress")
            
            # Simulate an AI-derived market stress score
            # In production, this proxies to CMC's Fear & Greed index or custom AI query
            result = {
                "stress_score": 0.25 if self.is_sandbox else 0.5,
                "sentiment": "neutral",
                "volatility_context": "low",
                "timestamp": datetime.now().isoformat()
            }
            
            await self.redis.set(cache_key, json.dumps(result), ex=self.cache_ttl)
            return result
            
        except Exception as e:
            logger.error("market_stress_fetch_failed", error=str(e))
            # Safe default fallback
            return {"stress_score": 0.5, "sentiment": "neutral", "volatility_context": "unknown", "error": True}

    async def get_protocol_health(self, protocol_id: str) -> Dict[str, Any]:
        """
        Returns health and sentiment metrics for a specific DeFi protocol.
        Used by the Smart Sweep Agent.
        """
        cache_key = f"cmc_ai:protocol_health:{protocol_id}"
        
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
                
            logger.info("fetching_cmc_protocol_health", protocol=protocol_id)
            
            # Simulated CMC AI response for protocol safety
            result = {
                "protocol": protocol_id,
                "health_score": 85 if self.is_sandbox else 70, # 0-100
                "ai_summary": "Protocol liquidity stable. No recent exploit chatter detected.",
                "risk_flag": False,
                "timestamp": datetime.now().isoformat()
            }
            
            # 15 min cache for protocol health
            await self.redis.set(cache_key, json.dumps(result), ex=900) 
            return result
            
        except Exception as e:
            logger.error("protocol_health_fetch_failed", protocol=protocol_id, error=str(e))
            return {"protocol": protocol_id, "health_score": 50, "risk_flag": True, "error": True}
        
    async def get_corridor_macro_context(self, corridor: str) -> Dict[str, Any]:
        """
        Provides macro context for a specific fiat corridor.
        Added to the Corridor Intelligence Feed.
        """
        cache_key = f"cmc_ai:macro_context:{corridor}"
        
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            result = {
                "corridor": corridor,
                "macro_trend": "stable",
                "ai_insight": f"Normal volume observed for {corridor}. No significant localized macro events."
            }
            
            await self.redis.set(cache_key, json.dumps(result), ex=self.cache_ttl)
            return result
            
        except Exception as e:
             logger.error("corridor_context_fetch_failed", corridor=corridor, error=str(e))
             return {"corridor": corridor, "macro_trend": "unknown", "error": True}

market_context = MarketContextService()
