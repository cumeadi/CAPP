import httpx
from typing import List, Optional
from ..models import ApprovalRequest
from .._utils import handle_api_error

class ApprovalsModule:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        
    async def list(self, status: str = "pending") -> List[ApprovalRequest]:
        res = await self._client.get("/approvals", params={"status": status})
        handle_api_error(res)
        return [ApprovalRequest(**item) for item in res.json().get("items", [])]

    async def resolve(self, approval_id: str, decision: str, note: Optional[str] = None):
        payload = {"decision": decision}
        if note:
            payload["note"] = note
            
        res = await self._client.post(f"/approvals/{approval_id}/resolve", json=payload)
        handle_api_error(res)
