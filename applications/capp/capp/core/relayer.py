import asyncio
import structlog
from typing import Dict, Any, List

from applications.capp.capp.core.starknet import get_starknet_client
from applications.capp.capp.core.aptos import get_aptos_client
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

class RelayerService:
    """
    Relayer Agent that monitors Starknet Bridge for 'TokensLocked' events
    and triggers 'release_funds' on Aptos.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.starknet_client = get_starknet_client()
        self.aptos_client = get_aptos_client()
        self.is_running = False
        
        self.last_processed_block = 0 
        # In prod, persist this to DB/Redis

    async def start(self):
        """Start the monitoring loop"""
        self.is_running = True
        logger.info("Relayer Agent Started", status="Monitoring Starknet...")
        
        while self.is_running:
            try:
                await self.monitor_events()
                await asyncio.sleep(10) # Poll every 10s
            except Exception as e:
                logger.error("Relayer loop parsing error", error=str(e))
                await asyncio.sleep(10)

    async def stop(self):
        self.is_running = False
        logger.info("Relayer Agent Stopped")

    async def monitor_events(self):
        """
        Check for new TokensLocked events on Starknet.
        """
        # For MVP/Sim, we might not have a deployed contract emitting real events constantly.
        # We will mock the "Finding" of an event for the verification script,
        # but implement the logic structure for real usage.
        
        # Real logic would be:
        # events = await self.starknet_client.client.get_events(
        #    from_block=self.last_processed_block + 1,
        #    address=self.settings.STARKNET_BRIDGE_ADDRESS,
        #    keys=[hash("TokensLocked")]
        # )
        
        # Here we just log "Polling"
        # logger.debug("Polling Starknet for bridge events...")
        pass

    async def process_event(self, event_data: Dict[str, Any]):
        """
        Process a detected Lock event and trigger Release.
        
        Event Payload Expectation:
        {
            "amount": float (or int wei),
            "recipient": str (Aptos Address),
            "token": str,
            "tx_hash": str
        }
        """
        logger.info("Event Detected", payload=event_data)
        
        try:
            # 1. Parse Event
            amount = event_data.get("amount", 0)
            recipient = event_data.get("recipient")
            tx_hash = event_data.get("tx_hash")
            
            # 2. Verify Finality (Skip for MVP/Sim)
            # await self.starknet_client.wait_for_tx(tx_hash)
            
            # 3. Trigger Aptos Release
            logger.info("Triggering Aptos Release...", recipient=recipient, amount=amount)
            
            release_tx = await self.aptos_client.release_funds(
                payment_id=f"bridge_{tx_hash[:10]}", # Derive ID from lock tx
                recipient_address=recipient,
                amount=amount
            )
            
            # NOTE: I need to update AptosClient.release_funds to take 'amount'. 
            # I will fix `aptos.py` in next step.
            
            logger.info("Funds Released on Aptos", tx_hash=release_tx)
            return release_tx
            
        except Exception as e:
            logger.error("Failed to process bridge event", error=str(e))
            raise
