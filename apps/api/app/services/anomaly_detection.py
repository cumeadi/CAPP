import json
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, List

from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import AnomalyEvent
from ..schemas import TransactionRequest

logger = structlog.get_logger(__name__)

class AnomalyDetectionService:
    """
    Security Intelligence Agent.
    Monitors incoming transaction streams for testnet abuse, routing loops, 
    and velocity spikes. Flags offending agents for suspension.
    """
    def __init__(self):
        # Configuration for Testnet rules
        self.max_tx_per_minute = 100
        self.max_corridor_switches_per_5m = 30
        
        # In-memory rapid sliding window for extreme spikes (avoid DB hits on DDOS)
        self._velocity_cache: Dict[str, List[datetime]] = {}

    def analyze_transaction(self, agent_id: str, tx_req: TransactionRequest):
        """
        Synchronous non-blocking hook fired on every routing/payment attempt.
        """
        now = datetime.utcnow()
        
        # 1. Update Velocity Cache
        if agent_id not in self._velocity_cache:
            self._velocity_cache[agent_id] = []
            
        # Prune old txs > 1 minute
        self._velocity_cache[agent_id] = [t for t in self._velocity_cache[agent_id] if t > now - timedelta(minutes=1)]
        self._velocity_cache[agent_id].append(now)

        # 2. Check Rule: Velocity Spike
        if len(self._velocity_cache[agent_id]) > self.max_tx_per_minute:
            self._flag_anomaly(
                agent_id=agent_id,
                severity="HIGH",
                rule="VELOCITY_SPIKE",
                details={
                    "tx_count_1m": len(self._velocity_cache[agent_id]),
                    "threshold": self.max_tx_per_minute,
                    "target_corridor": f"{tx_req.from_currency}-{tx_req.to_currency}"
                }
            )

        # 3. Check Rule: Unnatural Micro-Transactions (dust spam)
        if tx_req.amount > 0 and tx_req.amount < 0.01:
             self._flag_anomaly(
                agent_id=agent_id,
                severity="MEDIUM",
                rule="DUST_SPAM",
                details={
                    "amount": float(tx_req.amount),
                    "currency": tx_req.from_currency
                }
            )

    def _flag_anomaly(self, agent_id: str, severity: str, rule: str, details: Dict[str, Any]):
        """Persists the detection and logs securely"""
        db = SessionLocal()
        try:
            event = AnomalyEvent(
                agent_id=agent_id,
                severity=severity,
                rule_triggered=rule,
                details=json.dumps(details)
            )
            db.add(event)
            db.commit()
            
            logger.warn(
                "security_anomaly_detected",
                agent_id=agent_id,
                severity=severity,
                rule=rule,
                details=details
            )
            
            # Action logic: If CRITICAL or multiple HIGHs, we would 
            # ideally flip AgentCredential.is_active = False here.
            
        except Exception as e:
            logger.error("anomaly_logging_failed", error=str(e))
        finally:
            db.close()

anomaly_detector = AnomalyDetectionService()
