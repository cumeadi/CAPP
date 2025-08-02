"""
Base Agent

Base class for all payment processing agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for payment agents."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.is_active = True
        
    @abstractmethod
    async def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a payment request."""
        pass
        
    async def start(self):
        """Start the agent."""
        self.is_active = True
        logger.info(f"Agent {self.agent_id} started")
        
    async def stop(self):
        """Stop the agent."""
        self.is_active = False
        logger.info(f"Agent {self.agent_id} stopped") 