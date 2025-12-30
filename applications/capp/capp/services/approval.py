from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import structlog
from pydantic import BaseModel
from .activity_log import get_activity_log

logger = structlog.get_logger(__name__)

class ApprovalRequest(BaseModel):
    id: str
    created_at: datetime
    agent_id: str
    action_type: str
    description: str
    payload: Dict[str, Any]
    status: str = "PENDING" # PENDING, APPROVED, REJECTED, EXECUTED

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
        
        # Log to Activity Feed so it shows up in UI
        # We use action_type='APPROVAL' to trigger the Permission Card in the UI
        get_activity_log().log_activity(
            agent_id=agent_id,
            agent_type="system", 
            action_type="APPROVAL", 
            message=description,
            metadata={
                "request_id": req_id,
                "payload": payload,
                "status": "PENDING"
            }
        )
        logger.info("Approval Requested", req_id=req_id, agent=agent_id)
        return req_id

    def approve_request(self, request_id: str) -> bool:
        if request_id in self.pending_requests:
            self.pending_requests[request_id].status = "APPROVED"
            
            req = self.pending_requests[request_id]
            logger.info("Request Approved", req_id=request_id)
            
            # Log update to feed
            get_activity_log().log_activity(
                agent_id=req.agent_id,
                agent_type="system",
                action_type="DECISION",
                message=f"Approved: {req.description}",
                metadata={"request_id": request_id, "status": "APPROVED"}
            )
            return True
        return False

    def reject_request(self, request_id: str) -> bool:
        if request_id in self.pending_requests:
            self.pending_requests[request_id].status = "REJECTED"
            
            req = self.pending_requests[request_id]
            logger.info("Request Rejected", req_id=request_id)

            # Log update to feed
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
