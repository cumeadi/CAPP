
import asyncio
import sys
import os
from decimal import Decimal

# Fix path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from applications.capp.capp.services.billing_service import BillingService
from applications.capp.capp.services.relayer_service import RelayerService
from applications.capp.capp.core.redis import init_redis
from applications.capp.capp.core.aptos import init_aptos_client

# Disable Chaos for specific billing test
os.environ["CHAOS_ENABLED"] = "false"

async def test_billing():
    print("\n--- 💳 CAPP RELAYER: BILLING SYSTEM TEST ---")
    
    # Init Deps
    try:
        await init_redis()
        await init_aptos_client()
    except Exception:
        pass # Ignore mock init errors
        
    billing = BillingService.get_instance()
    relayer = RelayerService()
    
    # 1. Setup Accounts
    print("\nCreating Accounts...")
    broke_acc = billing.create_account("Broke Startups Inc.", initial_balance=0.0)
    rich_acc = billing.create_account("Big Money VC", initial_balance=50.0)
    
    broke_key = billing.create_api_key(broke_acc.account_id)
    rich_key = billing.create_api_key(rich_acc.account_id)
    
    route = {
        "bridge_provider": "MockBridge",
        "from_chain": "Aptos",
        "to_chain": "Polygon",
        "token_in": "USDC",
        "amount": 100.0,
        "recipient": "0xTarget"
    }
    
    # 2. Test: Missing Key
    print("\n--- TEST CASE 1: Missing API Key ---")
    try:
        await relayer.execute_route(route)
        print("❌ FAILED: Should have raised ValueError")
    except ValueError as e:
        print(f"✅ PASSED: Captured error -> {e}")

    # 3. Test: Insufficient Funds
    print("\n--- TEST CASE 2: Insufficient Funds ---")
    try:
        await relayer.execute_route(route, api_key=broke_key)
        print("❌ FAILED: Should have blocked for funds")
    except ValueError as e:
        print(f"✅ PASSED: Captured error -> {e}")
        
    # 4. Test: Success
    print("\n--- TEST CASE 3: Successful Payment ---")
    try:
        res = await relayer.execute_route(route, api_key=rich_key)
        print(f"✅ PASSED: Payment executed. Fee charged: ${res['fee_charged']}")
        
        # Verify Deduction
        if rich_acc.balance_usd == Decimal("49.50"):
            print(f"✅ PASSED: Balance correctly deducted (50.00 -> {rich_acc.balance_usd})")
        else:
            print(f"❌ FAILED: Balance incorrect: {rich_acc.balance_usd}")
            
    except Exception as e:
        print(f"❌ FAILED: Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_billing())
