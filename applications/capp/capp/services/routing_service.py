
from decimal import Decimal
from typing import List, Optional
import structlog
from pydantic import BaseModel

from applications.capp.capp.services.adapter_registry import AdapterRegistry
from applications.capp.capp.adapters.mock_rails import create_cheap_rail, create_fast_rail
from applications.capp.capp.models.payments import PaymentRoute, PaymentPreferences, Country, Currency

logger = structlog.get_logger(__name__)

class RoutingService:
    """
    Intelligent Routing Engine.
    Selects the best payment rail based on user preferences.
    """
    
    def __init__(self):
        self.registry = AdapterRegistry()
        
        # Auto-register mocks for demonstration/testing
        # (In prod, this would be done by a bootstrapped config)
        if not self.registry.get_payment_rail("FastRail"):
            logger.info("registering_mock_rail", name="FastRail")
            self.registry.register_payment_rail(create_fast_rail())
            
        if not self.registry.get_payment_rail("CheapRail"):
            logger.info("registering_mock_rail", name="CheapRail")
            self.registry.register_payment_rail(create_cheap_rail())

    async def calculate_best_route(
        self, 
        amount: Decimal, 
        currency: str, 
        destination: str,
        preferences: Optional[PaymentPreferences] = None
    ) -> List[dict]:
        """
        Query all rails, score results, and return the best route.
        """
        if preferences is None:
            preferences = PaymentPreferences() # Default: prioritize cost
            
        rails = self.registry.get_all_payment_rails()
        quotes = []
        
        logger.info("routing_calculation_started", amount=str(amount), currency=currency, rails_count=len(rails))
        
        for rail in rails:
            try:
                # Ask rail for quote
                quote = await rail.quote_transfer(currency, amount, destination)
                
                # Convert to internal Route object (simplified for this logic)
                # In real system, we'd map fee/time to PaymentRoute model
                score = self._calculate_score(quote, preferences)
                quote["score"] = score
                quotes.append(quote)
                
                logger.info("quote_received", rail=rail.config.name, score=score)
            except Exception as e:
                logger.warning("quote_failed", rail=rail.config.name, error=str(e))
                
        if not quotes:
            return []
            
        # Sort by score (higher is better)
        quotes.sort(key=lambda x: x["score"], reverse=True)
        
        return quotes

    def _calculate_score(self, quote: dict, prefs: PaymentPreferences) -> float:
        """
        Score a quote from 0.0 to 1.0 based on preferences.
        """
        # Normalize Cost (Lower is better)
        # Normalize Speed (Lower is better)
        
        # Simplified linear scoring
        fee = quote["fee"]
        time_mins = quote["estimated_time_minutes"]
        
        # We arbitarily normalize: 
        # Max acceptable fee = 5% of amount? 
        # Max acceptable time = 24 hours (1440 mins)
        
        amount = quote["amount"]
        if amount == 0: return 0.0
        
        # Stricter penalties
        # Fee: 0 score if > 10%
        # Time: 0 score if > 120 mins (2 hours)
        
        fee_score = max(0.0, 1.0 - (fee / (amount * 0.1))) 
        time_score = max(0.0, 1.0 - (time_mins / 120.0))
        
        weight_cost = 0.8 if prefs.prioritize_cost else 0.2
        weight_speed = 0.8 if prefs.prioritize_speed else 0.2
        
        # Reliability weight could be added from adapter config metadata
        
        total_score = (fee_score * weight_cost) + (time_score * weight_speed)
        return total_score
