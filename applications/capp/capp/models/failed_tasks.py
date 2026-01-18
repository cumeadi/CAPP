
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class FailedTask(BaseModel):
    """
    Model for a task that failed processing and was moved to the Dead Letter Queue.
    """
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    task_type: str # e.g., "YIELD_SWEEP", "PAYMENT_SETTLEMENT"
    payload: Dict[str, Any]
    error_message: str
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None
    
    retry_count: int = 0
    max_retries: int = 3
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_retry_at: Optional[datetime] = None
    
    status: str = "FAILED" # FAILED, RETRYING, RECOVERED, ARCHIVED

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
