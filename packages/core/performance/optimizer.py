"""
Performance optimizer for orchestration system

This module provides automatic performance optimization capabilities
for the orchestration system based on metrics and patterns.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
import statistics

import structlog
from pydantic import BaseModel, Field

from packages.core.performance.tracker import PerformanceTracker
from packages.core.performance.metrics import MetricsCollector
from packages.core.orchestration.orchestrator import FinancialOrchestrator, OrchestrationConfig

logger = structlog.get_logger(__name__)


class OptimizationStrategy(str, Enum):
    """Types of optimization strategies"""
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    RESOURCE_UTILIZATION = "resource_utilization"
    COST_EFFICIENCY = "cost_efficiency"
    BALANCED = "balanced"


class OptimizationAction(str, Enum):
    """Types of optimization actions"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    ADJUST_TIMEOUT = "adjust_timeout"
    ADJUST_RETRY = "adjust_retry"
    ADJUST_BATCH_SIZE = "adjust_batch_size"
    ADJUST_CONCURRENCY = "adjust_concurrency"
    SWITCH_ALGORITHM = "switch_algorithm"
    RECONFIGURE_AGENTS = "reconfigure_agents"


class OptimizationRule(BaseModel):
    """Rule for performance optimization"""
    rule_id: str
    name: str
    description: str
    condition: Dict[str, Any]
    action: OptimizationAction
    action_params: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 1
    enabled: bool = True
    cooldown_period: float = 300.0  # seconds
    last_triggered: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OptimizationResult(BaseModel):
    """Result of an optimization action"""
    rule_id: str
    action: OptimizationAction
    success: bool
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    impact_score: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PerformanceOptimizer:
    """
    Performance optimizer for orchestration system
    
    This class provides automatic performance optimization capabilities
    based on metrics analysis and predefined rules.
    """
    
    def __init__(self, 
                 performance_tracker: PerformanceTracker,
                 metrics_collector: MetricsCollector,
                 orchestrator: FinancialOrchestrator):
        self.performance_tracker = performance_tracker
        self.metrics_collector = metrics_collector
        self.orchestrator = orchestrator
        self.logger = structlog.get_logger(__name__)
        
        # Optimization rules
        self.optimization_rules: Dict[str, OptimizationRule] = {}
        
        # Optimization history
        self.optimization_history: List[OptimizationResult] = []
        
        # Current strategy
        self.current_strategy = OptimizationStrategy.BALANCED
        
        # Optimization task
        self.optimization_task: Optional[asyncio.Task] = None
        
        # Initialize default rules
        self._initialize_default_rules()
        
        self.logger.info("Performance optimizer initialized")
    
    def _initialize_default_rules(self) -> None:
        """Initialize default optimization rules"""
        default_rules = [
            OptimizationRule(
                rule_id="high_latency_scale_up",
                name="Scale up on high latency",
                description="Scale up agents when average latency exceeds threshold",
                condition={
                    "metric": "average_processing_time",
                    "threshold": 5.0,
                    "operator": ">",
                    "duration": 300  # 5 minutes
                },
                action=OptimizationAction.SCALE_UP,
                action_params={"scale_factor": 1.5},
                priority=1
            ),
            OptimizationRule(
                rule_id="low_throughput_scale_up",
                name="Scale up on low throughput",
                description="Scale up when throughput drops below threshold",
                condition={
                    "metric": "throughput_per_minute",
                    "threshold": 10.0,
                    "operator": "<",
                    "duration": 300
                },
                action=OptimizationAction.SCALE_UP,
                action_params={"scale_factor": 2.0},
                priority=1
            ),
            OptimizationRule(
                rule_id="high_error_rate_adjust",
                name="Adjust on high error rate",
                description="Adjust retry settings when error rate is high",
                condition={
                    "metric": "success_rate",
                    "threshold": 0.9,
                    "operator": "<",
                    "duration": 180
                },
                action=OptimizationAction.ADJUST_RETRY,
                action_params={"increase_retries": True, "increase_delay": True},
                priority=2
            ),
            OptimizationRule(
                rule_id="low_utilization_scale_down",
                name="Scale down on low utilization",
                description="Scale down when resource utilization is low",
                condition={
                    "metric": "resource_utilization",
                    "threshold": 0.3,
                    "operator": "<",
                    "duration": 600
                },
                action=OptimizationAction.SCALE_DOWN,
                action_params={"scale_factor": 0.7},
                priority=3
            )
        ]
        
        for rule in default_rules:
            self.add_optimization_rule(rule)
    
    def add_optimization_rule(self, rule: OptimizationRule) -> None:
        """
        Add an optimization rule
        
        Args:
            rule: Optimization rule to add
        """
        self.optimization_rules[rule.rule_id] = rule
        
        self.logger.info(
            "Optimization rule added",
            rule_id=rule.rule_id,
            name=rule.name,
            action=rule.action
        )
    
    def remove_optimization_rule(self, rule_id: str) -> bool:
        """
        Remove an optimization rule
        
        Args:
            rule_id: ID of the rule to remove
            
        Returns:
            bool: True if rule was removed
        """
        if rule_id in self.optimization_rules:
            del self.optimization_rules[rule_id]
            self.logger.info("Optimization rule removed", rule_id=rule_id)
            return True
        return False
    
    def set_optimization_strategy(self, strategy: OptimizationStrategy) -> None:
        """
        Set the optimization strategy
        
        Args:
            strategy: Optimization strategy to use
        """
        self.current_strategy = strategy
        
        self.logger.info(
            "Optimization strategy changed",
            strategy=strategy
        )
    
    async def start_optimization(self, interval: float = 60.0) -> None:
        """
        Start the optimization process
        
        Args:
            interval: Optimization check interval in seconds
        """
        if self.optimization_task is None or self.optimization_task.done():
            self.optimization_task = asyncio.create_task(self._optimization_loop(interval))
            
            self.logger.info(
                "Performance optimization started",
                interval=interval
            )
    
    async def stop_optimization(self) -> None:
        """Stop the optimization process"""
        if self.optimization_task and not self.optimization_task.done():
            self.optimization_task.cancel()
            try:
                await self.optimization_task
            except asyncio.CancelledError:
                pass
            
            self.logger.info("Performance optimization stopped")
    
    async def _optimization_loop(self, interval: float) -> None:
        """Main optimization loop"""
        while True:
            try:
                await self._run_optimization_cycle()
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(
                    "Error in optimization loop",
                    error=str(e)
                )
                await asyncio.sleep(10.0)  # Short delay on error
    
    async def _run_optimization_cycle(self) -> None:
        """Run a single optimization cycle"""
        # Get current performance metrics
        metrics = await self.performance_tracker.get_metrics()
        
        # Check each optimization rule
        for rule in self.optimization_rules.values():
            if not rule.enabled:
                continue
            
            # Check cooldown period
            if rule.last_triggered:
                time_since_last = (datetime.now(timezone.utc) - rule.last_triggered).total_seconds()
                if time_since_last < rule.cooldown_period:
                    continue
            
            # Check if rule condition is met
            if await self._evaluate_rule_condition(rule, metrics):
                # Execute optimization action
                result = await self._execute_optimization_action(rule)
                
                if result.success:
                    rule.last_triggered = datetime.now(timezone.utc)
                    self.optimization_history.append(result)
                    
                    self.logger.info(
                        "Optimization action executed",
                        rule_id=rule.rule_id,
                        action=rule.action,
                        impact_score=result.impact_score
                    )
    
    async def _evaluate_rule_condition(self, rule: OptimizationRule, metrics: Dict[str, Any]) -> bool:
        """
        Evaluate if a rule condition is met
        
        Args:
            rule: Optimization rule to evaluate
            metrics: Current performance metrics
            
        Returns:
            bool: True if condition is met
        """
        condition = rule.condition
        metric_name = condition.get("metric")
        threshold = condition.get("threshold")
        operator = condition.get("operator", ">")
        duration = condition.get("duration", 300)
        
        if not metric_name or threshold is None:
            return False
        
        # Get metric value
        metric_value = self._extract_metric_value(metrics, metric_name)
        if metric_value is None:
            return False
        
        # Apply operator
        if operator == ">":
            return metric_value > threshold
        elif operator == "<":
            return metric_value < threshold
        elif operator == ">=":
            return metric_value >= threshold
        elif operator == "<=":
            return metric_value <= threshold
        elif operator == "==":
            return metric_value == threshold
        else:
            return False
    
    def _extract_metric_value(self, metrics: Dict[str, Any], metric_name: str) -> Optional[float]:
        """
        Extract metric value from metrics dictionary
        
        Args:
            metrics: Metrics dictionary
            metric_name: Name of the metric to extract
            
        Returns:
            float: Metric value if found
        """
        # Handle nested metric paths
        if "." in metric_name:
            parts = metric_name.split(".")
            value = metrics
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            return float(value) if value is not None else None
        
        # Direct metric access
        if metric_name in metrics:
            return float(metrics[metric_name])
        
        return None
    
    async def _execute_optimization_action(self, rule: OptimizationRule) -> OptimizationResult:
        """
        Execute an optimization action
        
        Args:
            rule: Optimization rule to execute
            
        Returns:
            OptimizationResult: Result of the optimization action
        """
        try:
            if rule.action == OptimizationAction.SCALE_UP:
                return await self._scale_up(rule)
            elif rule.action == OptimizationAction.SCALE_DOWN:
                return await self._scale_down(rule)
            elif rule.action == OptimizationAction.ADJUST_TIMEOUT:
                return await self._adjust_timeout(rule)
            elif rule.action == OptimizationAction.ADJUST_RETRY:
                return await self._adjust_retry(rule)
            elif rule.action == OptimizationAction.ADJUST_BATCH_SIZE:
                return await self._adjust_batch_size(rule)
            elif rule.action == OptimizationAction.ADJUST_CONCURRENCY:
                return await self._adjust_concurrency(rule)
            else:
                return OptimizationResult(
                    rule_id=rule.rule_id,
                    action=rule.action,
                    success=False,
                    metadata={"error": "Unknown action"}
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to execute optimization action",
                rule_id=rule.rule_id,
                action=rule.action,
                error=str(e)
            )
            
            return OptimizationResult(
                rule_id=rule.rule_id,
                action=rule.action,
                success=False,
                metadata={"error": str(e)}
            )
    
    async def _scale_up(self, rule: OptimizationRule) -> OptimizationResult:
        """Scale up the system"""
        scale_factor = rule.action_params.get("scale_factor", 1.5)
        
        # Get current configuration
        current_config = self.orchestrator.config
        
        # Calculate new values
        new_max_concurrent = int(current_config.max_concurrent_transactions * scale_factor)
        
        # Create new configuration
        new_config = OrchestrationConfig(
            max_concurrent_transactions=new_max_concurrent,
            transaction_timeout=current_config.transaction_timeout,
            retry_attempts=current_config.retry_attempts,
            retry_delay=current_config.retry_delay
        )
        
        # Apply new configuration
        self.orchestrator.config = new_config
        
        return OptimizationResult(
            rule_id=rule.rule_id,
            action=rule.action,
            success=True,
            old_value=current_config.max_concurrent_transactions,
            new_value=new_max_concurrent,
            impact_score=0.8
        )
    
    async def _scale_down(self, rule: OptimizationRule) -> OptimizationResult:
        """Scale down the system"""
        scale_factor = rule.action_params.get("scale_factor", 0.7)
        
        # Get current configuration
        current_config = self.orchestrator.config
        
        # Calculate new values
        new_max_concurrent = max(1, int(current_config.max_concurrent_transactions * scale_factor))
        
        # Create new configuration
        new_config = OrchestrationConfig(
            max_concurrent_transactions=new_max_concurrent,
            transaction_timeout=current_config.transaction_timeout,
            retry_attempts=current_config.retry_attempts,
            retry_delay=current_config.retry_delay
        )
        
        # Apply new configuration
        self.orchestrator.config = new_config
        
        return OptimizationResult(
            rule_id=rule.rule_id,
            action=rule.action,
            success=True,
            old_value=current_config.max_concurrent_transactions,
            new_value=new_max_concurrent,
            impact_score=0.6
        )
    
    async def _adjust_timeout(self, rule: OptimizationRule) -> OptimizationResult:
        """Adjust timeout settings"""
        timeout_factor = rule.action_params.get("timeout_factor", 1.2)
        
        # Get current configuration
        current_config = self.orchestrator.config
        
        # Calculate new timeout
        new_timeout = current_config.transaction_timeout * timeout_factor
        
        # Create new configuration
        new_config = OrchestrationConfig(
            max_concurrent_transactions=current_config.max_concurrent_transactions,
            transaction_timeout=new_timeout,
            retry_attempts=current_config.retry_attempts,
            retry_delay=current_config.retry_delay
        )
        
        # Apply new configuration
        self.orchestrator.config = new_config
        
        return OptimizationResult(
            rule_id=rule.rule_id,
            action=rule.action,
            success=True,
            old_value=current_config.transaction_timeout,
            new_value=new_timeout,
            impact_score=0.5
        )
    
    async def _adjust_retry(self, rule: OptimizationRule) -> OptimizationResult:
        """Adjust retry settings"""
        increase_retries = rule.action_params.get("increase_retries", False)
        increase_delay = rule.action_params.get("increase_delay", False)
        
        # Get current configuration
        current_config = self.orchestrator.config
        
        # Calculate new values
        new_retry_attempts = current_config.retry_attempts
        new_retry_delay = current_config.retry_delay
        
        if increase_retries:
            new_retry_attempts = min(10, current_config.retry_attempts + 1)
        
        if increase_delay:
            new_retry_delay = min(10.0, current_config.retry_delay * 1.5)
        
        # Create new configuration
        new_config = OrchestrationConfig(
            max_concurrent_transactions=current_config.max_concurrent_transactions,
            transaction_timeout=current_config.transaction_timeout,
            retry_attempts=new_retry_attempts,
            retry_delay=new_retry_delay
        )
        
        # Apply new configuration
        self.orchestrator.config = new_config
        
        return OptimizationResult(
            rule_id=rule.rule_id,
            action=rule.action,
            success=True,
            old_value={"retry_attempts": current_config.retry_attempts, "retry_delay": current_config.retry_delay},
            new_value={"retry_attempts": new_retry_attempts, "retry_delay": new_retry_delay},
            impact_score=0.4
        )
    
    async def _adjust_batch_size(self, rule: OptimizationRule) -> OptimizationResult:
        """Adjust batch size settings"""
        # This would typically adjust agent batch sizes
        # For now, we'll return a placeholder result
        return OptimizationResult(
            rule_id=rule.rule_id,
            action=rule.action,
            success=True,
            impact_score=0.3
        )
    
    async def _adjust_concurrency(self, rule: OptimizationRule) -> OptimizationResult:
        """Adjust concurrency settings"""
        # This would typically adjust agent concurrency limits
        # For now, we'll return a placeholder result
        return OptimizationResult(
            rule_id=rule.rule_id,
            action=rule.action,
            success=True,
            impact_score=0.3
        )
    
    async def get_optimization_summary(self) -> Dict[str, Any]:
        """
        Get optimization summary
        
        Returns:
            Dict[str, Any]: Optimization summary
        """
        total_rules = len(self.optimization_rules)
        enabled_rules = len([r for r in self.optimization_rules.values() if r.enabled])
        total_actions = len(self.optimization_history)
        
        # Calculate success rate
        successful_actions = len([r for r in self.optimization_history if r.success])
        success_rate = successful_actions / total_actions if total_actions > 0 else 0.0
        
        # Get recent actions
        recent_actions = self.optimization_history[-10:] if self.optimization_history else []
        
        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "success_rate": success_rate,
            "current_strategy": self.current_strategy,
            "recent_actions": [
                {
                    "rule_id": action.rule_id,
                    "action": action.action,
                    "success": action.success,
                    "impact_score": action.impact_score,
                    "timestamp": action.timestamp.isoformat()
                }
                for action in recent_actions
            ]
        }
    
    async def get_optimization_history(self, limit: int = 100) -> List[OptimizationResult]:
        """
        Get optimization history
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List[OptimizationResult]: Optimization history
        """
        return self.optimization_history[-limit:] if self.optimization_history else []
    
    async def reset_optimization_history(self) -> None:
        """Reset optimization history"""
        self.optimization_history.clear()
        self.logger.info("Optimization history reset")
    
    async def shutdown(self) -> None:
        """Shutdown the performance optimizer"""
        await self.stop_optimization()
        self.logger.info("Performance optimizer shutdown completed")


# Global performance optimizer instance
_performance_optimizer: Optional[PerformanceOptimizer] = None


def get_performance_optimizer(performance_tracker: Optional[PerformanceTracker] = None,
                             metrics_collector: Optional[MetricsCollector] = None,
                             orchestrator: Optional[FinancialOrchestrator] = None) -> Optional[PerformanceOptimizer]:
    """
    Get the global performance optimizer instance
    
    Args:
        performance_tracker: Performance tracker instance
        metrics_collector: Metrics collector instance
        orchestrator: Orchestrator instance
        
    Returns:
        PerformanceOptimizer: Global performance optimizer instance
    """
    global _performance_optimizer
    
    if _performance_optimizer is None:
        if not all([performance_tracker, metrics_collector, orchestrator]):
            return None
        
        _performance_optimizer = PerformanceOptimizer(
            performance_tracker=performance_tracker,
            metrics_collector=metrics_collector,
            orchestrator=orchestrator
        )
    
    return _performance_optimizer


def set_performance_optimizer(optimizer: PerformanceOptimizer) -> None:
    """
    Set the global performance optimizer instance
    
    Args:
        optimizer: Performance optimizer instance
    """
    global _performance_optimizer
    _performance_optimizer = optimizer
