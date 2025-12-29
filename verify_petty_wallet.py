import asyncio
import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock

# Add CAPP root to path
sys.path.append(os.getcwd())

# Mock dependencies
# sys.modules["applications.capp.capp.core.aptos"] = MagicMock()
# sys.modules["applications.capp.capp.core.redis"] = MagicMock()
# sys.modules["applications.capp.capp.services.metrics"] = MagicMock()

# Manual Mocking to avoid patch issues
import applications.capp.capp.agents.base as base_module
import applications.capp.capp.core.redis as redis_core
import applications.capp.capp.services.metrics as metrics_module
import applications.capp.capp.core.aptos as aptos_core
import applications.capp.capp.config.settings as settings_module

# Mock Settings
settings_module.get_settings = MagicMock()
settings_module.get_settings.return_value.GEMINI_API_KEY = "mock"

# Mock Base Agent Dependencies
base_module.get_redis_client = MagicMock(return_value=AsyncMock())
base_module.get_aptos_client = MagicMock(return_value=MagicMock())

# Mock Core Dependencies (for Metrics etc)
redis_core.get_cache = MagicMock(return_value=AsyncMock())
redis_core.get_redis_client = MagicMock(return_value=AsyncMock())
aptos_core.get_aptos_client = MagicMock(return_value=MagicMock())


from applications.capp.capp.agents.base import BasePaymentAgent, AgentConfig
from applications.capp.capp.core.agent_wallet import AgentWallet
from applications.capp.capp.models.payments import CrossBorderPayment, PaymentResult

# Mock implementation of abstract agent
class TestAgent(BasePaymentAgent):
    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        pass
    async def validate_payment(self, payment: CrossBorderPayment) -> bool:
        return True

async def verify_petty_wallet():
    print("💰 Verifying Agent Petty Wallet...\n")
    
    # 1. Initialize Agent
    config = AgentConfig(agent_id="test_agent", agent_type="TEST")
    agent = TestAgent(config)
    
    # Verify Initial Deposit
    print(f"Initial Balance: {agent.wallet.balance} {agent.wallet.currency}")
    assert agent.wallet.balance == Decimal("100.00")
    print("✅ Wallet Initialization & Deposit Passed")
    
    # 2. Spend within limits (Limit $50, Spend $5)
    print("\n--- Test 1: Spend $5 (Allowed) ---")
    success = await agent.pay_petty_cash(Decimal("5.00"), "Vendor A", "Data Feed")
    print(f"Payment Status: {success}")
    assert success == True
    assert agent.wallet.balance == Decimal("95.00")
    print("✅ Allowed Spend Passed")
    
    # 3. Spend exceeding daily limit (Limit $50, Spent $5, Remaining $45. Try spend $46)
    print("\n--- Test 2: Spend $46 (Should Fail - Daily Limit) ---")
    success = await agent.pay_petty_cash(Decimal("46.00"), "Vendor B", "Expensive Feed")
    print(f"Payment Status: {success}")
    assert success == False
    assert agent.wallet.balance == Decimal("95.00") # Balance shouldn't change
    print("✅ Budget Limit Enforcement Passed")
    
    # 4. Spend within remaining budget (Try spend $40)
    print("\n--- Test 3: Spend $40 (Allowed - Inside remaining) ---")
    success = await agent.pay_petty_cash(Decimal("40.00"), "Vendor C", "Ok Feed")
    print(f"Payment Status: {success}")
    assert success == True
    assert agent.wallet.balance == Decimal("55.00")
    print("✅ Sequential Spend Passed")
    
    print("\n🎉 Petty Wallet Verification Complete!")

if __name__ == "__main__":
    asyncio.run(verify_petty_wallet())
