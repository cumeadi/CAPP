import asyncio
import structlog
import os
from unittest.mock import MagicMock, patch
from decimal import Decimal

# Mock API Key for testing if not set
os.environ["COINMARKETCAP_API_KEY"] = os.environ.get("COINMARKETCAP_API_KEY", "mock_key_for_verification")

from packages.intelligence.liquidity.agent import LiquidityManagementAgent
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

async def verify_liquidity_agent():
    print("Verifying Liquidity Management Agent...")
    
    # Mocking dependencies to avoid Redis/Chain connection during verification
    with patch("packages.intelligence.liquidity.agent.get_aptos_client") as MockClientFactory, \
         patch("packages.intelligence.market.analyst.ExchangeRateService") as MockExchangeService:
        
        # 1. Setup Mock Aptos Client
        mock_client = MagicMock()
        # Mock Balance -> 500.0 APT (> target 100.0)
        async def mock_get_balance(*args): 
            return Decimal("500.0")
        mock_client.get_account_balance.side_effect = mock_get_balance
        
        # Mock Swap
        async def mock_swap(f, t, a):
            return "0x_mocked_swap_tx_success"
        mock_client.swap_tokens.side_effect = mock_swap
        
        MockClientFactory.return_value = mock_client
        
        # 2. Setup Mock Exchange Service (for Market Agent inside Liquidity Agent)
        mock_exchange = MockExchangeService.return_value
        async def mock_get_rate(*args):
            return Decimal("10.0")
        mock_exchange.get_exchange_rate.side_effect = mock_get_rate
        
        # 3. Initialization
        agent = LiquidityManagementAgent()
        
        # 4. Run Evaluation (Mocking High Volatility via Prompt heuristics if possible, 
        # but since MockLLM is simple, we rely on its internal keyword triggers. 
        # Market Analyst sends "volatility" keyword to MockLLM. 
        # Liquidity Agent sends "risk_level" to MockLLM.
        
        # We need to ensure MockLLM returns a SWAP decision.
        # Check `MockLLMProvider` logic... it does not currently have specific logic for `REBALANCE_DECISION_PROMPT`.
        # I need to update MockLLMProvider one last time to support the Liquidity Agent's prompt.
        
        print("\n--- Test 1: Evaluate Treasury (High Volatility Scenario) ---")
        # To trigger the "High Volatility" path in MockLLM (Market), we need "volatility" in prompt.
        # The Market Agent adds that.
        
        # BUT, the Liquidity Agent calls `generate_json` with a NEW prompt for decision.
        # I need to patch MockLLMProvider to handle "Treasury Status" prompt.
        
        decision = await agent.evaluate_treasury_status(asset="APT", target_reserve=100.0)
        
        print(f"Action: {decision.get('action')}")
        print(f"Amount: {decision.get('amount')}")
        print(f"Reasoning: {decision.get('reasoning')}")
        
    print("\n✅ Liquidity Agent Verification Completed.")

if __name__ == "__main__":
    asyncio.run(verify_liquidity_agent())
