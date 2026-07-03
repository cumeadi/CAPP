"""
MOCK Stellar integration — sandbox/development only.

This client returns hardcoded balances and fake transaction hashes.
It is NOT connected to any real Stellar network (mainnet or testnet).

Gated behind ENABLE_MOCK_CHAINS=true.  Calling get_stellar_client() without
that flag set will raise RuntimeError so production can never accidentally
use this stub.
"""

import asyncio
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)


class StellarBridgeClient:
    """Mock Stellar client for sandbox use only."""

    def __init__(self, horizon_url: str = "https://horizon-testnet.stellar.org"):
        self.horizon_url = horizon_url
        self.is_connected = False

    async def connect(self):
        logger.info("stellar_mock_connecting", url=self.horizon_url)
        await asyncio.sleep(0.1)
        self.is_connected = True
        return self

    async def get_balance(self, public_key: str) -> float:
        """Returns a hardcoded mock XLM balance — NOT real."""
        if not self.is_connected:
            await self.connect()
        return 50000.00  # mock testnet value

    async def execute_payment(
        self, recipient: str, amount: float, asset_code: str = "XLM"
    ) -> str:
        """Simulates a Stellar payment — does NOT submit anything on-chain."""
        if not self.is_connected:
            await self.connect()
        logger.info(
            "stellar_mock_payment", recipient=recipient, amount=amount, asset=asset_code
        )
        await asyncio.sleep(0.5)
        import uuid
        return f"xlm_mock_tx_{uuid.uuid4().hex[:16]}"


_stellar_client: Optional[StellarBridgeClient] = None


def get_stellar_client() -> StellarBridgeClient:
    """
    Return the shared mock Stellar client.

    Raises RuntimeError unless ENABLE_MOCK_CHAINS=true is set, so the mock
    can never silently slip into a non-sandbox environment.
    """
    from applications.capp.capp.config.settings import get_settings
    settings = get_settings()
    if not settings.ENABLE_MOCK_CHAINS:
        raise RuntimeError(
            "Stellar client is a mock and is disabled in this environment. "
            "Set ENABLE_MOCK_CHAINS=true to use it in sandbox/dev."
        )

    global _stellar_client
    if _stellar_client is None:
        _stellar_client = StellarBridgeClient()
    return _stellar_client
