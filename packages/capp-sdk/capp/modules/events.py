from typing import Dict, Any, List, Optional
from ..client import CAPPClient
from ..models import CAPPBaseModel

class WebhookSubscriptionCreate(CAPPBaseModel):
    event_type: str
    corridor: str
    webhook_url: str
    threshold: Optional[Dict[str, Any]] = None

class WebhookSubscription(WebhookSubscriptionCreate):
    id: str
    agent_id: str
    is_active: bool
    created_at: str

class EventsModule:
    """Manage Webhook Subscriptions for Corridor and Market Events."""
    def __init__(self, client: CAPPClient):
        self._client = client
        
    async def subscribe(self, event_type: str, corridor: str, webhook_url: str, threshold: Optional[Dict[str, Any]] = None) -> WebhookSubscription:
        """
        Subscribe a webhook URL to receive notifications when specific corridor conditions are met.
        """
        payload = {
            "event_type": event_type,
            "corridor": corridor,
            "webhook_url": webhook_url,
            "threshold": threshold
        }
        res = await self._client._post("/events/subscriptions", json=payload)
        return WebhookSubscription(**res)
        
    async def list_subscriptions(self) -> List[WebhookSubscription]:
        """List all active webhook subscriptions."""
        res = await self._client._get("/events/subscriptions")
        return [WebhookSubscription(**sub) for sub in res]
        
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Cancel an active webhook subscription."""
        await self._client._delete(f"/events/subscriptions/{subscription_id}")
        return True
