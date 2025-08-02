"""
Agent registry for managing agent types and registration

This module provides a registry for managing different types of financial agents
and their registration in the orchestration system.
"""

import asyncio
from typing import Dict, List, Optional, Any, Type, Set
from datetime import datetime, timezone

import structlog
from pydantic import BaseModel, Field

from packages.core.agents.base import BaseFinancialAgent, AgentConfig

logger = structlog.get_logger(__name__)


class AgentRegistration(BaseModel):
    """Registration information for an agent type"""
    agent_type: str
    agent_class: Type[BaseFinancialAgent]
    description: str
    version: str = "1.0.0"
    capabilities: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentRegistry:
    """
    Registry for managing financial agent types
    
    This class provides a centralized registry for managing different types
    of financial agents with features like:
    - Agent type registration and discovery
    - Capability-based agent selection
    - Configuration validation
    - Dependency management
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        
        # Agent registrations
        self.registrations: Dict[str, AgentRegistration] = {}
        
        # Capability index
        self.capability_index: Dict[str, Set[str]] = {}
        
        # Instance tracking
        self.active_instances: Dict[str, BaseFinancialAgent] = {}
        
        self.logger.info("Agent registry initialized")
    
    def register_agent_type(self, agent_type: str, agent_class: Type[BaseFinancialAgent],
                           description: str = "", version: str = "1.0.0",
                           capabilities: Optional[List[str]] = None,
                           dependencies: Optional[List[str]] = None,
                           config_schema: Optional[Dict[str, Any]] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a new agent type
        
        Args:
            agent_type: Unique identifier for the agent type
            agent_class: Agent class to register
            description: Description of the agent type
            version: Version of the agent type
            capabilities: List of capabilities this agent provides
            dependencies: List of dependencies this agent requires
            config_schema: Configuration schema for this agent type
            metadata: Additional metadata
        """
        if agent_type in self.registrations:
            self.logger.warning(
                "Agent type already registered, updating",
                agent_type=agent_type
            )
        
        registration = AgentRegistration(
            agent_type=agent_type,
            agent_class=agent_class,
            description=description,
            version=version,
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            config_schema=config_schema or {},
            metadata=metadata or {}
        )
        
        self.registrations[agent_type] = registration
        
        # Update capability index
        for capability in registration.capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(agent_type)
        
        self.logger.info(
            "Agent type registered",
            agent_type=agent_type,
            capabilities=capabilities,
            dependencies=dependencies
        )
    
    def unregister_agent_type(self, agent_type: str) -> bool:
        """
        Unregister an agent type
        
        Args:
            agent_type: Agent type to unregister
            
        Returns:
            bool: True if agent type was unregistered
        """
        if agent_type not in self.registrations:
            return False
        
        registration = self.registrations[agent_type]
        
        # Remove from capability index
        for capability in registration.capabilities:
            if capability in self.capability_index:
                self.capability_index[capability].discard(agent_type)
                if not self.capability_index[capability]:
                    del self.capability_index[capability]
        
        # Remove registration
        del self.registrations[agent_type]
        
        self.logger.info("Agent type unregistered", agent_type=agent_type)
        return True
    
    def get_agent_type(self, agent_type: str) -> Optional[AgentRegistration]:
        """
        Get registration for an agent type
        
        Args:
            agent_type: Agent type to retrieve
            
        Returns:
            AgentRegistration: Registration if found
        """
        return self.registrations.get(agent_type)
    
    def list_agent_types(self) -> List[str]:
        """
        List all registered agent types
        
        Returns:
            List[str]: List of agent type names
        """
        return list(self.registrations.keys())
    
    def get_agent_types_by_capability(self, capability: str) -> List[str]:
        """
        Get agent types that provide a specific capability
        
        Args:
            capability: Capability to search for
            
        Returns:
            List[str]: List of agent types with the capability
        """
        return list(self.capability_index.get(capability, set()))
    
    def get_agent_types_by_capabilities(self, capabilities: List[str]) -> List[str]:
        """
        Get agent types that provide all specified capabilities
        
        Args:
            capabilities: List of capabilities to search for
            
        Returns:
            List[str]: List of agent types with all capabilities
        """
        if not capabilities:
            return []
        
        # Start with agents that have the first capability
        matching_agents = set(self.capability_index.get(capabilities[0], set()))
        
        # Intersect with agents that have other capabilities
        for capability in capabilities[1:]:
            capability_agents = set(self.capability_index.get(capability, set()))
            matching_agents &= capability_agents
        
        return list(matching_agents)
    
    def create_agent(self, agent_type: str, config: AgentConfig) -> BaseFinancialAgent:
        """
        Create an agent instance
        
        Args:
            agent_type: Type of agent to create
            config: Agent configuration
            
        Returns:
            BaseFinancialAgent: Created agent instance
            
        Raises:
            ValueError: If agent type is not registered
        """
        registration = self.get_agent_type(agent_type)
        if not registration:
            raise ValueError(f"Agent type '{agent_type}' is not registered")
        
        # Validate dependencies
        await self._validate_dependencies(registration)
        
        # Create agent instance
        agent = registration.agent_class(config)
        
        # Track instance
        self.active_instances[agent.agent_id] = agent
        
        self.logger.info(
            "Agent instance created",
            agent_type=agent_type,
            agent_id=agent.agent_id
        )
        
        return agent
    
    async def _validate_dependencies(self, registration: AgentRegistration) -> None:
        """
        Validate that all dependencies are available
        
        Args:
            registration: Agent registration to validate
            
        Raises:
            ValueError: If dependencies are not satisfied
        """
        missing_dependencies = []
        
        for dependency in registration.dependencies:
            if dependency not in self.registrations:
                missing_dependencies.append(dependency)
        
        if missing_dependencies:
            raise ValueError(
                f"Missing dependencies for agent type '{registration.agent_type}': "
                f"{missing_dependencies}"
            )
    
    def get_agent(self, agent_id: str) -> Optional[BaseFinancialAgent]:
        """
        Get an agent instance by ID
        
        Args:
            agent_id: ID of the agent instance
            
        Returns:
            BaseFinancialAgent: Agent instance if found
        """
        return self.active_instances.get(agent_id)
    
    def get_agents_by_type(self, agent_type: str) -> List[BaseFinancialAgent]:
        """
        Get all agent instances of a specific type
        
        Args:
            agent_type: Type of agents to retrieve
            
        Returns:
            List[BaseFinancialAgent]: List of agent instances
        """
        return [
            agent for agent in self.active_instances.values()
            if agent.config.agent_type == agent_type
        ]
    
    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent instance from tracking
        
        Args:
            agent_id: ID of the agent instance to remove
            
        Returns:
            bool: True if agent was removed
        """
        if agent_id in self.active_instances:
            del self.active_instances[agent_id]
            self.logger.info("Agent instance removed from tracking", agent_id=agent_id)
            return True
        return False
    
    async def stop_all_agents(self) -> None:
        """Stop all active agent instances"""
        self.logger.info("Stopping all agent instances")
        
        for agent_id, agent in list(self.active_instances.items()):
            try:
                await agent.stop()
                self.remove_agent(agent_id)
            except Exception as e:
                self.logger.error(
                    "Failed to stop agent",
                    agent_id=agent_id,
                    error=str(e)
                )
    
    async def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status of all agent instances
        
        Returns:
            Dict[str, Dict[str, Any]]: Health status of all agents
        """
        health_data = {}
        
        for agent_id, agent in self.active_instances.items():
            try:
                health = await agent.get_health_status()
                health_data[agent_id] = health
            except Exception as e:
                self.logger.error(
                    "Failed to get agent health",
                    agent_id=agent_id,
                    error=str(e)
                )
                health_data[agent_id] = {"status": "error", "error": str(e)}
        
        return health_data
    
    def get_registry_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the agent registry
        
        Returns:
            Dict[str, Any]: Registry metrics
        """
        total_registrations = len(self.registrations)
        total_instances = len(self.active_instances)
        
        # Count instances by type
        instances_by_type = {}
        for agent in self.active_instances.values():
            agent_type = agent.config.agent_type
            instances_by_type[agent_type] = instances_by_type.get(agent_type, 0) + 1
        
        # Count capabilities
        total_capabilities = len(self.capability_index)
        
        return {
            "total_registrations": total_registrations,
            "total_instances": total_instances,
            "total_capabilities": total_capabilities,
            "instances_by_type": instances_by_type,
            "registered_types": list(self.registrations.keys()),
            "available_capabilities": list(self.capability_index.keys())
        }
    
    def validate_config(self, agent_type: str, config: Dict[str, Any]) -> bool:
        """
        Validate configuration for an agent type
        
        Args:
            agent_type: Agent type to validate config for
            config: Configuration to validate
            
        Returns:
            bool: True if configuration is valid
        """
        registration = self.get_agent_type(agent_type)
        if not registration:
            return False
        
        # Basic validation - in a real implementation, you might use JSON Schema
        # or Pydantic for more sophisticated validation
        schema = registration.config_schema
        if not schema:
            return True  # No schema means any config is valid
        
        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in config:
                self.logger.warning(
                    "Missing required field in config",
                    agent_type=agent_type,
                    field=field
                )
                return False
        
        return True
    
    def get_agent_info(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about an agent type
        
        Args:
            agent_type: Agent type to get info for
            
        Returns:
            Dict[str, Any]: Agent information
        """
        registration = self.get_agent_type(agent_type)
        if not registration:
            return None
        
        instances = self.get_agents_by_type(agent_type)
        
        return {
            "agent_type": registration.agent_type,
            "description": registration.description,
            "version": registration.version,
            "capabilities": registration.capabilities,
            "dependencies": registration.dependencies,
            "config_schema": registration.config_schema,
            "registered_at": registration.registered_at.isoformat(),
            "metadata": registration.metadata,
            "active_instances": len(instances),
            "instance_ids": [agent.agent_id for agent in instances]
        }


# Global agent registry instance
_agent_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """
    Get the global agent registry instance
    
    Returns:
        AgentRegistry: Global agent registry instance
    """
    global _agent_registry
    
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    
    return _agent_registry


def set_agent_registry(registry: AgentRegistry) -> None:
    """
    Set the global agent registry instance
    
    Args:
        registry: Agent registry instance
    """
    global _agent_registry
    _agent_registry = registry
