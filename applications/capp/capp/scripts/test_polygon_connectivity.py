
import asyncio
import sys
import os

# Path Fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.core.polygon import init_polygon_client, get_polygon_client, PolygonSettlementService

async def test_polygon():
    print("🚀 Testing Polygon Connectivity...")
    
    # 1. Init
    await init_polygon_client()
    
    service = PolygonSettlementService()
    
    # 2. Check Connection
    if not service.w3.is_connected():
        print("❌ Failed to connect to Polygon RPC")
        return

    print(f"✅ Connected to Polygon (Block: {service.w3.eth.block_number})")
    
    # 3. Check Balance (Random Whale Address for verification)
    whale = "0x000000000000000000000000000000000000dead"
    balance = await service.get_account_balance(whale)
    print(f"💰 Balance of {whale}: {balance} MATIC")
    
    # 4. Check USDC
    usdc = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
    usdc_bal = await service.get_token_balance(usdc, whale)
    print(f"💵 USDC Balance: {usdc_bal}")

if __name__ == "__main__":
    asyncio.run(test_polygon())
