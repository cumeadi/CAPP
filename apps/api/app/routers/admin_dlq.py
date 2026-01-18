
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import structlog

from applications.capp.capp.services.dlq_service import DLQService
from applications.capp.capp.models.failed_tasks import FailedTask

router = APIRouter(
    prefix="/admin/dlq",
    tags=["admin", "dlq"]
)

logger = structlog.get_logger(__name__)

@router.get("/tasks", response_model=List[FailedTask])
async def get_failed_tasks(limit: int = 50):
    """
    Get list of failed tasks from the Dead Letter Queue.
    """
    dlq = DLQService()
    tasks = await dlq.get_failed_tasks(limit)
    return tasks

@router.post("/retry/{task_id}")
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    """
    Trigger a retry for a specific task.
    """
    dlq = DLQService()
    
    # We run retry in background to avoid blocking
    background_tasks.add_task(dlq.retry_task, task_id)
    
    return {"status": "Retry Initiated", "task_id": task_id}
