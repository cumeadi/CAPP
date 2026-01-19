
import asyncio
import sys
import os

# Fix path to allow importing from applications
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from applications.capp.capp.services.relayer_service import RelayerService

async def test_relayer():
    print("\n--- TEST: RELAYER SERVICE ---")
    
    service = RelayerService()
    
    # Define a mock route (similar to what RoutingService would output)
    mock_route = {
        "bridge_provider": "MockBridge",
        "from_chain": "Aptos",
        "to_chain": "Polygon",
        "token_in": "USDC",
        "token_out": "USDC",
        "amount": 50.0,
        "recipient": "0xRecipient123"
    }

    print(f"🚀 Executing Route: {mock_route['from_chain']} -> {mock_route['to_chain']}")
    
    try:
        result = await service.execute_route(mock_route)
        print(f"✅ Execution Successful")
        print(f"   Tx Hash: {result['tx_hash']}")
        print(f"   Explorer: {result['explorer_url']}")
        
        if result['status'] == "COMPLETED":
            print("✅ Status is COMPLETED")
        else:
            print(f"❌ Status mismatch: {result['status']}")
            
    except Exception as e:
        print(f"❌ Execution Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_relayer())
