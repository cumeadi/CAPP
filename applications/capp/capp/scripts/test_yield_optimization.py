
import asyncio
import sys
import os
from decimal import Decimal
import structlog
from typing import List

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.agents.defi.yield_agent import YieldAgent, YieldAgentConfig, YieldStrategy
from applications.capp.capp.models.payments import Chain
from applications.capp.capp.core.aptos import init_aptos_client
from applications.capp.capp.core.redis import init_redis

# Configure logging
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
)
logger = structlog.get_logger()

async def test_yield_optimization_flow():
    """
    Test the Yield Optimization Flow:
    1. Detect Idle Liquidity on Arbitrum.
    2. Supply to Aave V3.
    """
    logger.info("Starting Yield Optimization Verification")
    
    # 0. Initialize Clients
    await init_aptos_client()
    await init_redis()
    
    # 1. Configure Agent
    config = YieldAgentConfig(
        strategies=[
            YieldStrategy(
                name="Arbitrum Yield",
                protocol="AAVE_V3",
                asset="USDC",
                target_chain=Chain.ARBITRUM,
                min_idle_amount=Decimal("1000.00")
            )
        ]
    )
    
    agent = YieldAgent(config)
    
    # 2. Trigger Optimization (Single Run)
    # The Mock Balance in `_get_balance` is hardcoded to 2500 for Arbitrum.
    # Min idle is 1000.
    # Expected: Supply 1500 to Aave.
    
    logger.info("Running Optimization Cycle...")
    await agent.check_and_optimize()
    
    # In a real test we would assert the calls, here we rely on logs from the Mock Executor.
    print("\n--- Verification Summary ---")
    print("Agent ran optimization cycle.")
    print("Check logs for 'DeFi: Supplying to Aave V3' with amount 1500.00")
    print("----------------------------\n")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_yield_optimization_flow())
