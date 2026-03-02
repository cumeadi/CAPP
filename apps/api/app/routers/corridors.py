from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta

from .. import schemas, database, models
from ..services.market_context import market_context

router = APIRouter(
    prefix="/corridors",
    tags=["corridors"]
)

@router.get("/feed", response_model=schemas.CorridorFeedResponse)
async def get_corridor_feed(
    corridor: str,
    lookback_days: int = Query(7, ge=1, le=30),
    db: Session = Depends(database.get_db)
):
    """
    Get a real-time data hose of the liquidity and fee conditions within a specific CAPP network corridor.
    Includes AI-generated macro context from the intelligence layer.
    """
    try:
        # 1. Fetch historical metrics from TimescaleDB table
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        metrics = db.query(models.CorridorMetricsHistory)\
            .filter(models.CorridorMetricsHistory.corridor == corridor)\
            .filter(models.CorridorMetricsHistory.timestamp >= cutoff_date)\
            .order_by(models.CorridorMetricsHistory.timestamp.desc())\
            .limit(100)\
            .all()
            
        # 2. Add AI Context 
        market_data = await market_context.get_market_stress_indicator()
        macro_insight = None
        current_health = "UNKNOWN"
        
        if metrics:
            recent_success = metrics[0].success_rate
            if recent_success > 0.95:
                current_health = "HEALTHY"
            elif recent_success > 0.80:
                current_health = "DEGRADED"
            else:
                current_health = "UNSTABLE"
                
            # Synthesize basic insight
            if market_data.get("stress_score", 0.5) > 0.7:
                macro_insight = "High market stress detected. Expect elevated fees and wider spreads."
            elif current_health == "HEALTHY":
                macro_insight = "Corridor liquidity is stable. Favorable execution environment."
        else:
            current_health = "NO_DATA"
            macro_insight = "Insufficient historical data for this corridor."

        metrics_records = [
            schemas.CorridorMetricRecord(
                timestamp=m.timestamp,
                liquidity_depth=m.liquidity_depth,
                avg_fee_pct=m.avg_fee_pct,
                success_rate=m.success_rate,
                tx_volume_usd=m.tx_volume_usd
            ) for m in metrics
        ]
        
        return schemas.CorridorFeedResponse(
            corridor=corridor,
            current_health=current_health,
            macro_context=macro_insight,
            metrics=metrics_records
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
