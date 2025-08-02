"""
Agent factory for creating and managing financial agents

This module provides a factory pattern for creating different types of
financial agents dynamically based on configuration.
"""

import asyncio
from typing import Dict, List, Optional, Any, Type, TypeVar
from abc import ABC, abstractmethod

import structlog
from pydantic import BaseModel, Field

from packages.core.agents.base import BaseFinancialAgent, AgentConfig, AgentRegistry
from packages.core.agents.financial_base import FinancialTransaction

logger = structlog.get_logger(__name__)

T = TypeVar('T', bound=BaseFinancialAgent)


class AgentFactoryConfig(BaseModel):
    """Configuration for the agent factory"""
    auto_discovery: bool = True
    lazy_loading: bool = True
    max_agents_per_type: int = 10
    agent_pool_size: int = 100
    health_check_interval: float = 30.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentTemplate(BaseModel):
    """Template for creating agents"""
    agent_type: str
    agent_class: str
    config_template: Dict[str, Any]
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentPool(BaseModel):
    """Pool of agents for load balancing"""
    agent_type: str
    agents: List[BaseFinancialAgent] = Field(default_factory=list)
    max_size: int = 10
    current_index: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentFactory:
    """
    Factory for creating and managing financial agents
    
    This class provides a centralized way to create, configure, and manage
    different types of financial agents with features like:
    - Dynamic agent creation
    - Agent pooling and load balancing
    - Health monitoring
    - Configuration management
    """
    
    def __init__(self, config: AgentFactoryConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Agent registry and templates
        self.agent_registry = AgentRegistry()
        self.agent_templates: Dict[str, AgentTemplate] = {}
        self.agent_pools: Dict[str, AgentPool] = {}
        
        # Agent instances
        self.active_agents: Dict[str, BaseFinancialAgent] = {}
        self.agent_health: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.creation_count = 0
        self.destruction_count = 0
        
        self.logger.info("Agent factory initialized", config=config.dict())
    
    def register_agent_template(self, template: AgentTemplate) -> None:
        """
        Register an agent template
        
        Args:
            template: Agent template to register
        """
        self.agent_templates[template.agent_type] = template
        
        # Initialize agent pool if needed
        if template.agent_type not in self.agent_pools:
            self.agent_pools[template.agent_type] = AgentPool(
                agent_type=template.agent_type,
                max_size=self.config.max_agents_per_type
            )
        
        self.logger.info(
            "Agent template registered",
            agent_type=template.agent_type,
            agent_class=template.agent_class
        )
    
    def get_agent_template(self, agent_type: str) -> Optional[AgentTemplate]:
        """
        Get an agent template by type
        
        Args:
            agent_type: Type of agent template to retrieve
            
        Returns:
            AgentTemplate: Agent template if found
        """
        return self.agent_templates.get(agent_type)
    
    async def create_agent(self, agent_type: str, config: Optional[AgentConfig] = None) -> Optional[BaseFinancialAgent]:
        """
        Create a new agent instance
        
        Args:
            agent_type: Type of agent to create
            config: Agent configuration (optional)
            
        Returns:
            BaseFinancialAgent: Created agent instance
        """
        try:
            template = self.get_agent_template(agent_type)
            if not template:
                self.logger.error("Agent template not found", agent_type=agent_type)
                return None
            
            # Use template config if no config provided
            if config is None:
                config = AgentConfig(
                    agent_type=agent_type,
                    **template.config_template
                )
            
            # Create agent instance
            agent = self.agent_registry.create_agent(agent_type, config)
            
            # Add to active agents
            self.active_agents[agent.agent_id] = agent
            self.creation_count += 1
            
            # Initialize agent
            await agent.start()
            
            # Add to pool
            await self._add_to_pool(agent_type, agent)
            
            self.logger.info(
                "Agent created successfully",
                agent_id=agent.agent_id,
                agent_type=agent_type
            )
            
            return agent
            
        except Exception as e:
            self.logger.error(
                "Failed to create agent",
                agent_type=agent_type,
                error=str(e)
            )
            return None
    
    async def create_agent_pool(self, agent_type: str, pool_size: int) -> List[BaseFinancialAgent]:
        """
        Create a pool of agents
        
        Args:
            agent_type: Type of agents to create
            pool_size: Number of agents to create
            
        Returns:
            List[BaseFinancialAgent]: List of created agents
        """
        agents = []
        
        for i in range(pool_size):
            agent = await self.create_agent(agent_type)
            if agent:
                agents.append(agent)
            else:
                self.logger.warning(
                    "Failed to create agent in pool",
                    agent_type=agent_type,
                    index=i
                )
        
        self.logger.info(
            "Agent pool created",
            agent_type=agent_type,
            pool_size=len(agents),
            requested_size=pool_size
        )
        
        return agents
    
    async def get_agent(self, agent_type: str, strategy: str = "round_robin") -> Optional[BaseFinancialAgent]:
        """
        Get an agent from the pool
        
        Args:
            agent_type: Type of agent to get
            strategy: Load balancing strategy (round_robin, least_loaded, random)
            
        Returns:
            BaseFinancialAgent: Available agent
        """
        pool = self.agent_pools.get(agent_type)
        if not pool or not pool.agents:
            # Create a new agent if pool is empty
            return await self.create_agent(agent_type)
        
        if strategy == "round_robin":
            return await self._get_agent_round_robin(pool)
        elif strategy == "least_loaded":
            return await self._get_agent_least_loaded(pool)
        elif strategy == "random":
            return await self._get_agent_random(pool)
        else:
            self.logger.warning("Unknown strategy, using round_robin", strategy=strategy)
            return await self._get_agent_round_robin(pool)
    
    async def _get_agent_round_robin(self, pool: AgentPool) -> Optional[BaseFinancialAgent]:
        """Get agent using round-robin strategy"""
        if not pool.agents:
            return None
        
        agent = pool.agents[pool.current_index]
        pool.current_index = (pool.current_index + 1) % len(pool.agents)
        
        return agent
    
    async def _get_agent_least_loaded(self, pool: AgentPool) -> Optional[BaseFinancialAgent]:
        """Get agent with least current load"""
        if not pool.agents:
            return None
        
        # Find agent with least current tasks
        least_loaded_agent = min(pool.agents, key=lambda a: a.state.current_tasks)
        return least_loaded_agent
    
    async def _get_agent_random(self, pool: AgentPool) -> Optional[BaseFinancialAgent]:
        """Get agent randomly"""
        if not pool.agents:
            return None
        
        import random
        return random.choice(pool.agents)
    
    async def _add_to_pool(self, agent_type: str, agent: BaseFinancialAgent) -> None:
        """Add agent to pool"""
        pool = self.agent_pools.get(agent_type)
        if pool and len(pool.agents) < pool.max_size:
            pool.agents.append(agent)
    
    async def destroy_agent(self, agent_id: str) -> bool:
        """
        Destroy an agent instance
        
        Args:
            agent_id: ID of agent to destroy
            
        Returns:
            bool: True if agent was destroyed successfully
        """
        try:
            agent = self.active_agents.get(agent_id)
            if not agent:
                self.logger.warning("Agent not found for destruction", agent_id=agent_id)
                return False
            
            # Stop the agent
            await agent.stop()
            
            # Remove from active agents
            del self.active_agents[agent_id]
            
            # Remove from pool
            await self._remove_from_pool(agent)
            
            # Remove health data
            if agent_id in self.agent_health:
                del self.agent_health[agent_id]
            
            self.destruction_count += 1
            
            self.logger.info("Agent destroyed", agent_id=agent_id)
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to destroy agent",
                agent_id=agent_id,
                error=str(e)
            )
            return False
    
    async def _remove_from_pool(self, agent: BaseFinancialAgent) -> None:
        """Remove agent from pool"""
        for pool in self.agent_pools.values():
            if agent in pool.agents:
                pool.agents.remove(agent)
                break
    
    async def get_agent_health(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get health status of an agent
        
        Args:
            agent_id: ID of agent to check
            
        Returns:
            Dict[str, Any]: Health status
        """
        agent = self.active_agents.get(agent_id)
        if not agent:
            return None
        
        try:
            health = await agent.get_health_status()
            self.agent_health[agent_id] = health
            return health
        except Exception as e:
            self.logger.error(
                "Failed to get agent health",
                agent_id=agent_id,
                error=str(e)
            )
            return None
    
    async def get_all_agent_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status of all agents
        
        Returns:
            Dict[str, Dict[str, Any]]: Health status of all agents
        """
        health_data = {}
        
        for agent_id in self.active_agents.keys():
            health = await self.get_agent_health(agent_id)
            if health:
                health_data[agent_id] = health
        
        return health_data
    
    async def update_agent_config(self, agent_id: str, new_config: AgentConfig) -> bool:
        """
        Update configuration of an agent
        
        Args:
            agent_id: ID of agent to update
            new_config: New configuration
            
        Returns:
            bool: True if update was successful
        """
        try:
            agent = self.active_agents.get(agent_id)
            if not agent:
                return False
            
            await agent.update_config(new_config)
            
            self.logger.info(
                "Agent config updated",
                agent_id=agent_id,
                new_config=new_config.dict()
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to update agent config",
                agent_id=agent_id,
                error=str(e)
            )
            return False
    
    async def get_factory_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the agent factory
        
        Returns:
            Dict[str, Any]: Factory metrics
        """
        total_agents = len(self.active_agents)
        total_pools = len(self.agent_pools)
        
        pool_metrics = {}
        for agent_type, pool in self.agent_pools.items():
            pool_metrics[agent_type] = {
                "pool_size": len(pool.agents),
                "max_size": pool.max_size,
                "utilization": len(pool.agents) / pool.max_size if pool.max_size > 0 else 0
            }
        
        return {
            "total_agents": total_agents,
            "total_pools": total_pools,
            "creation_count": self.creation_count,
            "destruction_count": self.destruction_count,
            "pool_metrics": pool_metrics,
            "agent_types": list(self.agent_templates.keys()),
            "active_agent_types": list(set(agent.config.agent_type for agent in self.active_agents.values()))
        }
    
    async def cleanup_unhealthy_agents(self) -> int:
        """
        Clean up unhealthy agents
        
        Returns:
            int: Number of agents cleaned up
        """
        cleaned_count = 0
        
        for agent_id, agent in list(self.active_agents.items()):
            try:
                health = await agent.get_health_status()
                
                # Check if agent is unhealthy
                if health.get("status") == "error" or health.get("error_count", 0) > 5:
                    self.logger.warning(
                        "Cleaning up unhealthy agent",
                        agent_id=agent_id,
                        health=health
                    )
                    
                    if await self.destroy_agent(agent_id):
                        cleaned_count += 1
                        
            except Exception as e:
                self.logger.error(
                    "Failed to check agent health during cleanup",
                    agent_id=agent_id,
                    error=str(e)
                )
                
                # Destroy agent if we can't check its health
                if await self.destroy_agent(agent_id):
                    cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(
                "Agent cleanup completed",
                cleaned_count=cleaned_count
            )
        
        return cleaned_count
    
    async def shutdown(self) -> None:
        """Shutdown the agent factory"""
        self.logger.info("Shutting down agent factory")
        
        # Stop all agents
        for agent_id in list(self.active_agents.keys()):
            await self.destroy_agent(agent_id)
        
        self.logger.info("Agent factory shutdown completed")


# Global agent factory instance
_agent_factory: Optional[AgentFactory] = None


def get_agent_factory(config: Optional[AgentFactoryConfig] = None) -> AgentFactory:
    """
    Get the global agent factory instance
    
    Args:
        config: Factory configuration (only used for first initialization)
        
    Returns:
        AgentFactory: Global agent factory instance
    """
    global _agent_factory
    
    if _agent_factory is None:
        if config is None:
            config = AgentFactoryConfig()
        _agent_factory = AgentFactory(config)
    
    return _agent_factory


def set_agent_factory(factory: AgentFactory) -> None:
    """
    Set the global agent factory instance
    
    Args:
        factory: Agent factory instance
    """
    global _agent_factory
    _agent_factory = factory
