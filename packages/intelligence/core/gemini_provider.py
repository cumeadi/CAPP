
import os
import json
import structlog
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .llm_provider import LLMProvider, LLMResponse
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

class GeminiProvider(LLMProvider):
    """
    Google Gemini LLM Provider
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-pro"):
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        logger.info("Gemini Provider Initialized", model=self.model_name)
        
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text completion using Gemini"""
        try:
            full_prompt = prompt
            if system_prompt:
                # Gemini Pro doesn't strictly separate system prompt in the same way as GPT-4, 
                # but valid to prepend context.
                full_prompt = f"System Instruction: {system_prompt}\n\nUser Query: {prompt}"
                
            response = await self.model.generate_content_async(full_prompt)
            
            return LLMResponse(
                content=response.text,
                raw_response=response.to_dict(),
                usage={} # Usage stats extraction varies by version
            )
        except Exception as e:
            logger.error("Gemini text generation failed", error=str(e))
            raise e

    async def generate_json(self, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate structured JSON response using Gemini"""
        try:
            # Enforce JSON structure via prompt engineering (Gemini supports JSON mode but prompt is key)
            structure_hint = f"You must respond with valid JSON matching this schema: {json.dumps(schema)}"
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System Instruction: {system_prompt}\n\n{structure_hint}\n\nUser Query: {prompt}"
            else:
                full_prompt = f"{structure_hint}\n\n{prompt}"

            # Ensure we ask for JSON explicitly
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
            
            response = await self.model.generate_content_async(
                full_prompt, 
                generation_config=generation_config
            )
            
            # clean potential markdown code blocks
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
            
        except Exception as e:
            logger.error("Gemini JSON generation failed", error=str(e))
            raise e
