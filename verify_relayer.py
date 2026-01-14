import asyncio
import structlog
from applications.capp.capp.core.relayer import RelayerService
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

async def verify_relayer():
    logger.info("Starting Relayer Agent Verification...")
    
    # 1. Initialize Clients & Relayer
    from applications.capp.capp.core.aptos import init_aptos_client
    await init_aptos_client()
    
    relayer = RelayerService()
    
    # 2. Mock a Starknet 'TokensLocked' Event
    mock_event = {
        "amount": 10.5, # USD or token amount
        "recipient": "0xMockAptosRecipientAddress",
        "token": "0xStarknetETHToken",
        "tx_hash": "0x123456789abcde"
    }
    
    logger.info("Simulating Starknet Event Detection...", event=mock_event)
    
    # 3. Process Event (Trigger Bridge)
    try:
        release_tx = await relayer.process_event(mock_event)
        
        if release_tx and release_tx.startswith("0x"):
            logger.info("✅ Relayer Successfully Triggered Aptos Release!", tx_hash=release_tx)
        else:
            logger.error("❌ Relayer Failed to Return valid TX Hash")
            
    except Exception as e:
        logger.error("❌ Relayer Verification Failed", error=str(e))

if __name__ == "__main__":
    asyncio.run(verify_relayer())
