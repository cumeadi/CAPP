import json
import structlog
from typing import Dict, Any, List, Optional
from decimal import Decimal

from .prompts import MARKET_ANALYSIS_SYSTEM_PROMPT, VOLATILITY_ANALYSIS_PROMPT
from ..core.llm_provider import LLMProvider
from ..core.mock_provider import MockLLMProvider
from applications.capp.capp.services.exchange_rates import ExchangeRateService
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

class MarketAnalysisAgent:
    """
    AI Market Analyst
    
    analyzes market conditions to recommend optimal settlement timing.
    """
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.settings = get_settings()
        self.provider = provider or MockLLMProvider()
        self.exchange_service = ExchangeRateService()
        self.logger = structlog.get_logger(__name__)
        
    async def analyze_settlement_risk(self, symbol: str, settlement_amount_usd: float) -> Dict[str, Any]:
        """
        Analyze if it is safe to settle a specific asset now.
        """
        self.logger.info("Starting Market Analysis", symbol=symbol)
        
        # 1. Fetch Market Data (Real or Mocked via ExchangeService/CMC)
        # Note: ExchangeService currently returns rate. We might need expanded data for AI.
        # For Phase 4, we'll fetch price and simulate volatility data if CMC info is thin,
        # or rely on what we put in _get_rate_from_coinmarketcap if we expanded it.
        # Here, we'll simulate "Market Metrics" for the prompt if we can't get full depth yet.
        
        current_rate = await self.exchange_service.get_exchange_rate(symbol, "USD")
        price = float(current_rate) if current_rate else 0.0
        
        # simulated metrics for the prompt (In a real production app, we'd fetch these from CMC 'quotes' endpoint)
        market_data = {
            "price": price,
            "percent_change_24h": -5.2 if symbol == "APT" else 1.2, # Mock volatility for demo
            "volume_24h": "500M",
            "volatility_label": "HIGH" if symbol == "APT" else "LOW" 
        }
        
        # 2. Construct Prompt
        prompt = VOLATILITY_ANALYSIS_PROMPT.format(
            symbol=symbol,
            price=market_data["price"],
            currency="USD",
            percent_change_24h=market_data["percent_change_24h"],
            volume_24h=market_data["volume_24h"],
            volatility_label=market_data["volatility_label"],
            settlement_amount=settlement_amount_usd
        )
        
        # 3. Call LLM
        try:
            response = await self.provider.generate_json(
                prompt=prompt,
                schema={},
                system_prompt=MARKET_ANALYSIS_SYSTEM_PROMPT
            )
            
            self.logger.info("Market Analysis Completed", recommendation=response.get("recommendation"))
            return response
            
        except Exception as e:
            self.logger.error("AI Analysis failed", error=str(e))
            return {
                "risk_level": "UNKNOWN",
                "recommendation": "PROCEED_WITH_CAUTION",
                "reasoning": "AI Analysis failed, defaulting to caution."
            }
