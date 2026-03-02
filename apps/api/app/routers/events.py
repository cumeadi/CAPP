import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from typing import List

from applications.capp.capp.core.limiter import limiter
from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/events",
    tags=["events", "webhooks"]
)

@router.post("/subscriptions", response_model=schemas.WebhookSubscriptionResponse)
@limiter.limit("10/minute")
async def create_subscription(
    sub: schemas.WebhookSubscriptionCreate, 
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Subscribe to network events (like corridor fee changes or liquidity drops).
    """
    # In a real system, the agent_id comes from the authenticated principal
    agent_id = "agent_system_default"
    
    threshold_str = json.dumps(sub.threshold) if sub.threshold else "{}"
    
    new_sub = models.WebhookSubscription(
        id=f"sub_{uuid.uuid4().hex[:12]}",
        agent_id=agent_id,
        event_type=sub.event_type,
        corridor=sub.corridor,
        threshold=threshold_str,
        webhook_url=sub.webhook_url,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    
    # Matches response schema expectations
    response_data = new_sub.__dict__.copy()
    response_data["threshold"] = json.loads(new_sub.threshold) if new_sub.threshold else None
    
    return response_data

@router.get("/subscriptions", response_model=List[schemas.WebhookSubscriptionResponse])
@limiter.limit("30/minute")
async def list_subscriptions(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    List all active event subscriptions.
    """
    agent_id = "agent_system_default"
    
    subs = db.query(models.WebhookSubscription).filter(
        models.WebhookSubscription.agent_id == agent_id,
        models.WebhookSubscription.is_active == True
    ).all()
    
    results = []
    for s in subs:
        data = s.__dict__.copy()
        data["threshold"] = json.loads(s.threshold) if s.threshold else None
        results.append(data)
        
    return results

@router.delete("/subscriptions/{subscription_id}")
@limiter.limit("10/minute")
async def cancel_subscription(
    subscription_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Cancel an active webhook subscription.
    """
    sub = db.query(models.WebhookSubscription).filter(
        models.WebhookSubscription.id == subscription_id
    ).first()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    sub.is_active = False
    db.commit()
    
    return {"status": "cancelled", "subscription_id": subscription_id}
