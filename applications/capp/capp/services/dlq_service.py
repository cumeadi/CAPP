
import structlog
import traceback
from datetime import datetime
from typing import Dict, Any, List

from applications.capp.capp.models.failed_tasks import FailedTask
from applications.capp.capp.core.redis import get_redis_client, get_cache

logger = structlog.get_logger(__name__)

class DLQService:
    """
    Dead Letter Queue Service.
    Captures failures and manages retries.
    Uses Redis to persist failed tasks (for MVP, ideally DB).
    """
    
    REDIS_PREFIX = "dlq:task:"
    
    def __init__(self):
        self.redis = get_redis_client()
        self.cache = get_cache()

    async def capture_failure(
        self, 
        task_type: str, 
        payload: Dict[str, Any], 
        exception: Exception,
        max_retries: int = 3
    ) -> str:
        """
        Log a failure to the DLQ.
        """
        task = FailedTask(
            task_type=task_type,
            payload=payload,
            error_message=str(exception),
            stack_trace=traceback.format_exc(),
            max_retries=max_retries
        )
        
        # Save to Redis
        key = f"{self.REDIS_PREFIX}{task.task_id}"
        await self.cache.set(key, task.dict())
        
        # Add to index list for retrieval
        await self.redis.lpush("dlq:index", task.task_id)
        
        logger.error("task_moved_to_dlq", task_id=task.task_id, task_type=task_type, error=str(exception))
        return task.task_id

    async def get_failed_tasks(self, limit: int = 50) -> List[FailedTask]:
        """
        Retrieve list of failed tasks.
        """
        # Get IDs from index
        task_ids = await self.redis.lrange("dlq:index", 0, limit - 1)
        tasks = []
        
        for tid in task_ids:
            task_data = await self.cache.get(f"{self.REDIS_PREFIX}{tid}")
            if task_data:
                tasks.append(FailedTask(**task_data))
                
        return tasks

    async def retry_task(self, task_id: str) -> bool:
        """
        Attempt to retry a task. 
        Note: The actual retry logic usually requires invoking the original service handler.
        For MVP, we just mark it as RETRYING.
        """
        key = f"{self.REDIS_PREFIX}{task_id}"
        task_data = await self.cache.get(key)
        
        if not task_data:
            logger.warning("retry_task_not_found", task_id=task_id)
            return False
            
        task = FailedTask(**task_data)
        task.status = "RETRYING"
        task.retry_count += 1
        task.last_retry_at = datetime.utcnow()
        
        await self.cache.set(key, task.dict())
        logger.info("retrying_task", task_id=task_id, attempt=task.retry_count)
        
        # Here we would dispatch to the appropriate handler based on task_type
        # e.g. if task.type == "YIELD_SWEEP": yield_service.execute(task.payload)
        
        return True
