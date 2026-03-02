import httpx
from typing import List
from ..models import AgentCredential
from .._utils import handle_api_error

class AgentsModule:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        
    async def issue_credential(
        self,
        corridor_allowlist: List[str],
        max_per_tx_usd: float,
        daily_limit_usd: float,
        require_approval_above_usd: float,
        expiry_days: int
    ) -> AgentCredential:
        res = await self._client.post("/agents/credentials", json={
            "corridor_allowlist": corridor_allowlist,
            "max_per_tx_usd": max_per_tx_usd,
            "daily_limit_usd": daily_limit_usd,
            "require_approval_above_usd": require_approval_above_usd,
            "expiry_days": expiry_days
        })
        handle_api_error(res)
        return AgentCredential(**res.json())

    async def delegate(
        self,
        parent_agent_id: str,
        corridor_allowlist: List[str],
        max_per_tx_usd: float,
        daily_limit_usd: float,
        require_approval_above_usd: float,
        expiry_days: int
    ) -> AgentCredential:
        res = await self._client.post(f"/agents/credentials/{parent_agent_id}/delegate", json={
            "corridor_allowlist": corridor_allowlist,
            "max_per_tx_usd": max_per_tx_usd,
        })
        handle_api_error(res)
        return AgentCredential(**res.json())

    async def list_organization_credentials(self, organization_id: str) -> List[AgentCredential]:
        res = await self._client.get(f"/agents/credentials/organization/{organization_id}")
        handle_api_error(res)
        return [AgentCredential(**c) for c in res.json()]
        res = await self._client.get(f"/agents/credentials/organization/{organization_id}")
        handle_api_error(res)
        return [AgentCredential(**c) for c in res.json()]

    async def revoke(self, agent_id: str):
        res = await self._client.delete(f"/agents/credentials/{agent_id}")
        handle_api_error(res)
