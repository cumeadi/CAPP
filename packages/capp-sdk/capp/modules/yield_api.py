import httpx
from typing import Optional, Dict, Any
from .._utils import handle_api_error

class YieldModule:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def get_balance(self, wallet_address: str) -> Dict[str, Any]:
        res = await self._client.get(f"/yield/balance/{wallet_address}")
        handle_api_error(res)
        return res.json()
        
    async def optimize(
        self, 
        wallet_address: str, 
        min_sweep_amount: Optional[float] = None, 
        buffer_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        payload = {"wallet_address": wallet_address}
        if min_sweep_amount is not None:
            payload["min_sweep_amount"] = min_sweep_amount
        if buffer_pct is not None:
            payload["buffer_pct"] = buffer_pct
            
        res = await self._client.post("/yield/optimize", json=payload)
        handle_api_error(res)
        return res.json()
