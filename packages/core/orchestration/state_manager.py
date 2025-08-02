"""
State Manager

Manages the state of payment processing flows and agents.
"""

from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class StateManager:
    """Manages state for payment processing."""
    
    def __init__(self):
        self.states = {}
        
    async def set_state(self, key: str, value: Any) -> bool:
        """Set a state value."""
        self.states[key] = value
        return True
        
    async def get_state(self, key: str) -> Optional[Any]:
        """Get a state value."""
        return self.states.get(key) 