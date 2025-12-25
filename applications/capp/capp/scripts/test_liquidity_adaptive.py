
import asyncio
import sys
import os
from decimal import Decimal

# Path Fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.agents.liquidity.liquidity_agent import LiquidityAgent, LiquidityConfig
from applications.capp.capp.core.aptos import init_aptos_client
from applications.capp.capp.core.redis import init_redis
from applications.capp.capp.config.settings import get_settings

async def test_adaptive_liquidity():
    print("🚀 Starting Adaptive Liquidity Test...")
    
    # 0. Initialize Core Services
    await init_aptos_client()
    await init_redis()
    
    # 1. Initialize Agent
    config = LiquidityConfig()
    agent = LiquidityAgent(config)
    
    # 2. Setup Low Balance Scenario
    pool_id = "pool_usd_ngn"
    pool = agent.liquidity_pools[pool_id]
    
    print(f"Initial State: {pool.available_liquidity} (Threshold: {agent.strategy.base_buffer})")
    
    # artificially drop liquidity below threshold (50,000)
    pool.available_liquidity = Decimal("10000.00")
    print(f"📉 Simulating Liquidity Crunch: Dropped to {pool.available_liquidity}")
    
    # 3. Trigger Rebalancing
    print("Triggering Rebalance Loop...")
    await agent.rebalance_pools()
    
    # 4. Verify Result
    # rebalance_pools awaits the rebalance (which sleeps 2s)
    # So we should check immediately after
    
    final_balance = pool.available_liquidity
    print(f"📈 Post-Rebalance State: {final_balance}")
    
    if final_balance >= Decimal("50000.00"):
        print("✅ SUCCESS: Auto-Rebalancing restored liquidity to threshold!")
    else:
        print("❌ FAILURE: Liquidity not restored.")
        exit(1)

if __name__ == "__main__":
    asyncio.run(test_adaptive_liquidity())
