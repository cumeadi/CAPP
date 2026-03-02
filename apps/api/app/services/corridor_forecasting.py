import math
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import CorridorMetricsHistory, PaymentMemoryRecord
from .market_context import market_context

logger = structlog.get_logger(__name__)

class CorridorForecastingService:
    def __init__(self):
        self.lookback_days = 7

    async def predict_corridor_confidence(self, corridor: str) -> Dict[str, Any]:
        """
        Uses historical TimescaleDB metrics + real-time CMC AI context to 
        forecast the reliability of a routing corridor.
        Returns a confidence score between 0.0 and 1.0.
        """
        db = SessionLocal()
        try:
            # 1. Fetch historical volatility
            # In production, this would use TimescaleDB continuous aggregates 
            # e.g., SELECT time_bucket('1 day', timestamp), stddev(avg_fee_pct)
            metrics = db.query(CorridorMetricsHistory).filter(
                CorridorMetricsHistory.corridor == corridor,
                CorridorMetricsHistory.timestamp >= datetime.utcnow() - timedelta(days=self.lookback_days)
            ).order_by(CorridorMetricsHistory.timestamp.desc()).limit(10).all()

            base_confidence = 0.95
            volatility_penalty = 0.0
            
            if metrics:
                # Mock ARIMA standard deviation penalty
                fees = [m.avg_fee_pct for m in metrics if m.avg_fee_pct]
                if len(fees) > 1:
                    mean = sum(fees) / len(fees)
                    variance = sum((f - mean) ** 2 for f in fees) / len(fees)
                    std_dev = math.sqrt(variance)
                    # Higher historical volatility = lower confidence
                    volatility_penalty = min(std_dev * 2.0, 0.3)
            else:
                # No data penalty
                volatility_penalty = 0.15

            # 2. Fetch Real-time Market Stress from CMC AI
            # High global stress (e.g. CPI print day) impacts illiquid corridors 
            market_data = await market_context.get_market_stress_indicator()
            stress_score = market_data.get("stress_score", 0.5)
            
            # Stress penalty is geometric
            stress_penalty = stress_score * 0.2

            recent_failures = db.query(PaymentMemoryRecord).filter(
                PaymentMemoryRecord.corridor == corridor,
                PaymentMemoryRecord.success == False,
                PaymentMemoryRecord.timestamp >= datetime.utcnow() - timedelta(hours=2)
            ).count()
            
            # Additional penalty: -5% confidence for every failure in the last 2 hours
            memory_penalty = min(recent_failures * 0.05, 0.40)

            # 4. Calculate Final Prediction
            final_confidence = max(0.1, base_confidence - volatility_penalty - stress_penalty - memory_penalty)
            
            # Predict how long this score is valid (high volatility & failures = shorter window)
            valid_minutes = 60 if final_confidence > 0.8 else 10

            logger.info(
                "corridor_forecast_generated", 
                corridor=corridor, 
                confidence=round(final_confidence, 2),
                stress=stress_score
            )

            return {
                "corridor": corridor,
                "confidence_score": round(final_confidence, 2),
                "valid_until": (datetime.utcnow() + timedelta(minutes=valid_minutes)).isoformat(),
                "factors": {
                    "historical_volatility": round(volatility_penalty, 2),
                    "market_stress": round(stress_penalty, 2),
                    "recent_failures_penalty": round(memory_penalty, 2)
                }
            }

        except Exception as e:
            logger.error("corridor_forecast_failed", corridor=corridor, error=str(e))
            # Fallback safe score
            return {
                "corridor": corridor,
                "confidence_score": 0.50,
                "valid_until": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
                "error": True
            }
        finally:
            db.close()

corridor_forecaster = CorridorForecastingService()
