"""
Base agent classes for CAPP autonomous payment system
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Type
from decimal import Decimal

import structlog
from pydantic import BaseModel, Field

from .models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentRoute,
    Country, Currency, MMOProvider
)
from .config.settings import get_settings
from .core.aptos import get_aptos_client
from .core.database import get_database_session
from .core.redis import get_redis_client
from .services.metrics import MetricsCollector


logger = structlog.get_logger(__name__)


class AgentConfig(BaseModel):
    """Base configuration for payment agents"""
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


class BasePaymentAgent(ABC):
    """
    Base class for all payment agents in the CAPP system
    
    This class provides the foundation for autonomous payment processing
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
        
        # Core services
        self.settings = get_settings()
        self.aptos_client = get_aptos_client()
        self.redis_client = get_redis_client()
        self.metrics_collector = MetricsCollector()
        
        # Logging
        self.logger = structlog.get_logger(f"{self.agent_type}.{self.agent_id}")
        
        # Task management
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        
        # Circuit breaker
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        
        self.logger.info(
            "Agent initialized",
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            config=config.dict()
        )
    
    @abstractmethod
    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Process a cross-border payment
        
        Args:
            payment: The payment to process
            
        Returns:
            PaymentResult: The result of the payment processing
        """
        pass
    
    @abstractmethod
    async def validate_payment(self, payment: CrossBorderPayment) -> bool:
        """
        Validate if the payment can be processed by this agent
        
        Args:
            payment: The payment to validate
            
        Returns:
            bool: True if payment can be processed, False otherwise
        """
        pass
    
    async def validate_corridor(self, from_country: Country, to_country: Country) -> bool:
        """
        Validate if the payment corridor is supported
        
        Args:
            from_country: Source country
            to_country: Destination country
            
        Returns:
            bool: True if corridor is supported, False otherwise
        """
        # Base implementation - can be overridden by specific agents
        return True
    
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
    
    async def process_payment_with_retry(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Process payment with retry logic and circuit breaker
        
        Args:
            payment: The payment to process
            
        Returns:
            PaymentResult: The result of the payment processing
        """
        if self._is_circuit_breaker_open():
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message="Circuit breaker is open - agent temporarily unavailable",
                error_code="CIRCUIT_BREAKER_OPEN"
            )
        
        async with self._task_semaphore:
            task_id = str(uuid.uuid4())
            self.state.current_tasks += 1
            
            try:
                start_time = datetime.now(timezone.utc)
                
                # Validate payment first
                if not await self.validate_payment(payment):
                    return PaymentResult(
                        success=False,
                        payment_id=payment.payment_id,
                        status=PaymentStatus.FAILED,
                        message="Payment validation failed",
                        error_code="VALIDATION_FAILED"
                    )
                
                # Process with retry logic
                result = await self._process_with_retry(payment)
                
                # Update metrics
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
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
                    "Unexpected error in payment processing",
                    payment_id=payment.payment_id,
                    error=str(e),
                    exc_info=True
                )
                
                self._record_failure()
                
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message=f"Unexpected error: {str(e)}",
                    error_code="UNEXPECTED_ERROR"
                )
            finally:
                self.state.current_tasks -= 1
    
    async def _process_with_retry(self, payment: CrossBorderPayment) -> PaymentResult:
        """Process payment with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.retry_attempts + 1):
            try:
                if attempt > 0:
                    delay = self.config.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    await asyncio.sleep(delay)
                    self.logger.info(
                        "Retrying payment processing",
                        payment_id=payment.payment_id,
                        attempt=attempt
                    )
                
                return await self.process_payment(payment)
                
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    "Payment processing attempt failed",
                    payment_id=payment.payment_id,
                    attempt=attempt,
                    error=str(e)
                )
        
        # All retries failed
        return PaymentResult(
            success=False,
            payment_id=payment.payment_id,
            status=PaymentStatus.FAILED,
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
    
    async def _update_metrics(self, result: PaymentResult, processing_time: float) -> None:
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
            payment_amount=result.payment_id  # Use payment_id as proxy for amount
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
    """Registry for managing payment agents"""
    
    def __init__(self):
        self._agents: Dict[str, BasePaymentAgent] = {}
        self._agent_types: Dict[str, Type[BasePaymentAgent]] = {}
    
    def register_agent_type(self, agent_type: str, agent_class: Type[BasePaymentAgent]) -> None:
        """Register an agent type"""
        self._agent_types[agent_type] = agent_class
    
    def create_agent(self, agent_type: str, config: AgentConfig) -> BasePaymentAgent:
        """Create a new agent instance"""
        if agent_type not in self._agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_class = self._agent_types[agent_type]
        agent = agent_class(config)
        self._agents[agent.agent_id] = agent
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[BasePaymentAgent]:
        """Get agent by ID"""
        return self._agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: str) -> List[BasePaymentAgent]:
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