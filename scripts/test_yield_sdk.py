
import asyncio
import sys
import os
from decimal import Decimal

# Fix path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Only import after path is fixed
from applications.capp.capp.services.yield_service import YieldService
from applications.capp.capp.core.redis import init_redis
from applications.capp.capp.core.aptos import init_aptos_client

async def verify_yield_sdk():
    print("\n--- 🏦 CAPP PLATFORM: YIELD SDK VERIFICATION ---")
    
    # Initialize Core Dependencies
    try:
        await init_redis()
        await init_aptos_client()
    except Exception as e:
        print(f"⚠️ Warning during init: {e}")
    
    service = YieldService()
    
    # Client 1: Internal Treasury (Existing behavior)
    # Mocked Hot Balance: 15,000 | Config: Default (20% buffer)
    print("\n1️⃣ Processing Client A: Internal Treasury")
    await service.optimize_wallet("internal_hot_wallet")
    
    # Client 2: Fintech Partner "PayQuick" (New behavior)
    # Mocked Hot Balance: 50,000 | Config: Aggressive (5% buffer)
    print("\n2️⃣ Processing Client B: External Fintech (PayQuick)")
    # Should trigger massive sweep because buffer is small (5% of 50k = 2.5k target) -> Excess 47.5k
    client_config = {"buffer_pct": 0.05, "min_sweep_amount": 1000} 
    await service.optimize_wallet("payquick_wallet_0x123", config=client_config)
    
    # Check Result State
    print("\n--- 📊 FINAL STATE AUDIT ---")
    
    # Internal
    internal_state = await service.get_total_treasury_balance("internal_hot_wallet")
    print(f"Internal Yield Balance: ${internal_state['breakdown']['USDC']['yielding']}")
    
    # External
    external_state = await service.get_total_treasury_balance("payquick_wallet_0x123")
    print(f"PayQuick Yield Balance: ${external_state['breakdown']['USDC']['yielding']}")
    
    # Verification Logic
    # PayQuick started with 0 yield. 
    # Hot: 50,000. Buffer 5% = 2,500. Excess = 47,500.
    # Yield should be 47,500.
    
    payquick_yield = external_state['breakdown']['USDC']['yielding']
    if payquick_yield == 47500.0:
        print("✅ SUCCESS: PayQuick funds correctly optimized!")
    else:
        print(f"❌ FAILURE: PayQuick yield incorrect. Expected 47500.0, got {payquick_yield}")

if __name__ == "__main__":
    asyncio.run(verify_yield_sdk())
