"""
LLM Provider Interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class LLMResponse(BaseModel):
    """Standardized response from LLM"""
    content: str
    raw_response: Any
    usage: Dict[str, int] = {}

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text completion"""
        pass
    
    @abstractmethod
    async def generate_json(self, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate structured JSON response"""
        pass
