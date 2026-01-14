import structlog
from typing import List, Optional
import time
from decimal import Decimal

from applications.capp.capp.core.aptos import get_aptos_client
from applications.capp.capp.core.polygon import PolygonSettlementService
from applications.capp.capp.core.starknet import get_starknet_client
from applications.capp.capp.config.settings import get_settings

# We'll use the API schema for now to avoid circular imports if we used models/payments.py
# ensuring we decouple enough. Ideally we move models to a shared lib.
# For now, let's define a DTO here or import from schemas if possible.
# But importing from apps.api... is bad. 
# Let's define a simple dataclass here and let the API map it.

from dataclasses import dataclass

logger = structlog.get_logger(__name__)

@dataclass
class RouteOption:
    chain: str
    fee_usd: float
    eta_seconds: int
    recommendation_score: float
    reason: str
    estimated_gas_token: float

class PaymentRouter:
    """
    Intelligent Payment Routing Engine.
    Evaluates paths across supported chains to find the optimal route.
    """
    
    def __init__(self):
        self.settings = get_settings()
        # Price feeds (Mocked for now, usually fetched from Oracle/Coingecko)
        self.prices = {
            "APT": 10.50,
            "MATIC": 0.85,
            "ETH": 2200.0,
            "USDC": 1.00
        }

    async def calculate_routes(self, amount_usd: float, recipient: str, preference: str = "CHEAPEST") -> List[RouteOption]:
        """
        Calculate and rank routes for a given transfer.
        """
        routes = []
        
        # 1. Evaluate Aptos
        try:
            apt_route = await self._evaluate_aptos(amount_usd, recipient)
            routes.append(apt_route)
        except Exception as e:
            logger.error("Failed to evaluate Aptos route", error=str(e))

        # 2. Evaluate Polygon
        try:
            poly_route = await self._evaluate_polygon(amount_usd, recipient)
            routes.append(poly_route)
        except Exception as e:
            logger.error("Failed to evaluate Polygon route", error=str(e))

        # 3. Evaluate Starknet
        try:
            stark_route = await self._evaluate_starknet(amount_usd, recipient)
            routes.append(stark_route)
        except Exception as e:
            logger.error("Failed to evaluate Starknet route", error=str(e))

        # 4. Score and Sort
        scored_routes = self._score_routes(routes, preference)
        return scored_routes

    async def _evaluate_aptos(self, amount: float, recipient: str) -> RouteOption:
        client = get_aptos_client()
        # Estimate Gas (Live)
        try:
             gas_token = await client.estimate_transfer_gas(recipient, amount)
        except Exception:
             gas_token = 0.002 # Fallback
             
        fee_usd = gas_token * self.prices["APT"]
        
        return RouteOption(
            chain="APTOS",
            fee_usd=fee_usd,
            eta_seconds=2, # Aptos is fast
            estimated_gas_token=gas_token,
            recommendation_score=0, 
            reason="Sub-second finality"
        )
        
    async def _evaluate_polygon(self, amount: float, recipient: str) -> RouteOption:
        service = PolygonSettlementService()
        # Estimate Gas (Live)
        try:
             gas_token = await service.estimate_transfer_gas()
        except Exception:
             gas_token = 0.01 # Fallback
             
        fee_usd = gas_token * self.prices["MATIC"]
        
        return RouteOption(
            chain="POLYGON",
            fee_usd=fee_usd,
            eta_seconds=300, 
            estimated_gas_token=gas_token,
            recommendation_score=0,
            reason="High liquidity"
        )

    async def _evaluate_starknet(self, amount: float, recipient: str) -> RouteOption:
        client = get_starknet_client()
        # Estimate Gas (Live)
        try:
             # Starknet uses ETH for gas usually
             gas_token = await client.estimate_transfer_fee(recipient, 1, None) # Amount 1 wei for estimation
        except Exception:
             gas_token = 0.00015 # Fallback
        
        fee_usd = gas_token * self.prices["ETH"]
        
        return RouteOption(
            chain="STARKNET",
            fee_usd=fee_usd,
            eta_seconds=600,
            estimated_gas_token=gas_token,
            recommendation_score=0,
            reason="Secure AA & ZK Proven"
        )

    def _score_routes(self, routes: List[RouteOption], preference: str) -> List[RouteOption]:
        """Rank routes based on preference."""
        if not routes:
            return []
            
        # Normalize and Score
        # Simple scoring: Lower Fee is better (if CHEAPEST), Lower Time is better (if FASTEST)
        
        for route in routes:
            score = 0
            if preference == "CHEAPEST":
                # Inverse of fee. + points for low fee.
                # Heuristic: 10 - fee_usd
                score += max(0, 10 - route.fee_usd) * 2
                # Tiny penalty for time
                score -= route.eta_seconds / 600 
            
            elif preference == "FASTEST":
                # Inverse of time.
                score += max(0, 600 - route.eta_seconds) / 60
                # Tiny penalty for fee
                score -= route.fee_usd
            
            route.recommendation_score = round(score, 2)
            
        # Sort descending
        return sorted(routes, key=lambda x: x.recommendation_score, reverse=True)
