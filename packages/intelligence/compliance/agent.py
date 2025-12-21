import json
import structlog
from typing import Dict, Any, List, Optional
from decimal import Decimal

from .prompts import TRANSACTION_SCREENING_PROMPT, COMPLIANCE_ANALYSIS_SYSTEM_PROMPT
from ..core.llm_provider import LLMProvider
from ..core.mock_provider import MockLLMProvider
from applications.capp.capp.models.payments import CrossBorderPayment, PaymentResult

logger = structlog.get_logger(__name__)

class AIComplianceAgent:
    """
    Intelligent Compliance Agent
    
    Uses LLMs to analyze transaction risk, screen against sanctions with fuzzy matching,
    and provide human-readable reasoning for compliance decisions.
    """
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or MockLLMProvider()
        self.logger = structlog.get_logger(__name__)
        
    async def evaluate_transaction(self, payment: CrossBorderPayment) -> Dict[str, Any]:
        """
        Evaluate a transaction for compliance risks using LLM reasoning.
        """
        self.logger.info("Starting AI compliance evaluation", payment_id=str(payment.payment_id))
        
        # 1. Retrieve Context (in a real app, this would query a Vector DB or Sanctions API)
        # For now, we simulate "Sanctions Hits" context based on naive string matching
        # to feed the prompt. The LLM then decides if it's a real threat.
        sanctions_context = self._get_simulated_sanctions_context(payment)
        
        # 2. Construct Prompt
        prompt = TRANSACTION_SCREENING_PROMPT.format(
            sender_name=payment.sender.name,
            sender_country=payment.sender.country,
            recipient_name=payment.recipient.name,
            recipient_country=payment.recipient.country,
            amount=f"{payment.amount}",
            currency=payment.from_currency,
            payment_method=payment.payment_method,
            description=payment.description or "N/A",
            sanctions_matches=sanctions_context,
            sender_limit="10000 USD", # Mock limits
            recipient_limit="50000 USD"
        )
        
        # 3. Call LLM
        try:
            response = await self.provider.generate_json(
                prompt=prompt,
                schema={}, # Schema is implicit in prompt for Mock
                system_prompt=COMPLIANCE_ANALYSIS_SYSTEM_PROMPT
            )
            
            self.logger.info("AI Compliance Decision", decision=response)
            return response
            
        except Exception as e:
            self.logger.error("LLM evaluation failed", error=str(e))
            # Fallback to REJECT on error for safety
            return {
                "is_compliant": False,
                "risk_score": 1.0,
                "reasoning": f"Automated analysis failed: {str(e)}",
                "violations": ["System Error"],
                "required_actions": ["Manual Review"]
            }

    def _get_simulated_sanctions_context(self, payment: CrossBorderPayment) -> str:
        """
        Simulates retrieving potential sanctions hits from a database.
        The LLM will use this to reason about whether it's a true positive.
        """
        hits = []
        name_queries = [payment.sender.name.lower(), payment.recipient.name.lower()]
        
        # Simulated database of bad actors
        watchlist = {
            "osama": "Osama Bin Laden (Terrorist)",
            "putin": "Vladimir Putin (PEP/Sanctioned)",
            "kim jong": "Kim Jong Un (Sanctioned Leader)"
        }
        
        for query in name_queries:
            for watch_term, details in watchlist.items():
                if watch_term in query:
                    hits.append(f"- Potential Match: '{query}' matches watchlist term '{watch_term}' ({details})")
                    
        if not hits:
            return "No close string matches found in sanctions database."
            
        return "\n".join(hits)
