"""
Task management for financial orchestration

This module provides task distribution and management capabilities
for coordinating work across multiple agents.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from collections import defaultdict, deque

import structlog
from pydantic import BaseModel, Field

from packages.core.agents.base import BaseFinancialAgent, ProcessingResult
from packages.core.agents.financial_base import FinancialTransaction


logger = structlog.get_logger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """Task definition"""
    task_id: str
    transaction: FinancialTransaction
    agent_type: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agent_id: Optional[str] = None
    result: Optional[ProcessingResult] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskManager:
    """
    Task manager for distributing and managing tasks across agents
    
    This class provides capabilities for:
    - Task queuing and prioritization
    - Task distribution to agents
    - Task monitoring and tracking
    - Load balancing and optimization
    """
    
    def __init__(self, max_concurrent: int = 100):
        self.max_concurrent = max_concurrent
        self.logger = structlog.get_logger(__name__)
        
        # Task queues by priority
        self._task_queues: Dict[TaskPriority, deque] = {
            TaskPriority.LOW: deque(),
            TaskPriority.NORMAL: deque(),
            TaskPriority.HIGH: deque(),
            TaskPriority.CRITICAL: deque()
        }
        
        # Active tasks
        self._active_tasks: Dict[str, Task] = {}
        self._agent_tasks: Dict[str, List[str]] = defaultdict(list)
        
        # Task processing semaphore
        self._task_semaphore = asyncio.Semaphore(max_concurrent)
        
        # Task processing loop
        self._processing_task: Optional[asyncio.Task] = None
        self._running = False
        
        self.logger.info("Task manager initialized", max_concurrent=max_concurrent)
    
    async def start(self) -> None:
        """Start the task manager"""
        if self._running:
            return
        
        self._running = True
        self._processing_task = asyncio.create_task(self._process_tasks_loop())
        self.logger.info("Task manager started")
    
    async def stop(self) -> None:
        """Stop the task manager"""
        if not self._running:
            return
        
        self._running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Task manager stopped")
    
    async def submit_task(
        self, 
        transaction: FinancialTransaction,
        agent_type: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit a task for processing
        
        Args:
            transaction: The transaction to process
            agent_type: Type of agent to process the task
            priority: Task priority
            metadata: Additional task metadata
            
        Returns:
            Task ID
        """
        try:
            import uuid
            task_id = str(uuid.uuid4())
            
            task = Task(
                task_id=task_id,
                transaction=transaction,
                agent_type=agent_type,
                priority=priority,
                metadata=metadata or {}
            )
            
            # Add to appropriate queue
            self._task_queues[priority].append(task)
            
            self.logger.info(
                "Task submitted",
                task_id=task_id,
                agent_type=agent_type,
                priority=priority
            )
            
            return task_id
            
        except Exception as e:
            self.logger.error("Failed to submit task", error=str(e))
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get task status by ID"""
        try:
            # Check active tasks first
            if task_id in self._active_tasks:
                return self._active_tasks[task_id]
            
            # Check queues
            for priority, queue in self._task_queues.items():
                for task in queue:
                    if task.task_id == task_id:
                        return task
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get task status", error=str(e))
            return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        try:
            # Check active tasks
            if task_id in self._active_tasks:
                task = self._active_tasks[task_id]
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now(timezone.utc)
                
                # Remove from agent assignment
                if task.assigned_agent_id:
                    self._agent_tasks[task.assigned_agent_id] = [
                        tid for tid in self._agent_tasks[task.assigned_agent_id] 
                        if tid != task_id
                    ]
                
                del self._active_tasks[task_id]
                
                self.logger.info("Task cancelled", task_id=task_id)
                return True
            
            # Check queues
            for priority, queue in self._task_queues.items():
                for i, task in enumerate(queue):
                    if task.task_id == task_id:
                        queue.remove(task)
                        self.logger.info("Task cancelled from queue", task_id=task_id)
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to cancel task", error=str(e))
            return False
    
    async def _process_tasks_loop(self) -> None:
        """Main task processing loop"""
        try:
            while self._running:
                # Process tasks by priority
                for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
                    if self._task_queues[priority]:
                        await self._process_priority_queue(priority)
                
                # Wait before next iteration
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            self.logger.info("Task processing loop cancelled")
        except Exception as e:
            self.logger.error("Task processing loop failed", error=str(e))
    
    async def _process_priority_queue(self, priority: TaskPriority) -> None:
        """Process tasks in a priority queue"""
        try:
            queue = self._task_queues[priority]
            
            while queue and len(self._active_tasks) < self.max_concurrent:
                task = queue.popleft()
                
                # Create task processing task
                asyncio.create_task(self._process_task(task))
                
        except Exception as e:
            self.logger.error(f"Failed to process {priority} priority queue", error=str(e))
    
    async def _process_task(self, task: Task) -> None:
        """Process a single task"""
        try:
            async with self._task_semaphore:
                # Update task status
                task.status = TaskStatus.PROCESSING
                task.assigned_at = datetime.now(timezone.utc)
                self._active_tasks[task.task_id] = task
                
                self.logger.info(
                    "Processing task",
                    task_id=task.task_id,
                    agent_type=task.agent_type,
                    priority=task.priority
                )
                
                # Find available agent
                agent = await self._find_available_agent(task.agent_type)
                if not agent:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now(timezone.utc)
                    task.result = ProcessingResult(
                        success=False,
                        transaction_id=task.transaction.id,
                        status="failed",
                        message="No available agent found",
                        error_code="NO_AGENT_AVAILABLE"
                    )
                    return
                
                # Assign task to agent
                task.assigned_agent_id = agent.agent_id
                self._agent_tasks[agent.agent_id].append(task.task_id)
                
                # Process task
                result = await agent.process_transaction_with_retry(task.transaction)
                
                # Update task with result
                task.result = result
                task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc)
                
                # Remove from agent assignment
                self._agent_tasks[agent.agent_id] = [
                    tid for tid in self._agent_tasks[agent.agent_id] 
                    if tid != task.task_id
                ]
                
                # Remove from active tasks
                del self._active_tasks[task.task_id]
                
                self.logger.info(
                    "Task completed",
                    task_id=task.task_id,
                    success=result.success,
                    processing_time=result.processing_time
                )
                
        except Exception as e:
            self.logger.error("Task processing failed", task_id=task.task_id, error=str(e))
            
            # Update task status
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now(timezone.utc)
            task.result = ProcessingResult(
                success=False,
                transaction_id=task.transaction.id,
                status="failed",
                message=f"Task processing failed: {str(e)}",
                error_code="TASK_PROCESSING_ERROR"
            )
            
            # Clean up
            if task.assigned_agent_id:
                self._agent_tasks[task.assigned_agent_id] = [
                    tid for tid in self._agent_tasks[task.assigned_agent_id] 
                    if tid != task.task_id
                ]
            
            if task.task_id in self._active_tasks:
                del self._active_tasks[task.task_id]
    
    async def _find_available_agent(self, agent_type: str) -> Optional[BaseFinancialAgent]:
        """Find an available agent of the specified type"""
        try:
            # This would integrate with the agent registry
            # For now, return None to indicate no agent available
            return None
            
        except Exception as e:
            self.logger.error("Failed to find available agent", error=str(e))
            return None
    
    async def get_task_manager_metrics(self) -> Dict[str, Any]:
        """Get task manager metrics"""
        try:
            queue_sizes = {
                priority.value: len(queue) 
                for priority, queue in self._task_queues.items()
            }
            
            active_task_count = len(self._active_tasks)
            
            # Calculate task statistics
            completed_tasks = 0
            failed_tasks = 0
            
            # This would require tracking completed/failed tasks
            # For now, return basic metrics
            
            return {
                "queue_sizes": queue_sizes,
                "active_tasks": active_task_count,
                "max_concurrent": self.max_concurrent,
                "available_slots": self.max_concurrent - active_task_count,
                "agent_task_assignments": dict(self._agent_tasks),
                "running": self._running
            }
            
        except Exception as e:
            self.logger.error("Failed to get task manager metrics", error=str(e))
            return {"error": str(e)}
    
    async def clear_completed_tasks(self) -> int:
        """Clear completed tasks from memory"""
        try:
            # This would clear completed tasks from storage
            # For now, return 0
            return 0
            
        except Exception as e:
            self.logger.error("Failed to clear completed tasks", error=str(e))
            return 0 