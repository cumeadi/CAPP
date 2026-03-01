import httpx
from typing import Optional
from .modules.payments import PaymentsModule
from .modules.routing import RoutingModule
from .modules.wallet import WalletModule
from .modules.corridors import CorridorsModule
from .modules.agents import AgentsModule
from .modules.approvals import ApprovalsModule

class CAPPClient:
    def __init__(
        self, 
        api_key: str, 
        agent_credential: Optional[str] = None, 
        sandbox: bool = False,
        timeout: float = 30.0
    ):
        self.api_key = api_key
        self.agent_credential = agent_credential
        self.sandbox = sandbox
        
        base_url = "http://localhost:8000/v1" if sandbox else "https://api.canza.io/v1"
        if sandbox and not api_key.startswith("sk_test_"):
            import logging
            logging.warning("Using sandbox=True with a non-test API key. This may fail.")
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "capp-sdk-python/0.1.0"
        }
        if agent_credential:
            headers["X-Agent-Credential"] = agent_credential
            
        self._http_client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout
        )
        
        self.payments = PaymentsModule(self._http_client)
        self.routing = RoutingModule(self._http_client)
        self.wallet = WalletModule(self._http_client)
        self.corridors = CorridorsModule(self._http_client)
        self.agents = AgentsModule(self._http_client)
        self.approvals = ApprovalsModule(self._http_client)

    async def close(self):
        await self._http_client.aclose()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
