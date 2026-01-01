import asyncio
from applications.capp.capp.services.chain_listener import ChainListenerService

async def test_listener():
    print("Testing ChainListenerService...")
    service = ChainListenerService()
    
    # 1. Test Polling (Mock)
    print("1. Testing Poll...")
    await service.poll_events()
    print("✅ Poll finished (check logs for heartbeat)")
    
    # 2. Test Event Handling
    print("2. Testing Event Handle...")
    mock_event = {
        "event": "BridgeWithdrawalInitiated", 
        "tx": "0xaabbcc112233...",
        "args": {"amount": 1000, "user": "0xUser"}
    }
    service.handle_event(mock_event)
    print("✅ Event handled (check logs for 'Event Detected')")

if __name__ == "__main__":
    asyncio.run(test_listener())
