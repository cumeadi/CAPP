import httpx
from typing import List
from ..models import RouteAnalysisResult, FXRate
from .._utils import handle_api_error

class RoutingModule:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        
    async def analyze(
        self, 
        amount: float, 
        from_currency: str, 
        to_currency: str, 
        corridor: str
    ) -> List[RouteAnalysisResult]:
        res = await self._client.post("/routing/analyze", json={
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "corridor": corridor
        })
        handle_api_error(res)
        data = res.json()
        # Returning list to match the spec `routes[0].chain`
        return [RouteAnalysisResult(**item) for item in data.get("routes", [])]

    async def get_fx_rate(self, pair: str) -> FXRate:
        res = await self._client.get("/routing/fx", params={"pair": pair})
        handle_api_error(res)
        return FXRate(**res.json())
