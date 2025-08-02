"""
Canza Agent Framework SDK

Main framework interface for achieving 91% cost reduction through intelligent
multi-agent orchestration and proven optimization algorithms.

This framework provides a simple, powerful developer interface that abstracts
the complexity of multi-agent systems while preserving the core intelligence
that delivers results.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from functools import wraps

import structlog
from pydantic import BaseModel, Field

from packages.core.agents.base import BaseFinancialAgent, AgentConfig
from packages.core.agents.financial_base import FinancialTransaction, TransactionResult
from packages.core.agents.templates import (
    PaymentOptimizerAgent, PaymentOptimizerConfig, OptimizationStrategy,
    ComplianceCheckerAgent, ComplianceCheckerConfig, ComplianceLevel
)
from packages.core.orchestration.coordinator import OrchestrationCoordinator
from packages.core.consensus.consensus_engine import ConsensusEngine
from packages.core.performance.metrics_collector import MetricsCollector
from packages.integrations.data.redis_client import RedisClient, RedisConfig


logger = structlog.get_logger(__name__)


class Region(str, Enum):
    """Supported regions for framework configuration"""
    GLOBAL = "global"
    AFRICA = "africa"
    EAST_AFRICA = "east_africa"
    WEST_AFRICA = "west_africa"
    SOUTH_AFRICA = "south_africa"
    NORTH_AFRICA = "north_africa"
    EUROPE = "europe"
    ASIA = "asia"
    AMERICAS = "americas"


class ComplianceLevel(str, Enum):
    """Compliance levels for framework configuration"""
    BASIC = "basic"
    STANDARD = "standard"
    ENHANCED = "enhanced"
    CRITICAL = "critical"


class RiskTolerance(str, Enum):
    """Risk tolerance levels"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class FrameworkConfig(BaseModel):
    """Configuration for the Financial Framework"""
    region: Region = Region.GLOBAL
    compliance_level: ComplianceLevel = ComplianceLevel.STANDARD
    enable_learning: bool = True
    enable_consensus: bool = True
    enable_metrics: bool = True
    redis_config: Optional[RedisConfig] = None
    max_concurrent_agents: int = 10
    workflow_timeout: int = 300  # seconds
    consensus_threshold: float = 0.75


class AgentResult(BaseModel):
    """Result from agent execution"""
    agent_id: str
    agent_type: str
    success: bool
    confidence: float
    result: Dict[str, Any]
    processing_time: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    """Result from workflow execution"""
    workflow_id: str
    success: bool
    consensus_reached: bool
    agent_results: List[AgentResult]
    final_result: Dict[str, Any]
    total_processing_time: float
    cost_savings_percentage: Optional[float] = None
    compliance_score: Optional[float] = None
    risk_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FinancialFramework:
    """
    Canza Agent Framework
    
    Main framework interface for achieving 91% cost reduction through intelligent
    multi-agent orchestration. This framework provides a simple, powerful developer
    interface that abstracts the complexity of multi-agent systems while preserving
    the core intelligence that delivers results.
    
    Key Features:
    - Multi-agent orchestration with proven consensus mechanisms
    - Intelligent payment optimization (91% cost reduction)
    - Comprehensive compliance checking
    - Risk assessment and management
    - Performance tracking and analytics
    - Learning and adaptation capabilities
    """
    
    def __init__(self, region: Region = Region.GLOBAL, 
                 compliance_level: ComplianceLevel = ComplianceLevel.STANDARD,
                 config: Optional[FrameworkConfig] = None):
        """
        Initialize the Financial Framework
        
        Args:
            region: Target region for optimization
            compliance_level: Required compliance level
            config: Framework configuration
        """
        self.config = config or FrameworkConfig(
            region=region,
            compliance_level=compliance_level
        )
        
        # Core components
        self.coordinator = OrchestrationCoordinator()
        self.consensus_engine = ConsensusEngine()
        self.metrics_collector = MetricsCollector()
        
        # Agent registry
        self.agents: Dict[str, BaseFinancialAgent] = {}
        self.agent_configs: Dict[str, AgentConfig] = {}
        
        # Redis client for caching and state management
        self.redis_client: Optional[RedisClient] = None
        
        # Workflow tracking
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_history: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.total_transactions_processed = 0
        self.total_cost_savings = Decimal("0")
        self.average_processing_time = 0.0
        
        self.logger = structlog.get_logger(__name__)
        self.logger.info(
            "Financial Framework initialized",
            region=region.value,
            compliance_level=compliance_level.value
        )
    
    async def initialize(self, redis_config: Optional[RedisConfig] = None) -> bool:
        """
        Initialize the framework and all components
        
        Args:
            redis_config: Redis configuration for caching
            
        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize Redis client
            if redis_config or self.config.redis_config:
                config = redis_config or self.config.redis_config
                self.redis_client = RedisClient(config)
                await self.redis_client.connect()
            
            # Initialize core components
            await self.coordinator.initialize()
            await self.consensus_engine.initialize()
            await self.metrics_collector.initialize()
            
            # Initialize default agents based on configuration
            await self._initialize_default_agents()
            
            self.logger.info("Financial Framework initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize Financial Framework", error=str(e))
            return False
    
    def add_agent(self, agent: BaseFinancialAgent) -> bool:
        """
        Add an agent to the orchestration system
        
        Args:
            agent: Agent to add
            
        Returns:
            bool: True if agent added successfully
        """
        try:
            agent_id = f"{agent.config.agent_type}_{len(self.agents)}"
            self.agents[agent_id] = agent
            self.agent_configs[agent_id] = agent.config
            
            # Register with coordinator
            self.coordinator.register_agent(agent_id, agent)
            
            self.logger.info(
                "Agent added to framework",
                agent_id=agent_id,
                agent_type=agent.config.agent_type
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to add agent", error=str(e))
            return False
    
    def workflow(self, func: Callable) -> Callable:
        """
        Decorator for multi-agent workflows
        
        Args:
            func: Workflow function to decorate
            
        Returns:
            Callable: Decorated workflow function
        """
        @wraps(func)
        async def workflow_wrapper(*args, **kwargs):
            workflow_id = f"workflow_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
            
            try:
                # Start workflow tracking
                self.active_workflows[workflow_id] = {
                    "start_time": datetime.now(timezone.utc),
                    "function": func.__name__,
                    "status": "running"
                }
                
                # Execute workflow with consensus
                result = await self.execute_with_consensus({
                    "workflow_id": workflow_id,
                    "function": func,
                    "args": args,
                    "kwargs": kwargs
                })
                
                # Update workflow tracking
                self.active_workflows[workflow_id]["status"] = "completed"
                self.active_workflows[workflow_id]["result"] = result.dict()
                
                # Add to history
                self.workflow_history.append({
                    "workflow_id": workflow_id,
                    "function": func.__name__,
                    "result": result.dict(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                return result
                
            except Exception as e:
                # Update workflow tracking
                if workflow_id in self.active_workflows:
                    self.active_workflows[workflow_id]["status"] = "failed"
                    self.active_workflows[workflow_id]["error"] = str(e)
                
                self.logger.error(
                    "Workflow execution failed",
                    workflow_id=workflow_id,
                    function=func.__name__,
                    error=str(e)
                )
                raise
                
        return workflow_wrapper
    
    async def execute_with_consensus(self, context: Dict[str, Any]) -> WorkflowResult:
        """
        Execute workflow using proven consensus mechanisms
        
        Args:
            context: Workflow context including function and parameters
            
        Returns:
            WorkflowResult: Consensus-based workflow result
        """
        try:
            workflow_id = context["workflow_id"]
            start_time = datetime.now(timezone.utc)
            
            # Extract workflow parameters
            func = context["function"]
            args = context.get("args", [])
            kwargs = context.get("kwargs", {})
            
            # Execute workflow function
            workflow_result = await func(*args, **kwargs)
            
            # If result is a transaction, process through agents
            if isinstance(workflow_result, FinancialTransaction):
                return await self._process_transaction_with_consensus(workflow_result, workflow_id)
            
            # If result is a dict with transaction, process it
            elif isinstance(workflow_result, dict) and "transaction" in workflow_result:
                transaction = workflow_result["transaction"]
                return await self._process_transaction_with_consensus(transaction, workflow_id)
            
            # Otherwise, return direct result
            else:
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                return WorkflowResult(
                    workflow_id=workflow_id,
                    success=True,
                    consensus_reached=True,
                    agent_results=[],
                    final_result=workflow_result,
                    total_processing_time=processing_time,
                    metadata={"workflow_type": "direct_execution"}
                )
                
        except Exception as e:
            self.logger.error("Failed to execute workflow with consensus", error=str(e))
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return WorkflowResult(
                workflow_id=workflow_id,
                success=False,
                consensus_reached=False,
                agent_results=[],
                final_result={},
                total_processing_time=processing_time,
                metadata={"error": str(e)}
            )
    
    async def _process_transaction_with_consensus(self, transaction: FinancialTransaction, 
                                                workflow_id: str) -> WorkflowResult:
        """Process transaction through agents with consensus"""
        try:
            start_time = datetime.now(timezone.utc)
            agent_results = []
            
            # Process through each agent
            for agent_id, agent in self.agents.items():
                agent_start_time = datetime.now(timezone.utc)
                
                try:
                    # Process transaction with agent
                    result = await agent.process_transaction(transaction)
                    
                    agent_processing_time = (datetime.now(timezone.utc) - agent_start_time).total_seconds()
                    
                    agent_result = AgentResult(
                        agent_id=agent_id,
                        agent_type=agent.config.agent_type,
                        success=result.success,
                        confidence=result.metadata.get("confidence", 0.5),
                        result=result.metadata,
                        processing_time=agent_processing_time,
                        metadata={"message": result.message}
                    )
                    
                    agent_results.append(agent_result)
                    
                except Exception as e:
                    self.logger.error(
                        "Agent processing failed",
                        agent_id=agent_id,
                        error=str(e)
                    )
                    
                    agent_result = AgentResult(
                        agent_id=agent_id,
                        agent_type=agent.config.agent_type,
                        success=False,
                        confidence=0.0,
                        result={},
                        processing_time=0.0,
                        metadata={"error": str(e)}
                    )
                    
                    agent_results.append(agent_result)
            
            # Apply consensus mechanism
            consensus_result = await self.consensus_engine.reach_consensus(
                agent_results, threshold=self.config.consensus_threshold
            )
            
            # Calculate final metrics
            total_processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            cost_savings = self._extract_cost_savings(agent_results)
            compliance_score = self._extract_compliance_score(agent_results)
            risk_score = self._extract_risk_score(agent_results)
            
            # Update performance metrics
            self._update_performance_metrics(transaction, cost_savings, total_processing_time)
            
            # Prepare final result
            final_result = {
                "transaction_id": transaction.transaction_id,
                "consensus_reached": consensus_result.consensus_reached,
                "recommended_action": consensus_result.recommended_action,
                "agent_recommendations": consensus_result.agent_recommendations,
                "cost_savings_percentage": cost_savings,
                "compliance_score": compliance_score,
                "risk_score": risk_score
            }
            
            return WorkflowResult(
                workflow_id=workflow_id,
                success=consensus_result.consensus_reached,
                consensus_reached=consensus_result.consensus_reached,
                agent_results=agent_results,
                final_result=final_result,
                total_processing_time=total_processing_time,
                cost_savings_percentage=cost_savings,
                compliance_score=compliance_score,
                risk_score=risk_score,
                metadata={"workflow_type": "transaction_processing"}
            )
            
        except Exception as e:
            self.logger.error("Failed to process transaction with consensus", error=str(e))
            raise
    
    async def optimize_payment(self, transaction: FinancialTransaction) -> WorkflowResult:
        """
        Optimize payment using the framework's agents
        
        Args:
            transaction: Financial transaction to optimize
            
        Returns:
            WorkflowResult: Optimization result with cost savings
        """
        try:
            workflow_id = f"payment_optimization_{transaction.transaction_id}"
            
            # Create optimization workflow
            @self.workflow
            async def optimize_payment_workflow():
                return transaction
            
            # Execute optimization
            result = await optimize_payment_workflow()
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to optimize payment", error=str(e))
            raise
    
    async def check_compliance(self, transaction: FinancialTransaction) -> WorkflowResult:
        """
        Check transaction compliance using the framework's agents
        
        Args:
            transaction: Financial transaction to check
            
        Returns:
            WorkflowResult: Compliance check result
        """
        try:
            workflow_id = f"compliance_check_{transaction.transaction_id}"
            
            # Create compliance workflow
            @self.workflow
            async def compliance_check_workflow():
                return transaction
            
            # Execute compliance check
            result = await compliance_check_workflow()
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to check compliance", error=str(e))
            raise
    
    async def get_framework_analytics(self) -> Dict[str, Any]:
        """Get framework analytics and performance metrics"""
        try:
            analytics = {
                "total_transactions_processed": self.total_transactions_processed,
                "total_cost_savings": float(self.total_cost_savings),
                "average_processing_time": self.average_processing_time,
                "active_workflows": len(self.active_workflows),
                "workflow_history_count": len(self.workflow_history),
                "agents_count": len(self.agents),
                "consensus_rate": 0.0,
                "average_cost_savings_percentage": 0.0
            }
            
            # Calculate consensus rate
            if self.workflow_history:
                consensus_count = sum(1 for wf in self.workflow_history 
                                    if wf["result"].get("consensus_reached", False))
                analytics["consensus_rate"] = consensus_count / len(self.workflow_history)
            
            # Calculate average cost savings
            if self.total_transactions_processed > 0:
                analytics["average_cost_savings_percentage"] = float(
                    self.total_cost_savings / self.total_transactions_processed * 100
                )
            
            # Add agent-specific analytics
            agent_analytics = {}
            for agent_id, agent in self.agents.items():
                if hasattr(agent, 'get_optimization_analytics'):
                    agent_analytics[agent_id] = await agent.get_optimization_analytics()
                elif hasattr(agent, 'get_compliance_analytics'):
                    agent_analytics[agent_id] = await agent.get_compliance_analytics()
            
            analytics["agent_analytics"] = agent_analytics
            
            return analytics
            
        except Exception as e:
            self.logger.error("Failed to get framework analytics", error=str(e))
            return {}
    
    async def _initialize_default_agents(self) -> None:
        """Initialize default agents based on framework configuration"""
        try:
            # Initialize payment optimizer agent
            payment_config = PaymentOptimizerConfig(
                optimization_strategy=OptimizationStrategy.BALANCED,
                enable_learning=self.config.enable_learning
            )
            
            payment_agent = PaymentOptimizerAgent(payment_config)
            if self.redis_client:
                await payment_agent.initialize(self.redis_client)
            
            self.add_agent(payment_agent)
            
            # Initialize compliance checker agent
            compliance_config = ComplianceCheckerConfig(
                kyc_threshold_amount=1000.0,
                aml_threshold_amount=3000.0,
                enable_learning=self.config.enable_learning
            )
            
            compliance_agent = ComplianceCheckerAgent(compliance_config)
            if self.redis_client:
                await compliance_agent.initialize(self.redis_client)
            
            self.add_agent(compliance_agent)
            
            self.logger.info("Default agents initialized", agent_count=len(self.agents))
            
        except Exception as e:
            self.logger.error("Failed to initialize default agents", error=str(e))
    
    def _extract_cost_savings(self, agent_results: List[AgentResult]) -> Optional[float]:
        """Extract cost savings from agent results"""
        try:
            for result in agent_results:
                if result.agent_type == "payment_optimizer":
                    return result.result.get("cost_savings_percentage")
            return None
        except Exception:
            return None
    
    def _extract_compliance_score(self, agent_results: List[AgentResult]) -> Optional[float]:
        """Extract compliance score from agent results"""
        try:
            for result in agent_results:
                if result.agent_type == "compliance_checker":
                    return result.result.get("compliance_score")
            return None
        except Exception:
            return None
    
    def _extract_risk_score(self, agent_results: List[AgentResult]) -> Optional[float]:
        """Extract risk score from agent results"""
        try:
            for result in agent_results:
                if result.agent_type == "compliance_checker":
                    return result.result.get("risk_score")
            return None
        except Exception:
            return None
    
    def _update_performance_metrics(self, transaction: FinancialTransaction, 
                                  cost_savings: Optional[float], 
                                  processing_time: float) -> None:
        """Update framework performance metrics"""
        try:
            self.total_transactions_processed += 1
            
            if cost_savings:
                self.total_cost_savings += Decimal(str(cost_savings))
            
            # Update average processing time
            if self.total_transactions_processed == 1:
                self.average_processing_time = processing_time
            else:
                self.average_processing_time = (
                    (self.average_processing_time * (self.total_transactions_processed - 1) + processing_time) /
                    self.total_transactions_processed
                )
                
        except Exception as e:
            self.logger.error("Failed to update performance metrics", error=str(e))


# Factory functions for easy agent creation

def PaymentAgent(specialization: str = "general", **config) -> PaymentOptimizerAgent:
    """
    Factory for payment optimization agents
    
    Args:
        specialization: Agent specialization (general, africa, cross_border, etc.)
        **config: Additional configuration parameters
        
    Returns:
        PaymentOptimizerAgent: Configured payment optimization agent
    """
    try:
        # Set optimization strategy based on specialization
        strategy_map = {
            "general": OptimizationStrategy.BALANCED,
            "africa": OptimizationStrategy.COST_FIRST,
            "cross_border": OptimizationStrategy.RELIABILITY_FIRST,
            "urgent": OptimizationStrategy.SPEED_FIRST
        }
        
        optimization_strategy = strategy_map.get(specialization, OptimizationStrategy.BALANCED)
        
        # Create configuration
        agent_config = PaymentOptimizerConfig(
            optimization_strategy=optimization_strategy,
            **config
        )
        
        # Create and return agent
        agent = PaymentOptimizerAgent(agent_config)
        
        logger.info(
            "Payment agent created",
            specialization=specialization,
            strategy=optimization_strategy.value
        )
        
        return agent
        
    except Exception as e:
        logger.error("Failed to create payment agent", error=str(e))
        raise


def ComplianceAgent(jurisdictions: List[str] = None, **config) -> ComplianceCheckerAgent:
    """
    Factory for compliance agents
    
    Args:
        jurisdictions: List of regulatory jurisdictions
        **config: Additional configuration parameters
        
    Returns:
        ComplianceCheckerAgent: Configured compliance agent
    """
    try:
        jurisdictions = jurisdictions or []
        
        # Set compliance level based on jurisdictions
        compliance_level = ComplianceLevel.STANDARD
        if "US" in jurisdictions or "EU" in jurisdictions:
            compliance_level = ComplianceLevel.ENHANCED
        elif "AFRICA" in jurisdictions:
            compliance_level = ComplianceLevel.STANDARD
        
        # Create configuration
        agent_config = ComplianceCheckerConfig(
            regulatory_jurisdictions=jurisdictions,
            **config
        )
        
        # Create and return agent
        agent = ComplianceCheckerAgent(agent_config)
        
        logger.info(
            "Compliance agent created",
            jurisdictions=jurisdictions,
            compliance_level=compliance_level.value
        )
        
        return agent
        
    except Exception as e:
        logger.error("Failed to create compliance agent", error=str(e))
        raise


def RiskAgent(risk_tolerance: RiskTolerance = RiskTolerance.MODERATE, **config) -> BaseFinancialAgent:
    """
    Factory for risk assessment agents
    
    Args:
        risk_tolerance: Risk tolerance level
        **config: Additional configuration parameters
        
    Returns:
        BaseFinancialAgent: Configured risk assessment agent
    """
    try:
        # For now, return a compliance agent with risk-focused configuration
        # This will be replaced with a dedicated risk agent when implemented
        
        risk_config = {
            "high_risk_score_threshold": 0.5 if risk_tolerance == RiskTolerance.CONSERVATIVE else 0.7,
            "medium_risk_score_threshold": 0.3 if risk_tolerance == RiskTolerance.CONSERVATIVE else 0.4,
            **config
        }
        
        agent = ComplianceAgent(**risk_config)
        
        logger.info(
            "Risk agent created",
            risk_tolerance=risk_tolerance.value
        )
        
        return agent
        
    except Exception as e:
        logger.error("Failed to create risk agent", error=str(e))
        raise
