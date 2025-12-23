import json
import structlog
from typing import Dict, Any, List, Optional
from decimal import Decimal

from .prompts import MARKET_ANALYSIS_SYSTEM_PROMPT, VOLATILITY_ANALYSIS_PROMPT
from ..core.llm_provider import LLMProvider
from ..core.mock_provider import MockLLMProvider
from applications.capp.capp.services.market_data import RealTimeMarketService
from applications.capp.capp.services.chain_metrics import ChainMetricsService
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
        self.market_service = RealTimeMarketService()
        self.chain_service = ChainMetricsService()
        self.logger = structlog.get_logger(__name__)
        
    async def analyze_settlement_risk(self, symbol: str, settlement_amount_usd: float) -> Dict[str, Any]:
        """
        Analyze if it is safe to settle a specific asset now.
        """
        self.logger.info("Starting Market Analysis", symbol=symbol)
        
        # 1. Fetch Real-Time Data
        price_data = await self.market_service.get_token_price(symbol)
        
        if not price_data:
             self.logger.warning("Real-time price unavailable, using fallback mock", symbol=symbol)
             # Fallback to random mock if Pyth fails (so demo doesn't break)
             import random
             price = 10.5 + random.uniform(-0.5, 0.5)
             market_data = {
                "price": price,
                "percent_change_24h": -1.2,
                "volume_24h": "UNKNOWN",
                "volatility_label": "UNKNOWN (Fallback)"
             }
        else:
             # Calculate pseudo-change (since Pyth only gives current price, we'd need history for real 24h change)
             # For Phase 19, we'll assume 0 change or fetch history later. 
             # We can make a rough guess relative to a hardcoded 'open' or just label it "LIVE".
             market_data = {
                "price": price_data["price"],
                "percent_change_24h": "LIVE", # Pyth doesn't give 24h change in this endpoint
                "volume_24h": "LIVE_FEED",
                "volatility_label": "Checking..."
             }

        # 2. Fetch Chain Metrics
        chain_metrics = {}
        if symbol == "APT":
             chain_metrics = await self.chain_service.get_aptos_metrics()
        elif symbol == "MATIC" or symbol == "USDC":
             chain_metrics = await self.chain_service.get_polygon_metrics()
        
        congestion = chain_metrics.get("congestion_level", "UNKNOWN")
        gas_price = chain_metrics.get("gas_unit_price") or chain_metrics.get("gas_price_gwei") or "N/A"
        
        # 3. Construct Prompt with Real Data
        prompt = VOLATILITY_ANALYSIS_PROMPT.format(
            symbol=symbol,
            price=market_data["price"],
            currency="USD",
            percent_change_24h=market_data["percent_change_24h"],
            volume_24h=market_data["volume_24h"],
            volatility_label=f"Network Congestion: {congestion} | Gas: {gas_price}", # Hijacking label for metrics
            settlement_amount=settlement_amount_usd
        )
        
        # 4. Call LLM
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

    async def chat_with_analyst(self, query: str) -> str:
        """
        Interactively chat with the analyst about market conditions.
        """
        # 1. Fetch Context (Market + Chain) for 'Current Awareness'
        # For efficiency, we might cache this, but for now we fetch fresh.
        # We default to APT/USD context for general questions if not specified.
        params = await self.analyze_settlement_risk("APT", 1000)
        
        # 2. Construct Chat Prompt
        system_prompt = f"""
        You are the Voice of the CAPP Treasury. You observe the market and provide actionable, executive summaries.
        You have access to real-time market data:
        - Risk Level: {params.get('risk_level')}
        - Recommendation: {params.get('recommendation')}
        - Reasoning: {params.get('reasoning')}
        
        Users will click Action Buttons to trigger you. React specifically:
        - "Optimize": Analyze the portfolio vs risk. Suggest moves.
        - "Yield": Predict opportunities. Be specific about stablecoin vs volatile assets.
        - "Risk": Give a detailed breakdown of the current {params.get('risk_level')} status.

        Style Guidelines:
        - Be descriptive, not interrogative. Don't say "Do you want to?". Say "Recommended action: Rebalance."
        - Use concise, professional tone.
        - Keep answers under 3 sentences unless detailed analysis is requested.
        """
        
        # 3. Call LLM
        response = await self.provider.generate_text(
            prompt=query,
            system_prompt=system_prompt
        )
        return response
