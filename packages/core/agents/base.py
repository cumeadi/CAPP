"""
Base agent classes for financial orchestration system

This module provides the foundation for autonomous financial processing agents
with features like circuit breaker patterns, retry logic, performance monitoring,
and state management.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Type, Generic, TypeVar
from decimal import Decimal

import structlog
from pydantic import BaseModel, Field

from packages.core.performance.metrics import MetricsCollector

logger = structlog.get_logger(__name__)

# Generic type for financial transactions
T = TypeVar('T')


class AgentConfig(BaseModel):
    """Base configuration for financial agents"""
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: str
    enabled: bool = True
    max_concurrent_tasks: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds
    timeout: float = 30.0  # seconds
    priority: int = 1  # 1-10, higher is more important
    
    # Performance settings
    batch_size: int = 100
    processing_interval: float = 1.0  # seconds
    
    # Monitoring
    enable_metrics: bool = True
    enable_logging: bool = True
    
    # Circuit breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0  # seconds


class AgentState(BaseModel):
    """Agent state management"""
    agent_id: str
    status: str = "idle"  # idle, busy, error, offline
    current_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_count: int = 0
    circuit_breaker_open: bool = False
    circuit_breaker_opened_at: Optional[datetime] = None
    
    # Performance metrics
    average_processing_time: float = 0.0
    total_processing_time: float = 0.0
    success_rate: float = 1.0
    
    # Resource usage
    memory_usage: float = 0.0
    cpu_usage: float = 0.0


class ProcessingResult(BaseModel):
    """Generic result for financial processing operations"""
    success: bool
    transaction_id: str
    status: str
    message: str
    error_code: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseFinancialAgent(ABC, Generic[T]):
    """
    Base class for all financial agents
    
    This class provides the foundation for autonomous financial processing
    with features like:
    - Circuit breaker pattern for fault tolerance
    - Retry logic with exponential backoff
    - Performance monitoring and metrics
    - State management
    - Error handling and logging
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.agent_type = config.agent_type
        self.state = AgentState(agent_id=config.agent_id)
        
        # Logging
        self.logger = structlog.get_logger(f"{self.agent_type}.{self.agent_id}")
        
        # Task management
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        
        # Circuit breaker
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        
        # Metrics collector
        self.metrics_collector = MetricsCollector()
        
        self.logger.info(
            "Agent initialized",
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            config=config.dict()
        )
    
    @abstractmethod
    async def process_transaction(self, transaction: T) -> ProcessingResult:
        """
        Process a financial transaction
        
        Args:
            transaction: The transaction to process
            
        Returns:
            ProcessingResult: The result of the transaction processing
        """
        pass
    
    @abstractmethod
    async def validate_transaction(self, transaction: T) -> bool:
        """
        Validate if the transaction can be processed by this agent
        
        Args:
            transaction: The transaction to validate
            
        Returns:
            bool: True if transaction can be processed, False otherwise
        """
        pass
    
    async def start(self) -> None:
        """Start the agent"""
        self.state.status = "idle"
        self.logger.info("Agent started", agent_id=self.agent_id)
    
    async def stop(self) -> None:
        """Stop the agent and cancel all running tasks"""
        self.state.status = "stopping"
        
        # Cancel all running tasks
        for task_id, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._running_tasks.clear()
        self.state.status = "stopped"
        self.logger.info("Agent stopped", agent_id=self.agent_id)
    
    async def process_transaction_with_retry(self, transaction: T) -> ProcessingResult:
        """
        Process transaction with retry logic and circuit breaker
        
        Args:
            transaction: The transaction to process
            
        Returns:
            ProcessingResult: The result of the transaction processing
        """
        if self._is_circuit_breaker_open():
            return ProcessingResult(
                success=False,
                transaction_id=getattr(transaction, 'id', str(uuid.uuid4())),
                status="failed",
                message="Circuit breaker is open - agent temporarily unavailable",
                error_code="CIRCUIT_BREAKER_OPEN"
            )
        
        async with self._task_semaphore:
            task_id = str(uuid.uuid4())
            self.state.current_tasks += 1
            
            try:
                start_time = datetime.now(timezone.utc)
                
                # Validate transaction first
                if not await self.validate_transaction(transaction):
                    return ProcessingResult(
                        success=False,
                        transaction_id=getattr(transaction, 'id', str(uuid.uuid4())),
                        status="failed",
                        message="Transaction validation failed",
                        error_code="VALIDATION_FAILED"
                    )
                
                # Process with retry logic
                result = await self._process_with_retry(transaction)
                
                # Update metrics
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                result.processing_time = processing_time
                await self._update_metrics(result, processing_time)
                
                # Update state
                self.state.completed_tasks += 1
                self.state.last_activity = datetime.now(timezone.utc)
                
                if result.success:
                    self._reset_circuit_breaker()
                else:
                    self._record_failure()
                
                return result
                
            except Exception as e:
                self.logger.error(
                    "Unexpected error in transaction processing",
                    transaction_id=getattr(transaction, 'id', 'unknown'),
                    error=str(e),
                    exc_info=True
                )
                
                self._record_failure()
                
                return ProcessingResult(
                    success=False,
                    transaction_id=getattr(transaction, 'id', str(uuid.uuid4())),
                    status="failed",
                    message=f"Unexpected error: {str(e)}",
                    error_code="UNEXPECTED_ERROR"
                )
            finally:
                self.state.current_tasks -= 1
    
    async def _process_with_retry(self, transaction: T) -> ProcessingResult:
        """Process transaction with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.retry_attempts + 1):
            try:
                if attempt > 0:
                    delay = self.config.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    await asyncio.sleep(delay)
                    self.logger.info(
                        "Retrying transaction processing",
                        transaction_id=getattr(transaction, 'id', 'unknown'),
                        attempt=attempt
                    )
                
                return await self.process_transaction(transaction)
                
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    "Transaction processing attempt failed",
                    transaction_id=getattr(transaction, 'id', 'unknown'),
                    attempt=attempt,
                    error=str(e)
                )
        
        # All retries failed
        return ProcessingResult(
            success=False,
            transaction_id=getattr(transaction, 'id', str(uuid.uuid4())),
            status="failed",
            message=f"All retry attempts failed: {str(last_exception)}",
            error_code="RETRY_EXHAUSTED"
        )
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self.config.circuit_breaker_enabled:
            return False
        
        if not self.state.circuit_breaker_open:
            return False
        
        # Check if timeout has passed
        if self.state.circuit_breaker_opened_at:
            timeout_duration = datetime.now(timezone.utc) - self.state.circuit_breaker_opened_at
            if timeout_duration.total_seconds() >= self.config.circuit_breaker_timeout:
                self._reset_circuit_breaker()
                return False
        
        return True
    
    def _record_failure(self) -> None:
        """Record a failure for circuit breaker"""
        if not self.config.circuit_breaker_enabled:
            return
        
        self._failure_count += 1
        self.state.error_count += 1
        self._last_failure_time = datetime.now(timezone.utc)
        
        if self._failure_count >= self.config.circuit_breaker_threshold:
            self.state.circuit_breaker_open = True
            self.state.circuit_breaker_opened_at = datetime.now(timezone.utc)
            self.logger.warning(
                "Circuit breaker opened",
                agent_id=self.agent_id,
                failure_count=self._failure_count
            )
    
    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker"""
        self._failure_count = 0
        self.state.circuit_breaker_open = False
        self.state.circuit_breaker_opened_at = None
    
    async def _update_metrics(self, result: ProcessingResult, processing_time: float) -> None:
        """Update performance metrics"""
        if not self.config.enable_metrics:
            return
        
        # Update state metrics
        self.state.total_processing_time += processing_time
        if self.state.completed_tasks > 0:
            self.state.average_processing_time = (
                self.state.total_processing_time / self.state.completed_tasks
            )
        
        if result.success:
            if self.state.completed_tasks > 0:
                self.state.success_rate = (
                    (self.state.completed_tasks - self.state.failed_tasks) / 
                    self.state.completed_tasks
                )
        else:
            self.state.failed_tasks += 1
            if self.state.completed_tasks > 0:
                self.state.success_rate = (
                    (self.state.completed_tasks - self.state.failed_tasks) / 
                    self.state.completed_tasks
                )
        
        # Send metrics to collector
        await self.metrics_collector.record_agent_metrics(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            processing_time=processing_time,
            success=result.success,
            transaction_id=result.transaction_id
        )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get agent health status"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.state.status,
            "current_tasks": self.state.current_tasks,
            "completed_tasks": self.state.completed_tasks,
            "failed_tasks": self.state.failed_tasks,
            "success_rate": self.state.success_rate,
            "average_processing_time": self.state.average_processing_time,
            "circuit_breaker_open": self.state.circuit_breaker_open,
            "last_activity": self.state.last_activity.isoformat(),
            "config": self.config.dict()
        }
    
    async def update_config(self, new_config: AgentConfig) -> None:
        """Update agent configuration"""
        self.config = new_config
        self._task_semaphore = asyncio.Semaphore(new_config.max_concurrent_tasks)
        self.logger.info("Agent configuration updated", new_config=new_config.dict())


class AgentRegistry:
    """Registry for managing financial agents"""
    
    def __init__(self):
        self._agents: Dict[str, BaseFinancialAgent] = {}
        self._agent_types: Dict[str, Type[BaseFinancialAgent]] = {}
    
    def register_agent_type(self, agent_type: str, agent_class: Type[BaseFinancialAgent]) -> None:
        """Register an agent type"""
        self._agent_types[agent_type] = agent_class
    
    def create_agent(self, agent_type: str, config: AgentConfig) -> BaseFinancialAgent:
        """Create a new agent instance"""
        if agent_type not in self._agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_class = self._agent_types[agent_type]
        agent = agent_class(config)
        self._agents[agent.agent_id] = agent
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[BaseFinancialAgent]:
        """Get agent by ID"""
        return self._agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: str) -> List[BaseFinancialAgent]:
        """Get all agents of a specific type"""
        return [agent for agent in self._agents.values() if agent.agent_type == agent_type]
    
    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent"""
        if agent_id in self._agents:
            del self._agents[agent_id]
    
    async def stop_all_agents(self) -> None:
        """Stop all registered agents"""
        for agent in self._agents.values():
            await agent.stop()
    
    async def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all agents"""
        statuses = {}
        for agent_id, agent in self._agents.items():
            statuses[agent_id] = await agent.get_health_status()
        return statuses


# Global agent registry
agent_registry = AgentRegistry() 