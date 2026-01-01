import httpx
import structlog
from typing import List, Dict, Any, Optional

logger = structlog.get_logger(__name__)

class DefiLlamaService:
    """
    Service to fetch real yield opportunities from DefiLlama.
    Base URL: https://yields.llama.fi
    """
    
    BASE_URL = "https://yields.llama.fi"
    
    async def get_yield_opportunities(self, symbol: str = "USDC", chains: List[str] = ["Arbitrum", "Polygon"]) -> List[Dict[str, Any]]:
        """
        Fetch top yield opportunities for a specific asset on specific chains.
        """
        try:
            url = f"{self.BASE_URL}/pools"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    logger.error("DefiLlama API Error", status=response.status_code)
                    return []
                
                data = response.json()
                if "data" not in data:
                    return []
                
                # Filter Logic
                matches = []
                for pool in data["data"]:
                    # Basic filters: correct symbol, correct chain, decent TVL (>1M)
                    if (
                        pool.get("symbol") == symbol and 
                        pool.get("chain") in chains and 
                        pool.get("tvlUsd", 0) > 1_000_000 and
                        pool.get("apyBase") is not None # Ensure base APY exists
                    ):
                        matches.append({
                            "protocol": pool.get("project"),
                            "chain": pool.get("chain"),
                            "asset": pool.get("symbol"),
                            "apy": pool.get("apy", 0),
                            "tvl": pool.get("tvlUsd"),
                            "risk": "LOW" if pool.get("tvlUsd") > 10_000_000 else "MEDIUM"
                        })
                
                # Sort by APY descending
                matches.sort(key=lambda x: x["apy"], reverse=True)
                
                # Return top 10
                return matches[:10]
                
        except Exception as e:
            logger.error("Failed to fetch DefiLlama yields", error=str(e))
            return []

    async def get_market_status(self) -> Dict[str, Any]:
        """
        Get aggregated market status (Volatility, Top APY).
        Since we don't have a direct VIX API here freely available without keys,
        we will infer 'volatility' based on the spread of yields or just mock it more intelligently 
        until we add a VIX provider. For now, we focus on Real APY.
        """
        opps = await self.get_yield_opportunities()
        top_apy = opps[0]["apy"] if opps else 0
        
        return {
            "volatility": "MEDIUM", # Placeholder until Chainlink integration
            "reasoning": f"Market stable. Top yields found on {opps[0]['chain'] if opps else 'N/A'}.",
            "top_apy": top_apy,
            "active_protocols": list(set([o['protocol'] for o in opps[:3]])) if opps else []
        }
