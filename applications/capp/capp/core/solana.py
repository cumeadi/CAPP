"""
MOCK Solana integration — sandbox/development only.

This client returns hardcoded balances and fake transaction hashes.
It is NOT connected to any real Solana network (mainnet or devnet).

Gated behind ENABLE_MOCK_CHAINS=true.  Calling get_solana_client() without
that flag set will raise RuntimeError so production can never accidentally
use this stub.
"""

import asyncio
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)


class SolanaBridgeClient:
    """Mock Solana client for sandbox use only."""

    def __init__(self, rpc_url: str = "https://api.devnet.solana.com"):
        self.rpc_url = rpc_url
        self.is_connected = False

    async def connect(self):
        logger.info("solana_mock_connecting", rpc=self.rpc_url)
        await asyncio.sleep(0.1)
        self.is_connected = True
        return self

    async def get_balance(self, address: str) -> float:
        """Returns a hardcoded mock SOL balance — NOT real."""
        if not self.is_connected:
            await self.connect()
        return 15000.50  # mock testnet value

    async def execute_transfer(
        self, target_address: str, amount: float, token: Optional[str] = None
    ) -> str:
        """Simulates a SOL/SPL transfer — does NOT submit anything on-chain."""
        if not self.is_connected:
            await self.connect()
        logger.info(
            "solana_mock_transfer", target=target_address, amount=amount, token=token or "SOL"
        )
        await asyncio.sleep(0.4)
        import uuid
        return f"sol_mock_tx_{uuid.uuid4().hex[:16]}"


_solana_client: Optional[SolanaBridgeClient] = None


def get_solana_client() -> SolanaBridgeClient:
    """
    Return the shared mock Solana client.

    Raises RuntimeError unless ENABLE_MOCK_CHAINS=true is set, so the mock
    can never silently slip into a non-sandbox environment.
    """
    from applications.capp.capp.config.settings import get_settings
    settings = get_settings()
    if not settings.ENABLE_MOCK_CHAINS:
        raise RuntimeError(
            "Solana client is a mock and is disabled in this environment. "
            "Set ENABLE_MOCK_CHAINS=true to use it in sandbox/dev."
        )

    global _solana_client
    if _solana_client is None:
        _solana_client = SolanaBridgeClient()
    return _solana_client
