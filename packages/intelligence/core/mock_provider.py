"""
Mock LLM Provider for Development and Testing
"""
import json
import asyncio
import re
from typing import Dict, Any, Optional, List
import structlog

from .llm_provider import LLMProvider, LLMResponse

logger = structlog.get_logger(__name__)

class MockLLMProvider(LLMProvider):
    """
    Simulates LLM responses using heuristics and regex matching.
    Useful for testing without incurring API costs.
    """
    
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text completion based on keywords in prompt"""
        logger.info("Mock LLM generating text", prompt_snippet=prompt[:50])
        await asyncio.sleep(0.5) # Simulate latency
        
        # Simple heuristic response generation
        if "reasoning" in prompt.lower():
            return LLMResponse(
                content="Based on the analysis of the transaction details and sanctions lists, the risk appears properly mitigated. The name match is partial and likely a false positive due to phonetic similarity.",
                raw_response={"mock": True}
            )
        
        return LLMResponse(
            content="Mock AI analysis completed. No critical issues found.",
            raw_response={"mock": True}
        )
    
    async def generate_json(self, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate structured JSON response based on keywords"""
        logger.info("Mock LLM generating JSON", prompt_snippet=prompt[:50])
        await asyncio.sleep(0.5)
        
        prompt_lower = prompt.lower()
        
        # Simulate Sanctions Screening Logic
        is_sanctioned = False
        risk_score = 0.1
        reasoning = "Passes standard checks."
        
        # Heuristic: Detect suspicious names or countries in the prompt
        # In a real app, the prompt would contain the data. We'll verify if the prompt *contains* specific test strings.
        
        # Check for Liquidity Management Prompt
        if "treasury status" in prompt_lower:
            # Heuristic: If risk is HIGH (which comes from the injected prompt text), then SWAP.
            # We look for "risk level: high" in the prompt content.
            if "risk level: high" in prompt_lower:
                return {
                    "action": "SWAP",
                    "amount": 400.0, # Swap diff (500 - 100)
                    "target_asset": "USDC",
                    "reasoning": "High risk detected and balance exceeds reserve. Rebalancing to stablecoin."
                }
            else:
                return {
                    "action": "HOLD",
                    "amount": 0.0,
                    "target_asset": None,
                    "reasoning": "Risk level is acceptable or balance is low."
                }

        # Check for Market Analysis Prompt
        if "volatility" in prompt_lower or "settlement batch" in prompt_lower:
            # Heuristic for Volatility
            risk_level = "LOW"
            recommendation = "PROCEED"
            reasoning = "Market conditions are stable. Low volatility detected."
            
            if "high" in prompt_lower and "volatility" in prompt_lower:
                risk_level = "HIGH"
                recommendation = "WAIT"
                reasoning = "High volatility detected. Recommended to wait for stabilization."
            elif "apt" in prompt_lower: # Mock APT as volatile for testing
                risk_level = "HIGH"
                recommendation = "PROCEED_WITH_CAUTION"
                reasoning = "Asset is experiencing moderate fluctuations."
                
            return {
                "risk_level": risk_level,
                "recommendation": recommendation,
                "reasoning": reasoning
            }

        # Check for Sanctioned Names (Phonetic/Fuzzy simulation)
        suspicious_names = ["osama", "ladin", "vladimir", "putin", "kim jong"]
        
        for name in suspicious_names:
            if name in prompt_lower:
                is_sanctioned = True
                risk_score = 0.95
                reasoning = f"Flagged due to high similarity with sanctioned entity name: '{name.capitalize()}'."
                break
                
        # Check for Sanctioned Countries
        suspicious_countries = ["north korea", "iran", "syria"]
        for country in suspicious_countries:
            if country in prompt_lower:
                is_sanctioned = True
                risk_score = 0.99
                reasoning = f"Transaction involves high-risk jurisdiction: {country.title()}."
                break
        
        return {
            "is_compliant": not is_sanctioned,
            "risk_score": risk_score,
            "reasoning": reasoning,
            "violations": ["Sanctions Match"] if is_sanctioned else [],
            "required_actions": ["Manual Review"] if is_sanctioned else []
        }
