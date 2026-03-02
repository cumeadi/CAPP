import structlog
import asyncio
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

class SolanaBridgeClient:
    """
    Mock integration for Solana for the CAPP Sandbox MVP.
    """
    def __init__(self, rpc_url: str = "https://api.devnet.solana.com"):
        self.rpc_url = rpc_url
        self.is_connected = False
        
    async def connect(self):
        logger.info("solana_bridge_connecting", rpc=self.rpc_url)
        await asyncio.sleep(0.1) # Simulate connection time
        self.is_connected = True
        return self
        
    async def get_balance(self, address: str) -> float:
        """Return a mock SOL balance."""
        if not self.is_connected:
             await self.connect()
        # Mock high-liquidity testnet whale
        return 15000.50

    async def execute_transfer(self, target_address: str, amount: float, token: Optional[str] = None) -> str:
        """Simulates native SOL or SPL token transfers on Solana."""
        if not self.is_connected:
             await self.connect()
             
        logger.info("solana_transfer_initiated", target=target_address, amount=amount, token=token or "SOL")
        await asyncio.sleep(0.4) # Fast block times
        
        import uuid
        return f"sol_tx_{uuid.uuid4().hex[:16]}"

# Global lazy mock client
_solana_client = None

def get_solana_client() -> SolanaBridgeClient:
    global _solana_client
    if not _solana_client:
        _solana_client = SolanaBridgeClient()
    return _solana_client
