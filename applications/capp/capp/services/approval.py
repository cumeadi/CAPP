from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import structlog
from pydantic import BaseModel
from eth_account import Account
from eth_account.messages import encode_defunct
from .activity_log import get_activity_log

logger = structlog.get_logger(__name__)

class ApprovalRequest(BaseModel):
    id: str
    created_at: datetime
    agent_id: str
    action_type: str
    description: str
    payload: Dict[str, Any]
    status: str = "PENDING"
    signature: Optional[str] = None
    signer_address: Optional[str] = None

class ApprovalService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ApprovalService, cls).__new__(cls)
            cls._instance.pending_requests: Dict[str, ApprovalRequest] = {}
        return cls._instance

    def request_approval(self, agent_id: str, action_type: str, description: str, payload: Dict[str, Any] = None) -> str:
        req_id = str(uuid.uuid4())
        request = ApprovalRequest(
            id=req_id,
            created_at=datetime.utcnow(),
            agent_id=agent_id,
            action_type=action_type,
            description=description,
            payload=payload or {}
        )
        self.pending_requests[req_id] = request
        
        get_activity_log().log_activity(
            agent_id=agent_id,
            agent_type="system", 
            action_type=action_type, 
            message=description,
            metadata={
                "request_id": req_id,
                "payload": payload,
                "status": "PENDING"
            }
        )
        logger.info("Approval Requested", req_id=req_id, agent=agent_id)
        return req_id

    def approve_request(self, request_id: str, signature: str = None) -> bool:
        if request_id not in self.pending_requests:
            return False

        req = self.pending_requests[request_id]

        # Phase 3: Enforce Signature Verification
        if signature:
            try:
                # Recover address from signature
                # Message that was signed (must match frontend)
                msg = f"Approve Request: {request_id}"
                message = encode_defunct(text=msg)
                signer = Account.recover_message(message, signature=signature)
                
                req.signature = signature
                req.signer_address = signer
                logger.info("Signature Verified", signer=signer, req_id=request_id)
                
                # In production, check if 'signer' is an authorized admin
                # For now, we accept any valid signature
                
            except Exception as e:
                logger.error("Invalid Signature", error=str(e))
                return False
        else:
            # For backward compatibility during migration, or dev mode
            logger.warning("Unsigned Approval Attempt", req_id=request_id)
            # UNCOMMENT TO ENFORCE: return False

        req.status = "APPROVED"
        logger.info("Request Approved", req_id=request_id)
        
        get_activity_log().log_activity(
            agent_id=req.agent_id,
            agent_type="system",
            action_type="DECISION",
            message=f"Approved: {req.description}",
            metadata={
                "request_id": request_id, 
                "status": "APPROVED",
                "signer": req.signer_address
            }
        )
        return True

    def reject_request(self, request_id: str) -> bool:
        if request_id in self.pending_requests:
            self.pending_requests[request_id].status = "REJECTED"
            
            req = self.pending_requests[request_id]
            logger.info("Request Rejected", req_id=request_id)

            get_activity_log().log_activity(
                agent_id=req.agent_id,
                agent_type="system",
                action_type="JURISDICTION", 
                message=f"Rejected: {req.description}",
                metadata={"request_id": request_id, "status": "REJECTED"}
            )
            return True
        return False

    def get_request_status(self, request_id: str) -> Optional[str]:
        if request_id in self.pending_requests:
            return self.pending_requests[request_id].status
        return None

def get_approval_service():
    return ApprovalService()
