import httpx
import structlog
from typing import Dict, Optional, Any

logger = structlog.get_logger(__name__)

class RealTimeMarketService:
    """
    Fetches real-time market prices from Pyth Hermes API.
    """
    
    # Hermes Public Endpoint (For dev/demo)
    BASE_URL = "https://hermes.pyth.network"
    
    # Feed IDs (Beta/Stable mix)
    FEED_IDS = {
        "APT": "03ae4db29ed4ae33d323568895aa00337e658e348b37509f5372ae51f0af00d5",
        "MATIC": "5de33a9112c2b700b8d30b8a3402c103578ccfa2765696471cc672bd5cf6ac52",
        "USDC": "eaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a",
        "BTC": "e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
        "ETH": "ff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace"
    }
    
    async def get_token_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch price for a symbol.
        Returns dict with: price, conf, publish_time
        """
        feed_id = self.FEED_IDS.get(symbol.upper())
        if not feed_id:
            logger.warning(f"No Pyth Feed ID for {symbol}")
            return None
            
        try:
            url = f"{self.BASE_URL}/v2/updates/price/latest"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params={"ids[]": [f"0x{feed_id}"]})
                
                if response.status_code != 200:
                    logger.error("Pyth API Error", status=response.status_code, body=response.text)
                    return None
                    
                data = response.json()
                
                # Parse Pyth Response Structure
                # Response is { "binary": { ... }, "parsed": [ { "id": "...", "price": { "price": "...", "expo": ... } } ] }
                if "parsed" in data and len(data["parsed"]) > 0:
                    price_info = data["parsed"][0]["price"]
                    raw_price = int(price_info["price"])
                    expo = int(price_info["expo"])
                    
                    # Calculate float price: raw * 10^expo
                    real_price = raw_price * (10 ** expo)
                    
                    return {
                        "price": real_price,
                        "raw_price": raw_price,
                        "expo": expo,
                        "publish_time": price_info["publish_time"]
                    }
                    
                return None
                
        except Exception as e:
            logger.error("Failed to fetch Pyth price", error=str(e))
            return None
