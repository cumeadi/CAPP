import asyncio
import json
import httpx
import structlog
from datetime import datetime

from applications.capp.capp.core.redis import get_redis_client
from ..database import SessionLocal
from ..models import WebhookSubscription

logger = structlog.get_logger(__name__)

class WebhookDispatcherService:
    def __init__(self):
        self.redis = get_redis_client()
        self.is_running = False
        self.http_client = httpx.AsyncClient(timeout=5.0)

    async def start_listening(self):
        self.is_running = True
        logger.info("webhook_dispatcher_started")
        
        # In a real cluster, this would connect to Kafka (topic: corridor.events)
        # For this prototype, we simulate a listening loop reading from a mock Redis stream or queue
        while self.is_running:
            try:
                # Simulated poll for events
                # In production: await kafka_consumer.get_message()
                await asyncio.sleep(15) 
                
                # Mock event simulating a fee spike detected by the routing engine
                mock_event = {
                    "event_type": "corridor.fee_spike",
                    "corridor": "NG-KE",
                    "data": {
                        "current_fee_pct": 1.8,
                        "previous_fee_pct": 1.2,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                
                await self.process_event(mock_event)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("webhook_dispatcher_error", error=str(e))
                await asyncio.sleep(5)
                
    async def process_event(self, event: dict):
        event_type = event.get("event_type")
        corridor = event.get("corridor")
        
        # Load active subscriptions for this event type and corridor
        db = SessionLocal()
        try:
            subs = db.query(WebhookSubscription).filter(
                WebhookSubscription.event_type == event_type,
                WebhookSubscription.corridor == corridor,
                WebhookSubscription.is_active == True
            ).all()
            
            for sub in subs:
                await self.evaluate_and_dispatch(sub, event)
                
        finally:
            db.close()
            
    async def evaluate_and_dispatch(self, sub: WebhookSubscription, event: dict):
        # 1. Evaluate thresholds
        thresholds = json.loads(sub.threshold) if sub.threshold else {}
        should_fire = True
        
        if event.get("event_type") == "corridor.fee_spike":
            target_fee = thresholds.get("fee_pct", 0)
            actual_fee = event.get("data", {}).get("current_fee_pct", 0)
            if actual_fee < target_fee:
                should_fire = False
                
        # 2. Fire webhook if conditions met
        if should_fire:
            logger.info("firing_webhook", sub_id=sub.id, target=sub.webhook_url)
            try:
                payload = {
                    "subscription_id": sub.id,
                    "event": event
                }
                # Fire and forget (in reality, we'd use a task queue with retries)
                asyncio.create_task(self._post_webhook(sub.webhook_url, payload))
            except Exception as e:
                 logger.error("webhook_dispatch_failed", sub_id=sub.id, error=str(e))

    async def _post_webhook(self, url: str, payload: dict):
        try:
             res = await self.http_client.post(url, json=payload)
             res.raise_for_status()
             logger.debug("webhook_delivered", url=url, status=res.status_code)
        except Exception as e:
             logger.warning("webhook_delivery_failure", url=url, error=str(e))

    async def stop(self):
        self.is_running = False
        await self.http_client.aclose()
