from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import deque
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

class ActivityItem(BaseModel):
    id: str
    timestamp: datetime
    agent_id: str
    agent_type: str
    action_type: str  # e.g., "DECISION", "PAYMENT", "ALERT"
    message: str
    metadata: Dict[str, Any] = {}

class ActivityLogService:
    """
    In-memory store for recent agent activities.
    Serves as the 'decision feed' for the frontend.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ActivityLogService, cls).__new__(cls)
            cls._instance.logs = deque(maxlen=100) # Keep last 100 events
        return cls._instance

    def log_activity(self, agent_id: str, agent_type: str, action_type: str, message: str, metadata: Dict[str, Any] = None):
        """
        Record an agent activity.
        """
        import uuid
        item = ActivityItem(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            agent_type=agent_type,
            action_type=action_type,
            message=message,
            metadata=metadata or {}
        )
        self.logs.appendleft(item) # Newest first
        logger.info("Activity Logged", agent=agent_id, action=action_type, msg=message)

    def get_recent_activities(self, limit: int = 20) -> List[Dict]:
        """
        Get recent activities.
        """
        # Convert to dict for JSON response
        return [item.dict() for item in list(self.logs)[:limit]]

# Global instance accessor
def get_activity_log():
    return ActivityLogService()
