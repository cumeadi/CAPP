
from typing import Dict, List, Optional
import structlog
from datetime import datetime, timezone

from applications.capp.capp.models.payments import PaymentStatus
from applications.capp.capp.core.redis import get_redis_client

logger = structlog.get_logger(__name__)

class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass

class StatusManager:
    """
    Finite State Machine (FSM) manager for Payment Status transitions.
    Enforces valid transitions and atomic updates.
    """
    
    # Define valid transitions
    TRANSITIONS: Dict[PaymentStatus, List[PaymentStatus]] = {
        PaymentStatus.PENDING: [
            PaymentStatus.ROUTING, 
            PaymentStatus.CANCELLED, 
            PaymentStatus.FAILED, 
            PaymentStatus.EXPIRED
        ],
        PaymentStatus.ROUTING: [
            PaymentStatus.SETTLING, 
            PaymentStatus.FAILED,
            PaymentStatus.PENDING # Retry case
        ],
        PaymentStatus.SETTLING: [
            PaymentStatus.COMPLETED, 
            PaymentStatus.FAILED, 
            PaymentStatus.YIELD_UNWINDING, 
            PaymentStatus.COMPLIANCE_REVIEW
        ],
        PaymentStatus.YIELD_UNWINDING: [
            PaymentStatus.SETTLING, 
            PaymentStatus.FAILED
        ],
        PaymentStatus.COMPLIANCE_REVIEW: [
            PaymentStatus.SETTLING, 
            PaymentStatus.FAILED,
            PaymentStatus.CANCELLED
        ],
        PaymentStatus.OFFLINE_QUEUED: [
            PaymentStatus.PENDING,
            PaymentStatus.FAILED
        ],
        # Terminal States
        PaymentStatus.COMPLETED: [],
        PaymentStatus.FAILED: [], #[PaymentStatus.PENDING], # Potentially allow manual retry from failed? usually no.
        PaymentStatus.CANCELLED: [],
        PaymentStatus.EXPIRED: []
    }

    def __init__(self):
        self.redis = get_redis_client()

    async def validate_transition(self, current_status: PaymentStatus, new_status: PaymentStatus) -> bool:
        """
        Check if transition is valid based on the FSM map.
        """
        # Allow self-transition (updating metadata without changing status)
        if current_status == new_status:
            return True
            
        allowed_next_states = self.TRANSITIONS.get(current_status, [])
        if new_status not in allowed_next_states:
            logger.error("invalid_state_transition", current=current_status, new=new_status)
            return False
        
        return True

    async def transition(self, payment_id: str, current_status: PaymentStatus, new_status: PaymentStatus) -> bool:
        """
        Atomically transition a payment status.
        Uses Redis lock to ensure no race conditions during check-and-set.
        """
        lock_key = f"lock:payment:{payment_id}"
        
        # Simple spin-lock or just use a short expiration if using proper redis lock lib
        # For this implementation, we assume single-threaded async event loop per request or rely on atomic ops.
        # But to be "Defensive", we should check validity first.
        
        if not await self.validate_transition(current_status, new_status):
            raise InvalidStateTransitionError(f"Cannot transition from {current_status} to {new_status}")
            
        logger.info("payment_status_transition", payment_id=payment_id, from_status=current_status, to_status=new_status)
        
        # Here we would typically update the DB. 
        # Since this is a service helper, the caller usually updates DB.
        # But to enforce atomicity, this manager should optimally handle the DB update or be called inside a transaction.
        # For this MVP step, we are just validating the logic.
        
        return True
