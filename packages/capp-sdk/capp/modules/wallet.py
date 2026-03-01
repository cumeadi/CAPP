import httpx
from typing import Optional
from ..models import Balances
from .._utils import handle_api_error

class WalletModule:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        
    async def get_balance(
        self, 
        chain: Optional[str] = None, 
        currency: Optional[str] = None
    ) -> Balances:
        params = {}
        if chain:
            params["chain"] = chain
        if currency:
            params["currency"] = currency
            
        res = await self._client.get("/wallet/balances", params=params)
        handle_api_error(res)
        return Balances(**res.json())
