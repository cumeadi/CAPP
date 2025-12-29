import asyncio
import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch
import aiohttp

# Manual Mocking to avoid patch issues
import applications.capp.capp.agents.base as base_module
import applications.capp.capp.core.redis as redis_core
import applications.capp.capp.core.aptos as aptos_core
import applications.capp.capp.config.settings as settings_module

# Mock Settings
settings_module.get_settings = MagicMock()
settings_module.get_settings.return_value.GEMINI_API_KEY = "mock"
settings_module.get_settings.return_value.GEMINI_MODEL = "mock"

# Mock Core Dependencies
base_module.get_redis_client = MagicMock(return_value=AsyncMock())
base_module.get_aptos_client = MagicMock(return_value=MagicMock())
redis_core.get_cache = MagicMock(return_value=AsyncMock())
redis_core.get_redis_client = MagicMock(return_value=AsyncMock())
aptos_core.get_aptos_client = MagicMock(return_value=MagicMock())

# Add CAPP root to path
sys.path.append(os.getcwd())

from applications.capp.capp.core.x402_client import X402Client
from applications.capp.capp.core.agent_wallet import AgentWallet
from packages.intelligence.market.analyst import MarketAnalysisAgent

async def verify_x402_process():
    print("🤖 Verifying x402 Autonomous Payment...\n")
    
    # Setup Agent with Wallet
    # Note: MarketAnalysisAgent creates its own wallet in __init__ now
    agent = MarketAnalysisAgent()
    
    # Mock HTTP Client Session
    # We need to mock a specific sequence:
    # Req 1 -> 402 Payment Required
    # Req 2 -> 200 OK (with proof)
    
    mock_response_402 = AsyncMock()
    mock_response_402.status = 402
    mock_response_402.headers = {
        "WWW-Authenticate": "X402 amount=5.00, currency=USDC, address=0xVendor123"
    }
    
    mock_response_200 = AsyncMock()
    mock_response_200.status = 200
    mock_response_200.json.return_value = {"insight": "VOLATILITY_DETECTED", "alpha": "High"}
    
    # Patch aiohttp.ClientSession.get to return sequence
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Side effect: First call returns context manager for 402, second for 200
        mock_get.side_effect = [
            AsyncMock(__aenter__=AsyncMock(return_value=mock_response_402), __aexit__=AsyncMock()),
            AsyncMock(__aenter__=AsyncMock(return_value=mock_response_200), __aexit__=AsyncMock())
        ]
        
        # Log Initial State
        print(f"Initial Balance: {agent.wallet.balance}")
        
        # Execute Fetch
        print(f"\n--- Attempting to fetch premium data from 'http://premium-api.com' ---")
        data = await agent.fetch_premium_insight("http://premium-api.com")
        
        # Verify Results
        print(f"Data Received: {data}")
        print(f"Final Balance: {agent.wallet.balance}")
        
        # Check Assertions
        assert agent.wallet.balance == Decimal("45.00") # 50 - 5
        assert data["insight"] == "VOLATILITY_DETECTED"
        
        print("\n✅ x402 Handshake & Payment Verified!")
        print("1. Agent received 402 challenge.")
        print("2. Agent parsed invoice (5.00 USDC).")
        print("3. Agent paid vendor from Petty Wallet.")
        print("4. Agent retried with proof and got data.")

if __name__ == "__main__":
    asyncio.run(verify_x402_process())
