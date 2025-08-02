"""
Payment Workflow Factory

This module provides a factory for creating and configuring payment workflows
with different settings and requirements.
"""

from typing import Dict, List, Optional, Any, Type
from enum import Enum
import structlog

from pydantic import BaseModel, Field

from packages.core.orchestration.payment_workflow_orchestrator import (
    PaymentWorkflowOrchestrator, 
    PaymentWorkflowConfig,
    PaymentWorkflowStep
)
from packages.core.agents.base import AgentRegistry


logger = structlog.get_logger(__name__)


class WorkflowType(str, Enum):
    """Types of payment workflows"""
    STANDARD = "standard"
    FAST_TRACK = "fast_track"
    HIGH_VALUE = "high_value"
    COMPLIANCE_HEAVY = "compliance_heavy"
    LIQUIDITY_OPTIMIZED = "liquidity_optimized"
    CUSTOM = "custom"


class WorkflowPreset(BaseModel):
    """Preset configuration for payment workflows"""
    name: str
    description: str
    config: PaymentWorkflowConfig
    required_agents: List[str] = Field(default_factory=list)
    optional_steps: List[str] = Field(default_factory=list)
    skip_steps: List[str] = Field(default_factory=list)


class PaymentWorkflowFactory:
    """
    Factory for creating payment workflow orchestrators
    
    Provides predefined configurations and easy setup for different
    types of payment processing workflows.
    """
    
    def __init__(self, agent_registry: AgentRegistry):
        self.agent_registry = agent_registry
        self.logger = structlog.get_logger(__name__)
        self._presets = self._create_presets()
    
    def _create_presets(self) -> Dict[str, WorkflowPreset]:
        """Create predefined workflow presets"""
        return {
            WorkflowType.STANDARD: WorkflowPreset(
                name="Standard Payment Workflow",
                description="Standard cross-border payment processing with all steps",
                config=PaymentWorkflowConfig(
                    enable_parallel_processing=False,
                    enable_consensus=True,
                    enable_circuit_breaker=True,
                    create_payment_timeout=10.0,
                    validate_payment_timeout=5.0,
                    optimize_route_timeout=15.0,
                    validate_compliance_timeout=20.0,
                    check_liquidity_timeout=10.0,
                    lock_exchange_rate_timeout=10.0,
                    execute_mmo_timeout=30.0,
                    settle_payment_timeout=60.0,
                    confirm_payment_timeout=10.0,
                    max_retry_attempts=3,
                    retry_delay=1.0,
                    enable_performance_tracking=True,
                    performance_sampling_rate=1.0
                ),
                required_agents=[
                    "payment_service",
                    "route_optimization",
                    "compliance",
                    "liquidity",
                    "exchange_rate",
                    "mmo_service",
                    "settlement"
                ]
            ),
            
            WorkflowType.FAST_TRACK: WorkflowPreset(
                name="Fast Track Payment Workflow",
                description="Optimized for speed with reduced compliance checks",
                config=PaymentWorkflowConfig(
                    enable_parallel_processing=True,
                    enable_consensus=False,
                    enable_circuit_breaker=True,
                    create_payment_timeout=5.0,
                    validate_payment_timeout=3.0,
                    optimize_route_timeout=10.0,
                    validate_compliance_timeout=10.0,
                    check_liquidity_timeout=5.0,
                    lock_exchange_rate_timeout=5.0,
                    execute_mmo_timeout=20.0,
                    settle_payment_timeout=30.0,
                    confirm_payment_timeout=5.0,
                    max_retry_attempts=2,
                    retry_delay=0.5,
                    enable_performance_tracking=True,
                    performance_sampling_rate=0.5
                ),
                required_agents=[
                    "payment_service",
                    "route_optimization",
                    "compliance",
                    "liquidity",
                    "exchange_rate",
                    "mmo_service",
                    "settlement"
                ],
                skip_steps=[]
            ),
            
            WorkflowType.HIGH_VALUE: WorkflowPreset(
                name="High Value Payment Workflow",
                description="Enhanced security and compliance for high-value payments",
                config=PaymentWorkflowConfig(
                    enable_parallel_processing=False,
                    enable_consensus=True,
                    enable_circuit_breaker=True,
                    create_payment_timeout=15.0,
                    validate_payment_timeout=10.0,
                    optimize_route_timeout=20.0,
                    validate_compliance_timeout=45.0,
                    check_liquidity_timeout=15.0,
                    lock_exchange_rate_timeout=15.0,
                    execute_mmo_timeout=45.0,
                    settle_payment_timeout=90.0,
                    confirm_payment_timeout=15.0,
                    max_retry_attempts=5,
                    retry_delay=2.0,
                    enable_performance_tracking=True,
                    performance_sampling_rate=1.0
                ),
                required_agents=[
                    "payment_service",
                    "route_optimization",
                    "compliance",
                    "liquidity",
                    "exchange_rate",
                    "mmo_service",
                    "settlement"
                ],
                optional_steps=[
                    PaymentWorkflowStep.VALIDATE_COMPLIANCE
                ]
            ),
            
            WorkflowType.COMPLIANCE_HEAVY: WorkflowPreset(
                name="Compliance Heavy Payment Workflow",
                description="Enhanced compliance checks for regulated corridors",
                config=PaymentWorkflowConfig(
                    enable_parallel_processing=False,
                    enable_consensus=True,
                    enable_circuit_breaker=True,
                    create_payment_timeout=10.0,
                    validate_payment_timeout=5.0,
                    optimize_route_timeout=15.0,
                    validate_compliance_timeout=60.0,
                    check_liquidity_timeout=10.0,
                    lock_exchange_rate_timeout=10.0,
                    execute_mmo_timeout=30.0,
                    settle_payment_timeout=60.0,
                    confirm_payment_timeout=10.0,
                    max_retry_attempts=4,
                    retry_delay=1.5,
                    enable_performance_tracking=True,
                    performance_sampling_rate=1.0
                ),
                required_agents=[
                    "payment_service",
                    "route_optimization",
                    "compliance",
                    "liquidity",
                    "exchange_rate",
                    "mmo_service",
                    "settlement"
                ]
            ),
            
            WorkflowType.LIQUIDITY_OPTIMIZED: WorkflowPreset(
                name="Liquidity Optimized Payment Workflow",
                description="Optimized for liquidity management and pool utilization",
                config=PaymentWorkflowConfig(
                    enable_parallel_processing=True,
                    enable_consensus=True,
                    enable_circuit_breaker=True,
                    create_payment_timeout=10.0,
                    validate_payment_timeout=5.0,
                    optimize_route_timeout=20.0,
                    validate_compliance_timeout=15.0,
                    check_liquidity_timeout=20.0,
                    lock_exchange_rate_timeout=10.0,
                    execute_mmo_timeout=30.0,
                    settle_payment_timeout=60.0,
                    confirm_payment_timeout=10.0,
                    max_retry_attempts=3,
                    retry_delay=1.0,
                    enable_performance_tracking=True,
                    performance_sampling_rate=1.0
                ),
                required_agents=[
                    "payment_service",
                    "route_optimization",
                    "compliance",
                    "liquidity",
                    "exchange_rate",
                    "mmo_service",
                    "settlement"
                ]
            )
        }
    
    def create_workflow(
        self, 
        workflow_type: WorkflowType,
        custom_config: Optional[PaymentWorkflowConfig] = None
    ) -> PaymentWorkflowOrchestrator:
        """
        Create a payment workflow orchestrator
        
        Args:
            workflow_type: Type of workflow to create
            custom_config: Optional custom configuration to override preset
            
        Returns:
            PaymentWorkflowOrchestrator: Configured workflow orchestrator
        """
        try:
            if workflow_type not in self._presets:
                raise ValueError(f"Unknown workflow type: {workflow_type}")
            
            preset = self._presets[workflow_type]
            
            # Use custom config if provided, otherwise use preset
            config = custom_config or preset.config
            
            # Validate required agents are available
            self._validate_required_agents(preset.required_agents)
            
            # Create orchestrator
            orchestrator = PaymentWorkflowOrchestrator(
                agent_registry=self.agent_registry,
                config=config
            )
            
            self.logger.info(
                f"Created payment workflow: {preset.name}",
                workflow_type=workflow_type,
                config_type="custom" if custom_config else "preset"
            )
            
            return orchestrator
            
        except Exception as e:
            self.logger.error(
                f"Failed to create payment workflow: {workflow_type}",
                error=str(e),
                exc_info=True
            )
            raise
    
    def create_custom_workflow(
        self,
        name: str,
        description: str,
        config: PaymentWorkflowConfig,
        required_agents: List[str],
        optional_steps: List[str] = None,
        skip_steps: List[str] = None
    ) -> PaymentWorkflowOrchestrator:
        """
        Create a custom payment workflow
        
        Args:
            name: Workflow name
            description: Workflow description
            config: Workflow configuration
            required_agents: List of required agent types
            optional_steps: List of optional steps
            skip_steps: List of steps to skip
            
        Returns:
            PaymentWorkflowOrchestrator: Custom workflow orchestrator
        """
        try:
            # Validate required agents are available
            self._validate_required_agents(required_agents)
            
            # Create orchestrator
            orchestrator = PaymentWorkflowOrchestrator(
                agent_registry=self.agent_registry,
                config=config
            )
            
            self.logger.info(
                f"Created custom payment workflow: {name}",
                description=description,
                required_agents=required_agents
            )
            
            return orchestrator
            
        except Exception as e:
            self.logger.error(
                f"Failed to create custom payment workflow: {name}",
                error=str(e),
                exc_info=True
            )
            raise
    
    def _validate_required_agents(self, required_agents: List[str]) -> None:
        """Validate that required agents are available in the registry"""
        missing_agents = []
        
        for agent_type in required_agents:
            agents = self.agent_registry.get_agents_by_type(agent_type)
            if not agents:
                missing_agents.append(agent_type)
        
        if missing_agents:
            raise ValueError(
                f"Required agents not available in registry: {missing_agents}"
            )
    
    def get_available_presets(self) -> Dict[str, WorkflowPreset]:
        """Get all available workflow presets"""
        return self._presets.copy()
    
    def get_preset(self, workflow_type: WorkflowType) -> Optional[WorkflowPreset]:
        """Get a specific workflow preset"""
        return self._presets.get(workflow_type)
    
    def list_workflow_types(self) -> List[str]:
        """List all available workflow types"""
        return list(self._presets.keys())
    
    def validate_workflow_config(
        self, 
        config: PaymentWorkflowConfig,
        workflow_type: Optional[WorkflowType] = None
    ) -> Dict[str, Any]:
        """
        Validate a workflow configuration
        
        Args:
            config: Configuration to validate
            workflow_type: Optional workflow type for comparison
            
        Returns:
            Dict with validation results
        """
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check timeout values
        if config.create_payment_timeout < 1.0:
            validation_result["warnings"].append("create_payment_timeout is very low")
        
        if config.validate_compliance_timeout < 5.0:
            validation_result["warnings"].append("validate_compliance_timeout is very low")
        
        if config.settle_payment_timeout < 30.0:
            validation_result["warnings"].append("settle_payment_timeout is very low")
        
        # Check retry settings
        if config.max_retry_attempts > 10:
            validation_result["warnings"].append("max_retry_attempts is very high")
        
        if config.retry_delay < 0.1:
            validation_result["warnings"].append("retry_delay is very low")
        
        # Compare with preset if provided
        if workflow_type and workflow_type in self._presets:
            preset = self._presets[workflow_type]
            
            # Check if custom config differs significantly from preset
            if config.enable_parallel_processing != preset.config.enable_parallel_processing:
                validation_result["warnings"].append(
                    f"enable_parallel_processing differs from {workflow_type} preset"
                )
            
            if config.enable_consensus != preset.config.enable_consensus:
                validation_result["warnings"].append(
                    f"enable_consensus differs from {workflow_type} preset"
                )
        
        return validation_result 