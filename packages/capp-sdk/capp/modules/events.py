import httpx
from typing import Dict, Any, List, Optional
from ..models import CAPPBaseModel
from .._utils import handle_api_error

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
    def __init__(self, client: httpx.AsyncClient):
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
        res = await self._client.post("/events/subscriptions", json=payload)
        handle_api_error(res)
        return WebhookSubscription(**res.json())

    async def list_subscriptions(self) -> List[WebhookSubscription]:
        """List all active webhook subscriptions."""
        res = await self._client.get("/events/subscriptions")
        handle_api_error(res)
        return [WebhookSubscription(**sub) for sub in res.json()]

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Cancel an active webhook subscription."""
        res = await self._client.delete(f"/events/subscriptions/{subscription_id}")
        handle_api_error(res)
        return True
