"""
Agent coordination for financial orchestration

This module provides agent coordination capabilities including load balancing,
agent selection, and inter-agent communication.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import random

import structlog
from pydantic import BaseModel, Field

from packages.core.agents.base import BaseFinancialAgent, AgentRegistry, ProcessingResult
from packages.core.agents.financial_base import FinancialTransaction


logger = structlog.get_logger(__name__)


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"
    PERFORMANCE_BASED = "performance_based"


class AgentSelectionCriteria(BaseModel):
    """Criteria for agent selection"""
    agent_type: str
    min_agents: int = 1
    max_agents: int = 5
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    performance_threshold: float = 0.8
    max_processing_time: float = 30.0
    required_capabilities: List[str] = Field(default_factory=list)


class AgentCoordinator:
    """
    Agent coordinator for managing agent interactions and load balancing
    
    This class provides capabilities for:
    - Agent selection and load balancing
    - Inter-agent communication
    - Performance monitoring and optimization
    - Agent health management
    """
    
    def __init__(self, agent_registry: AgentRegistry):
        self.agent_registry = agent_registry
        self.logger = structlog.get_logger(__name__)
        
        # Load balancing state
        self._round_robin_counters: Dict[str, int] = {}
        self._agent_usage_count: Dict[str, int] = {}
        self._agent_performance: Dict[str, float] = {}
        
        # Coordination state
        self._active_transactions: Dict[str, List[str]] = {}  # transaction_id -> agent_ids
        self._agent_transactions: Dict[str, List[str]] = {}   # agent_id -> transaction_ids
        
        self.logger.info("Agent coordinator initialized")
    
    async def select_agents(
        self, 
        criteria: AgentSelectionCriteria,
        transaction: FinancialTransaction
    ) -> List[BaseFinancialAgent]:
        """
        Select agents based on criteria
        
        Args:
            criteria: Selection criteria
            transaction: The transaction to process
            
        Returns:
            List of selected agents
        """
        try:
            # Get available agents of the specified type
            available_agents = self.agent_registry.get_agents_by_type(criteria.agent_type)
            
            if not available_agents:
                self.logger.warning(f"No agents available for type: {criteria.agent_type}")
                return []
            
            # Filter agents based on criteria
            filtered_agents = await self._filter_agents_by_criteria(available_agents, criteria, transaction)
            
            if not filtered_agents:
                self.logger.warning(f"No agents meet criteria for type: {criteria.agent_type}")
                return []
            
            # Apply load balancing strategy
            selected_agents = await self._apply_load_balancing(
                filtered_agents, 
                criteria.load_balancing_strategy,
                criteria.min_agents,
                criteria.max_agents
            )
            
            self.logger.info(
                "Agents selected",
                agent_type=criteria.agent_type,
                selected_count=len(selected_agents),
                strategy=criteria.load_balancing_strategy
            )
            
            return selected_agents
            
        except Exception as e:
            self.logger.error("Failed to select agents", error=str(e))
            return []
    
    async def _filter_agents_by_criteria(
        self, 
        agents: List[BaseFinancialAgent], 
        criteria: AgentSelectionCriteria,
        transaction: FinancialTransaction
    ) -> List[BaseFinancialAgent]:
        """Filter agents based on selection criteria"""
        try:
            filtered_agents = []
            
            for agent in agents:
                # Check if agent is healthy
                health_status = await agent.get_health_status()
                if health_status.get("status") != "idle":
                    continue
                
                # Check performance threshold
                success_rate = health_status.get("success_rate", 0.0)
                if success_rate < criteria.performance_threshold:
                    continue
                
                # Check processing time
                avg_processing_time = health_status.get("average_processing_time", 0.0)
                if avg_processing_time > criteria.max_processing_time:
                    continue
                
                # Check capabilities (if specified)
                if criteria.required_capabilities:
                    agent_capabilities = getattr(agent, 'capabilities', [])
                    if not all(cap in agent_capabilities for cap in criteria.required_capabilities):
                        continue
                
                # Check if agent can handle the transaction
                if not await agent.validate_transaction(transaction):
                    continue
                
                filtered_agents.append(agent)
            
            return filtered_agents
            
        except Exception as e:
            self.logger.error("Failed to filter agents by criteria", error=str(e))
            return []
    
    async def _apply_load_balancing(
        self, 
        agents: List[BaseFinancialAgent], 
        strategy: LoadBalancingStrategy,
        min_agents: int,
        max_agents: int
    ) -> List[BaseFinancialAgent]:
        """Apply load balancing strategy to select agents"""
        try:
            if strategy == LoadBalancingStrategy.ROUND_ROBIN:
                return await self._round_robin_selection(agents, min_agents, max_agents)
            elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                return await self._least_connections_selection(agents, min_agents, max_agents)
            elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                return await self._weighted_round_robin_selection(agents, min_agents, max_agents)
            elif strategy == LoadBalancingStrategy.RANDOM:
                return await self._random_selection(agents, min_agents, max_agents)
            elif strategy == LoadBalancingStrategy.PERFORMANCE_BASED:
                return await self._performance_based_selection(agents, min_agents, max_agents)
            else:
                raise ValueError(f"Unknown load balancing strategy: {strategy}")
                
        except Exception as e:
            self.logger.error("Failed to apply load balancing", error=str(e))
            return agents[:min_agents] if agents else []
    
    async def _round_robin_selection(
        self, 
        agents: List[BaseFinancialAgent], 
        min_agents: int,
        max_agents: int
    ) -> List[BaseFinancialAgent]:
        """Round robin agent selection"""
        try:
            agent_type = agents[0].agent_type if agents else ""
            
            # Initialize counter if not exists
            if agent_type not in self._round_robin_counters:
                self._round_robin_counters[agent_type] = 0
            
            # Select agents using round robin
            selected_agents = []
            num_agents = min(len(agents), max_agents)
            
            for i in range(num_agents):
                index = (self._round_robin_counters[agent_type] + i) % len(agents)
                selected_agents.append(agents[index])
            
            # Update counter
            self._round_robin_counters[agent_type] = (self._round_robin_counters[agent_type] + num_agents) % len(agents)
            
            return selected_agents
            
        except Exception as e:
            self.logger.error("Round robin selection failed", error=str(e))
            return agents[:min_agents] if agents else []
    
    async def _least_connections_selection(
        self, 
        agents: List[BaseFinancialAgent], 
        min_agents: int,
        max_agents: int
    ) -> List[BaseFinancialAgent]:
        """Least connections agent selection"""
        try:
            # Get current task count for each agent
            agent_loads = []
            for agent in agents:
                health_status = await agent.get_health_status()
                current_tasks = health_status.get("current_tasks", 0)
                agent_loads.append((agent, current_tasks))
            
            # Sort by current tasks (least first)
            agent_loads.sort(key=lambda x: x[1])
            
            # Select agents with least connections
            num_agents = min(len(agents), max_agents)
            selected_agents = [agent for agent, _ in agent_loads[:num_agents]]
            
            return selected_agents
            
        except Exception as e:
            self.logger.error("Least connections selection failed", error=str(e))
            return agents[:min_agents] if agents else []
    
    async def _weighted_round_robin_selection(
        self, 
        agents: List[BaseFinancialAgent], 
        min_agents: int,
        max_agents: int
    ) -> List[BaseFinancialAgent]:
        """Weighted round robin agent selection"""
        try:
            # Calculate weights based on performance
            agent_weights = []
            for agent in agents:
                health_status = await agent.get_health_status()
                success_rate = health_status.get("success_rate", 0.5)
                avg_processing_time = health_status.get("average_processing_time", 1.0)
                
                # Weight based on success rate and processing time
                weight = success_rate / max(avg_processing_time, 0.1)
                agent_weights.append((agent, weight))
            
            # Sort by weight (highest first)
            agent_weights.sort(key=lambda x: x[1], reverse=True)
            
            # Select top agents
            num_agents = min(len(agents), max_agents)
            selected_agents = [agent for agent, _ in agent_weights[:num_agents]]
            
            return selected_agents
            
        except Exception as e:
            self.logger.error("Weighted round robin selection failed", error=str(e))
            return agents[:min_agents] if agents else []
    
    async def _random_selection(
        self, 
        agents: List[BaseFinancialAgent], 
        min_agents: int,
        max_agents: int
    ) -> List[BaseFinancialAgent]:
        """Random agent selection"""
        try:
            num_agents = min(len(agents), max_agents)
            selected_agents = random.sample(agents, num_agents)
            return selected_agents
            
        except Exception as e:
            self.logger.error("Random selection failed", error=str(e))
            return agents[:min_agents] if agents else []
    
    async def _performance_based_selection(
        self, 
        agents: List[BaseFinancialAgent], 
        min_agents: int,
        max_agents: int
    ) -> List[BaseFinancialAgent]:
        """Performance-based agent selection"""
        try:
            # Get performance metrics for each agent
            agent_performance = []
            for agent in agents:
                health_status = await agent.get_health_status()
                success_rate = health_status.get("success_rate", 0.0)
                avg_processing_time = health_status.get("average_processing_time", 1.0)
                
                # Calculate performance score
                performance_score = success_rate / max(avg_processing_time, 0.1)
                agent_performance.append((agent, performance_score))
            
            # Sort by performance score (highest first)
            agent_performance.sort(key=lambda x: x[1], reverse=True)
            
            # Select top performing agents
            num_agents = min(len(agents), max_agents)
            selected_agents = [agent for agent, _ in agent_performance[:num_agents]]
            
            return selected_agents
            
        except Exception as e:
            self.logger.error("Performance-based selection failed", error=str(e))
            return agents[:min_agents] if agents else []
    
    async def coordinate_transaction(
        self, 
        transaction: FinancialTransaction,
        agents: List[BaseFinancialAgent]
    ) -> List[ProcessingResult]:
        """
        Coordinate multiple agents for a transaction
        
        Args:
            transaction: The transaction to process
            agents: List of agents to coordinate
            
        Returns:
            List of processing results from all agents
        """
        try:
            transaction_id = transaction.id
            
            # Record transaction assignment
            self._active_transactions[transaction_id] = [agent.agent_id for agent in agents]
            for agent in agents:
                if agent.agent_id not in self._agent_transactions:
                    self._agent_transactions[agent.agent_id] = []
                self._agent_transactions[agent.agent_id].append(transaction_id)
            
            self.logger.info(
                "Coordinating transaction",
                transaction_id=transaction_id,
                agent_count=len(agents)
            )
            
            # Process with all agents concurrently
            tasks = [agent.process_transaction_with_retry(transaction) for agent in agents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(
                        "Agent processing failed",
                        agent_id=agents[i].agent_id,
                        error=str(result)
                    )
                    # Create error result
                    error_result = ProcessingResult(
                        success=False,
                        transaction_id=transaction_id,
                        status="failed",
                        message=f"Agent processing failed: {str(result)}",
                        error_code="AGENT_ERROR"
                    )
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)
            
            # Clean up transaction assignment
            await self._cleanup_transaction_assignment(transaction_id)
            
            return processed_results
            
        except Exception as e:
            self.logger.error("Transaction coordination failed", error=str(e))
            return []
    
    async def _cleanup_transaction_assignment(self, transaction_id: str) -> None:
        """Clean up transaction assignment records"""
        try:
            if transaction_id in self._active_transactions:
                agent_ids = self._active_transactions[transaction_id]
                for agent_id in agent_ids:
                    if agent_id in self._agent_transactions:
                        self._agent_transactions[agent_id] = [
                            tx_id for tx_id in self._agent_transactions[agent_id] 
                            if tx_id != transaction_id
                        ]
                del self._active_transactions[transaction_id]
                
        except Exception as e:
            self.logger.error("Failed to cleanup transaction assignment", error=str(e))
    
    async def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get coordination metrics"""
        try:
            return {
                "active_transactions": len(self._active_transactions),
                "agent_assignments": {
                    agent_id: len(transactions) 
                    for agent_id, transactions in self._agent_transactions.items()
                },
                "round_robin_counters": self._round_robin_counters,
                "agent_usage_count": self._agent_usage_count,
                "agent_performance": self._agent_performance
            }
        except Exception as e:
            self.logger.error("Failed to get coordination metrics", error=str(e))
            return {"error": str(e)}
    
    async def optimize_agent_allocation(self) -> Dict[str, Any]:
        """Optimize agent allocation based on current metrics"""
        try:
            # Get current agent health status
            agent_health = await self.agent_registry.get_all_health_status()
            
            # Analyze performance patterns
            performance_analysis = {}
            for agent_id, health in agent_health.items():
                success_rate = health.get("success_rate", 0.0)
                avg_processing_time = health.get("average_processing_time", 0.0)
                current_tasks = health.get("current_tasks", 0)
                
                # Calculate efficiency score
                efficiency_score = success_rate / max(avg_processing_time, 0.1)
                
                performance_analysis[agent_id] = {
                    "efficiency_score": efficiency_score,
                    "success_rate": success_rate,
                    "avg_processing_time": avg_processing_time,
                    "current_tasks": current_tasks,
                    "recommendation": "optimal" if efficiency_score > 0.8 else "needs_attention"
                }
            
            return {
                "performance_analysis": performance_analysis,
                "recommendations": {
                    "high_performers": [
                        agent_id for agent_id, analysis in performance_analysis.items()
                        if analysis["efficiency_score"] > 0.9
                    ],
                    "needs_attention": [
                        agent_id for agent_id, analysis in performance_analysis.items()
                        if analysis["efficiency_score"] < 0.5
                    ]
                }
            }
            
        except Exception as e:
            self.logger.error("Failed to optimize agent allocation", error=str(e))
            return {"error": str(e)} 