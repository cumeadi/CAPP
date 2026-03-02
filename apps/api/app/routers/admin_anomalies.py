from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import schemas, database, models

router = APIRouter(
    prefix="/admin/anomalies",
    tags=["admin"]
)

@router.get("/")
def list_anomalies(
    agent_id: Optional[str] = None,
    unresolved_only: bool = True,
    limit: int = Query(50, le=100),
    db: Session = Depends(database.get_db)
):
    """
    Get a list of security events and anomalous agent behaviors detected on the network. 
    """
    query = db.query(models.AnomalyEvent)
    
    if agent_id:
        query = query.filter(models.AnomalyEvent.agent_id == agent_id)
        
    if unresolved_only:
        query = query.filter(models.AnomalyEvent.resolved == False)
        
    events = query.order_by(models.AnomalyEvent.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp,
            "agent_id": e.agent_id,
            "severity": e.severity,
            "rule_triggered": e.rule_triggered,
            "details": e.details,
            "resolved": e.resolved
        } for e in events
    ]

@router.post("/{anomaly_id}/resolve")
def resolve_anomaly(anomaly_id: int, db: Session = Depends(database.get_db)):
    """Mark an incident as resolved following a security review."""
    event = db.query(models.AnomalyEvent).filter(models.AnomalyEvent.id == anomaly_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Anomaly not found.")
        
    event.resolved = True
    db.commit()
    
    return {"status": "success", "message": f"Anomaly {anomaly_id} resolved."}
