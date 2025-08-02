"""
Main orchestration engine for financial applications

This module provides the core orchestration logic that coordinates multiple agents
to process financial transactions efficiently and reliably.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Type, Callable
from decimal import Decimal
import uuid

import structlog
from pydantic import BaseModel, Field

from packages.core.agents.base import BaseFinancialAgent, AgentRegistry, ProcessingResult
from packages.core.agents.financial_base import FinancialTransaction, FinancialProcessingResult
from packages.core.consensus.mechanisms import ConsensusEngine
from packages.core.orchestration.coordinator import AgentCoordinator
from packages.core.orchestration.task_manager import TaskManager
from packages.core.performance.tracker import PerformanceTracker


logger = structlog.get_logger(__name__)


class OrchestrationConfig(BaseModel):
    """Configuration for the orchestration engine"""
    # General settings
    max_concurrent_transactions: int = 100
    transaction_timeout: float = 300.0  # 5 minutes
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Consensus settings
    consensus_threshold: float = 0.7
    consensus_timeout: float = 30.0
    
    # Performance settings
    enable_performance_tracking: bool = True
    performance_sampling_rate: float = 1.0  # 100% sampling
    
    # Monitoring
    enable_metrics: bool = True
    enable_logging: bool = True
    
    # Circuit breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 10
    circuit_breaker_timeout: float = 60.0


class OrchestrationStep(BaseModel):
    """Definition of an orchestration step"""
    step_id: str
    step_name: str
    agent_type: str
    required: bool = True
    timeout: float = 30.0
    retry_attempts: int = 3
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationWorkflow(BaseModel):
    """Definition of an orchestration workflow"""
    workflow_id: str
    workflow_name: str
    steps: List[OrchestrationStep]
    max_parallel_steps: int = 5
    timeout: float = 300.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationResult(BaseModel):
    """Result of orchestration processing"""
    success: bool
    transaction_id: str
    workflow_id: str
    status: str
    message: str
    processing_time: float
    step_results: Dict[str, ProcessingResult]
    final_result: Optional[ProcessingResult] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FinancialOrchestrator:
    """
    Main orchestration engine for financial applications
    
    This class coordinates multiple agents to process financial transactions
    with features like:
    - Multi-step workflow processing
    - Agent coordination and consensus
    - Performance tracking and monitoring
    - Error handling and recovery
    - Circuit breaker patterns
    """
    
    def __init__(self, config: OrchestrationConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Core components
        self.agent_registry = AgentRegistry()
        self.consensus_engine = ConsensusEngine(
            threshold=config.consensus_threshold,
            timeout=config.consensus_timeout
        )
        self.coordinator = AgentCoordinator(self.agent_registry)
        self.task_manager = TaskManager(
            max_concurrent=config.max_concurrent_transactions
        )
        self.performance_tracker = PerformanceTracker(
            enabled=config.enable_performance_tracking,
            sampling_rate=config.performance_sampling_rate
        )
        
        # Workflow registry
        self._workflows: Dict[str, OrchestrationWorkflow] = {}
        
        # Circuit breaker
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._circuit_breaker_open = False
        
        self.logger.info("Financial orchestrator initialized", config=config.dict())
    
    def register_workflow(self, workflow: OrchestrationWorkflow) -> None:
        """Register an orchestration workflow"""
        self._workflows[workflow.workflow_id] = workflow
        self.logger.info("Workflow registered", workflow_id=workflow.workflow_id)
    
    def get_workflow(self, workflow_id: str) -> Optional[OrchestrationWorkflow]:
        """Get a registered workflow"""
        return self._workflows.get(workflow_id)
    
    async def process_transaction(
        self, 
        transaction: FinancialTransaction, 
        workflow_id: str
    ) -> OrchestrationResult:
        """
        Process a financial transaction through the specified workflow
        
        Args:
            transaction: The transaction to process
            workflow_id: The workflow to use for processing
            
        Returns:
            OrchestrationResult: The orchestration result
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open():
                return OrchestrationResult(
                    success=False,
                    transaction_id=transaction.id,
                    workflow_id=workflow_id,
                    status="failed",
                    message="Circuit breaker is open - orchestrator temporarily unavailable",
                    processing_time=0.0,
                    step_results={},
                    error_code="CIRCUIT_BREAKER_OPEN"
                )
            
            # Get workflow
            workflow = self.get_workflow(workflow_id)
            if not workflow:
                return OrchestrationResult(
                    success=False,
                    transaction_id=transaction.id,
                    workflow_id=workflow_id,
                    status="failed",
                    message=f"Workflow not found: {workflow_id}",
                    processing_time=0.0,
                    step_results={},
                    error_code="WORKFLOW_NOT_FOUND"
                )
            
            self.logger.info(
                "Starting transaction orchestration",
                transaction_id=transaction.id,
                workflow_id=workflow_id,
                workflow_name=workflow.workflow_name
            )
            
            # Process through workflow
            step_results = await self._execute_workflow(transaction, workflow)
            
            # Determine final result
            final_result = await self._determine_final_result(step_results, workflow)
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Record performance metrics
            await self._record_performance_metrics(transaction, processing_time, final_result.success)
            
            # Update circuit breaker
            if final_result.success:
                self._reset_circuit_breaker()
            else:
                self._record_failure()
            
            self.logger.info(
                "Transaction orchestration completed",
                transaction_id=transaction.id,
                success=final_result.success,
                processing_time=processing_time
            )
            
            return OrchestrationResult(
                success=final_result.success,
                transaction_id=transaction.id,
                workflow_id=workflow_id,
                status="completed" if final_result.success else "failed",
                message=final_result.message,
                processing_time=processing_time,
                step_results=step_results,
                final_result=final_result,
                error_code=final_result.error_code
            )
            
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.error(
                "Transaction orchestration failed",
                transaction_id=transaction.id,
                workflow_id=workflow_id,
                error=str(e),
                exc_info=True
            )
            
            self._record_failure()
            
            return OrchestrationResult(
                success=False,
                transaction_id=transaction.id,
                workflow_id=workflow_id,
                status="failed",
                message=f"Orchestration error: {str(e)}",
                processing_time=processing_time,
                step_results={},
                error_code="ORCHESTRATION_ERROR"
            )
    
    async def _execute_workflow(
        self, 
        transaction: FinancialTransaction, 
        workflow: OrchestrationWorkflow
    ) -> Dict[str, ProcessingResult]:
        """Execute a workflow for a transaction"""
        step_results: Dict[str, ProcessingResult] = {}
        
        try:
            # Create dependency graph
            dependency_graph = self._build_dependency_graph(workflow.steps)
            
            # Execute steps in dependency order
            for step_batch in self._get_execution_order(dependency_graph):
                # Execute parallel steps
                batch_tasks = []
                for step in step_batch:
                    if self._can_execute_step(step, step_results):
                        task = self._execute_step(transaction, step, step_results)
                        batch_tasks.append(task)
                
                # Wait for batch completion
                if batch_tasks:
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Process results
                    for i, result in enumerate(batch_results):
                        if isinstance(result, Exception):
                            step = step_batch[i]
                            step_results[step.step_id] = ProcessingResult(
                                success=False,
                                transaction_id=transaction.id,
                                status="failed",
                                message=f"Step execution failed: {str(result)}",
                                error_code="STEP_EXECUTION_ERROR"
                            )
                        else:
                            step = step_batch[i]
                            step_results[step.step_id] = result
            
            return step_results
            
        except Exception as e:
            self.logger.error("Workflow execution failed", error=str(e))
            raise
    
    def _build_dependency_graph(self, steps: List[OrchestrationStep]) -> Dict[str, List[str]]:
        """Build dependency graph for workflow steps"""
        graph = {}
        for step in steps:
            graph[step.step_id] = step.dependencies
        return graph
    
    def _get_execution_order(self, dependency_graph: Dict[str, List[str]]) -> List[List[OrchestrationStep]]:
        """Get execution order for steps based on dependencies"""
        # Simple topological sort implementation
        # In production, use a more robust implementation
        steps_by_id = {step.step_id: step for step in self._workflows.values()}
        
        execution_order = []
        visited = set()
        temp_visited = set()
        
        def visit(step_id: str) -> List[OrchestrationStep]:
            if step_id in temp_visited:
                raise ValueError(f"Circular dependency detected: {step_id}")
            
            if step_id in visited:
                return []
            
            temp_visited.add(step_id)
            
            # Visit dependencies first
            dependencies = dependency_graph.get(step_id, [])
            for dep_id in dependencies:
                visit(dep_id)
            
            temp_visited.remove(step_id)
            visited.add(step_id)
            
            return [steps_by_id[step_id]]
        
        # Visit all steps
        for step_id in dependency_graph:
            if step_id not in visited:
                batch = visit(step_id)
                if batch:
                    execution_order.append(batch)
        
        return execution_order
    
    def _can_execute_step(
        self, 
        step: OrchestrationStep, 
        step_results: Dict[str, ProcessingResult]
    ) -> bool:
        """Check if a step can be executed based on dependencies"""
        for dep_id in step.dependencies:
            if dep_id not in step_results:
                return False
            if not step_results[dep_id].success:
                return False
        return True
    
    async def _execute_step(
        self, 
        transaction: FinancialTransaction, 
        step: OrchestrationStep, 
        step_results: Dict[str, ProcessingResult]
    ) -> ProcessingResult:
        """Execute a single workflow step"""
        try:
            self.logger.info(
                "Executing workflow step",
                transaction_id=transaction.id,
                step_id=step.step_id,
                step_name=step.step_name,
                agent_type=step.agent_type
            )
            
            # Get agents for this step
            agents = self.agent_registry.get_agents_by_type(step.agent_type)
            if not agents:
                return ProcessingResult(
                    success=False,
                    transaction_id=transaction.id,
                    status="failed",
                    message=f"No agents available for type: {step.agent_type}",
                    error_code="NO_AGENTS_AVAILABLE"
                )
            
            # Execute with consensus if multiple agents
            if len(agents) > 1:
                return await self._execute_with_consensus(transaction, step, agents)
            else:
                return await self._execute_single_agent(transaction, step, agents[0])
            
        except Exception as e:
            self.logger.error(
                "Step execution failed",
                transaction_id=transaction.id,
                step_id=step.step_id,
                error=str(e)
            )
            
            return ProcessingResult(
                success=False,
                transaction_id=transaction.id,
                status="failed",
                message=f"Step execution failed: {str(e)}",
                error_code="STEP_EXECUTION_ERROR"
            )
    
    async def _execute_single_agent(
        self, 
        transaction: FinancialTransaction, 
        step: OrchestrationStep, 
        agent: BaseFinancialAgent
    ) -> ProcessingResult:
        """Execute a step with a single agent"""
        try:
            # Add step metadata to transaction
            transaction.metadata.update(step.metadata)
            
            # Process with agent
            result = await agent.process_transaction_with_retry(transaction)
            
            return result
            
        except Exception as e:
            self.logger.error("Single agent execution failed", error=str(e))
            raise
    
    async def _execute_with_consensus(
        self, 
        transaction: FinancialTransaction, 
        step: OrchestrationStep, 
        agents: List[BaseFinancialAgent]
    ) -> ProcessingResult:
        """Execute a step with multiple agents using consensus"""
        try:
            # Create tasks for all agents
            tasks = []
            for agent in agents:
                task = agent.process_transaction_with_retry(transaction)
                tasks.append(task)
            
            # Execute all agents
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.warning(
                        "Agent execution failed",
                        agent_id=agents[i].agent_id,
                        error=str(result)
                    )
                else:
                    valid_results.append(result)
            
            if not valid_results:
                return ProcessingResult(
                    success=False,
                    transaction_id=transaction.id,
                    status="failed",
                    message="All agents failed to execute",
                    error_code="ALL_AGENTS_FAILED"
                )
            
            # Apply consensus
            consensus_result = await self.consensus_engine.reach_consensus(valid_results)
            
            return consensus_result
            
        except Exception as e:
            self.logger.error("Consensus execution failed", error=str(e))
            raise
    
    async def _determine_final_result(
        self, 
        step_results: Dict[str, ProcessingResult], 
        workflow: OrchestrationWorkflow
    ) -> ProcessingResult:
        """Determine the final result based on step results"""
        try:
            # Check if all required steps succeeded
            failed_steps = []
            for step in workflow.steps:
                if step.required:
                    if step.step_id not in step_results:
                        failed_steps.append(f"Missing step: {step.step_name}")
                    elif not step_results[step.step_id].success:
                        failed_steps.append(f"Failed step: {step.step_name}")
            
            if failed_steps:
                return ProcessingResult(
                    success=False,
                    transaction_id=list(step_results.values())[0].transaction_id if step_results else "unknown",
                    status="failed",
                    message=f"Workflow failed: {', '.join(failed_steps)}",
                    error_code="WORKFLOW_FAILED"
                )
            
            # All required steps succeeded
            return ProcessingResult(
                success=True,
                transaction_id=list(step_results.values())[0].transaction_id if step_results else "unknown",
                status="completed",
                message="Workflow completed successfully"
            )
            
        except Exception as e:
            self.logger.error("Failed to determine final result", error=str(e))
            return ProcessingResult(
                success=False,
                transaction_id="unknown",
                status="failed",
                message=f"Failed to determine final result: {str(e)}",
                error_code="FINAL_RESULT_ERROR"
            )
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self.config.circuit_breaker_enabled:
            return False
        
        if not self._circuit_breaker_open:
            return False
        
        # Check if timeout has passed
        if self._last_failure_time:
            timeout_duration = datetime.now(timezone.utc) - self._last_failure_time
            if timeout_duration.total_seconds() >= self.config.circuit_breaker_timeout:
                self._reset_circuit_breaker()
                return False
        
        return True
    
    def _record_failure(self) -> None:
        """Record a failure for circuit breaker"""
        if not self.config.circuit_breaker_enabled:
            return
        
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc)
        
        if self._failure_count >= self.config.circuit_breaker_threshold:
            self._circuit_breaker_open = True
            self.logger.warning(
                "Circuit breaker opened",
                failure_count=self._failure_count
            )
    
    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker"""
        self._failure_count = 0
        self._circuit_breaker_open = False
        self._last_failure_time = None
    
    async def _record_performance_metrics(
        self, 
        transaction: FinancialTransaction, 
        processing_time: float, 
        success: bool
    ) -> None:
        """Record performance metrics"""
        try:
            await self.performance_tracker.record_transaction_metrics(
                transaction_id=transaction.id,
                transaction_type=transaction.transaction_type.value,
                amount=float(transaction.amount),
                processing_time=processing_time,
                success=success
            )
        except Exception as e:
            self.logger.error("Failed to record performance metrics", error=str(e))
    
    async def get_orchestration_metrics(self) -> Dict[str, Any]:
        """Get orchestration metrics"""
        try:
            return {
                "workflows_registered": len(self._workflows),
                "circuit_breaker_open": self._circuit_breaker_open,
                "failure_count": self._failure_count,
                "performance_metrics": await self.performance_tracker.get_metrics(),
                "agent_health": await self.agent_registry.get_all_health_status()
            }
        except Exception as e:
            self.logger.error("Failed to get orchestration metrics", error=str(e))
            return {} 