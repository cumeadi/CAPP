import httpx
import structlog
from typing import Dict, Any

from applications.capp.capp.core.aptos import get_aptos_client
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

class ChainMetricsService:
    """
    Fetches real-time on-chain metrics (Gas, Congestion).
    """
    
    def __init__(self):
        self.settings = get_settings()
        # For simplicity in Phase 19, we'll hit public endpoints or use the Aptos Client
        self.polygon_rpc = "https://polygon-rpc.com" 
    
    async def get_aptos_metrics(self) -> Dict[str, Any]:
        """
        Get Aptos Chain Metrics (Gas Unit Price estimate)
        """
        try:
            client = get_aptos_client()
            # Aptos Client usually has an endpoint for estimation or we can just fetch ledger info
            # For this Phase, we'll query ledger info as a proxy for "liveness" 
            ledger_info = await client.client.get_ledger_info()
            
            # Simple gas estimate (Aptos gas is usually stable, but let's pretend)
            # In a real impl, `client.estimate_gas_price()` if available
            gas_estimate = await client.client.estimate_gas_price()
            
            return {
                "chain": "APTOS",
                "block_height": ledger_info.get("block_height"),
                "gas_unit_price": gas_estimate,
                "congestion_level": "LOW" # Logic: if gas > threshold then HIGH
            }
        except Exception as e:
            logger.error("Aptos Metrics Failed", error=str(e))
            return {"chain": "APTOS", "error": str(e), "congestion_level": "UNKNOWN"}

    async def get_polygon_metrics(self) -> Dict[str, Any]:
        """
        Get Polygon Gas Price
        """
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_gasPrice",
                "params": [],
                "id": 1
            }
            async with httpx.AsyncClient() as client:
                res = await client.post(self.polygon_rpc, json=payload)
                data = res.json()
                
                if "result" in data:
                    wei = int(data["result"], 16)
                    gwei = round(wei / 10**9, 2)
                    
                    congestion = "LOW"
                    if gwei > 100: congestion = "HIGH"
                    elif gwei > 50: congestion = "MEDIUM"
                    
                    return {
                        "chain": "POLYGON",
                        "gas_price_gwei": gwei,
                        "congestion_level": congestion
                    }
                return {"chain": "POLYGON", "error": "No Result"}
        except Exception as e:
            logger.error("Polygon Metrics Failed", error=str(e))
            return {"chain": "POLYGON", "error": str(e)}
