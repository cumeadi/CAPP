
import aiohttp
import structlog
from decimal import Decimal
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from applications.capp.capp.models.payments import Chain, BridgeProvider
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

class BridgeQuote(BaseModel):
    """Normalized Bridge Quote"""
    provider: str
    from_chain: Chain
    to_chain: Chain
    from_token: str
    to_token: str
    amount_in: Decimal
    amount_out: Decimal
    fee_usd: Decimal
    gas_cost_usd: Decimal
    estimated_duration_seconds: int
    transaction_request: Optional[Dict[str, Any]] = None # The transaction data to sign

class LiFiBridgeProvider:
    """
    Integration with Li.Fi API for Cross-Chain Aggregation.
    API Docs: https://apidocs.li.fi/
    """
    
    API_URL = "https://li.quest/v1"
    
    # Chain IDs mapping (Mainnet)
    CHAIN_IDS = {
        Chain.BASE: 8453, 
        Chain.ARBITRUM: 42161, 
        Chain.ETHEREUM: 1, 
        Chain.OPTIMISM: 10
    }
    
    # Token Addresses (Mainnet USDC)
    TOKENS = {
        Chain.BASE: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 
        Chain.ARBITRUM: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831" 
    }

    def __init__(self):
        self.settings = get_settings()
        self.logger = logger.bind(service="LiFiBridgeProvider")
        
    async def get_quote(self, from_chain: Chain, to_chain: Chain, from_token: str, amount: Decimal, wallet_address: str) -> Optional[BridgeQuote]:
        """
        Get a quote from Li.Fi
        """
        try:
            from_chain_id = self.CHAIN_IDS.get(from_chain)
            to_chain_id = self.CHAIN_IDS.get(to_chain)
            
            if not from_chain_id or not to_chain_id:
                self.logger.warning("Unsupported chain for Li.Fi", from_chain=from_chain, to_chain=to_chain)
                return None
                
            # Convert amount to Wei/Atomic units (Assuming USDC 6 decimals)
            amount_atomic = int(amount * 1_000_000) 
            
            url = f"{self.API_URL}/quote"
            params = {
                "fromChain": from_chain_id,
                "toChain": to_chain_id,
                "fromToken": from_token,
                "toToken": self.TOKENS.get(to_chain, from_token), # Use mapped token or same address
                "fromAmount": str(amount_atomic),
                "fromAddress": wallet_address,
                "order": "RECOMMENDED"
            }
            
            self.logger.info("Fetching Li.Fi quote", params=params)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error("Li.Fi API Error", status=response.status, error=error_text)
                        return None
                        
                    data = await response.json()
                    
                    # Parse Response
                    # Li.Fi returns detailed route info
                    route = data
                    
                    estimated_gas_usd = Decimal(str(route.get("gasCostUSD", 0) or 0))
                    # Li.Fi fee structure is complex, simplified here
                    # cost = gas + fees
                    
                    return BridgeQuote(
                        provider="Li.Fi",
                        from_chain=from_chain,
                        to_chain=to_chain,
                        from_token=from_token,
                        to_token=params["toToken"],
                        amount_in=amount,
                        amount_out=Decimal(route["estimate"]["toAmount"]) / 1_000_000,
                        fee_usd=Decimal("0.0"), # Li.Fi base fee (often embedded)
                        gas_cost_usd=estimated_gas_usd,
                        estimated_duration_seconds=route["estimate"]["executionDuration"],
                        transaction_request=route.get("transactionRequest")
                    )
                    
        except Exception as e:
            self.logger.error("Failed to fetch Li.Fi quote", error=str(e))
            return None

# Singleton
bridge_provider = LiFiBridgeProvider()
