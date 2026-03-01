import httpx
from typing import Optional, List
from ..models import PaymentResult
from .._utils import handle_api_error

class PaymentsModule:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        
    async def send(
        self, 
        amount: float, 
        from_currency: str, 
        to_currency: str, 
        recipient: str, 
        corridor: str
    ) -> PaymentResult:
        res = await self._client.post("/payments/send", json={
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "recipient": recipient,
            "corridor": corridor
        })
        handle_api_error(res)
        return PaymentResult(**res.json())

    async def get(self, tx_id: str) -> PaymentResult:
        res = await self._client.get(f"/payments/{tx_id}")
        handle_api_error(res)
        return PaymentResult(**res.json())
        
    async def list(self, limit: int = 20, corridor: Optional[str] = None) -> List[PaymentResult]:
        params = {"limit": limit}
        if corridor:
            params["corridor"] = corridor
        res = await self._client.get("/payments", params=params)
        handle_api_error(res)
        return [PaymentResult(**item) for item in res.json().get("items", [])]
