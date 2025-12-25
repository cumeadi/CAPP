"""
Sanctions Screening Service

Checks entities and addresses against sanctions lists (e.g. OFAC SDN).
Uses fuzzy matching to detect name variations.
"""

from typing import List, Dict, Tuple, Optional
from decimal import Decimal
import structlog
from thefuzz import process, fuzz

logger = structlog.get_logger(__name__)

# Simulated Mini-SDN List (Specially Designated Nationals)
# in a real app, this would be loaded from XML/CSV daily
SDN_LIST_NAMES = [
    "OSAMA BIN LADEN",
    "SADDAM HUSSEIN",
    "KIM JONG UN",
    "VLADIMIR PUTIN",
    "NICOLAS MADURO",
    "BASHAR AL-ASSAD",
    "AL-QAEDA",
    "ISIS",
    "HEZBOLLAH",
    "HAMAS",
    "LAZARUS GROUP"
]

# Blocked Crypto Addresses (Example: Tornado Cash, Lazarus Group hacks)
BLOCKED_ADDRESSES = {
    "0x7FFC57839B00206D1ad20c69A1981b489f772031": "Tornado Cash Router",
    "0x8589427373D6D84E98730D7795D8f6f8731FDA16": "Ronin Bridge Hacker (Lazarus)",
    "0x1234567890abcdef1234567890abcdef12345678": "Simulated Sanctioned Entity"
}

HIGH_RISK_COUNTRIES = ["KP", "IR", "CU", "SY", "RU", "BY"]

class SanctionsService:
    """Service for checking sanctions compliance"""
    
    def __init__(self):
        self.logger = logger
        self.similarity_threshold = 85  # Match score required to trigger hit
        
    async def screening_check(self, 
                            name: str, 
                            wallet_address: Optional[str] = None, 
                            country: Optional[str] = None) -> Dict[str, any]:
        """
        Screen a user against sanctions lists.
        
        Returns:
            Dict with 'is_sanctioned' (bool) and 'reason' (str)
        """
        # 1. Country Check
        if country and country.upper() in HIGH_RISK_COUNTRIES:
             return {
                "is_sanctioned": True,
                "reason": f"Country '{country}' is properly embargoed/high-risk.",
                "match_score": 100,
                "matched_entry": country
            }

        # 2. Wallet Address Check
        if wallet_address and wallet_address in BLOCKED_ADDRESSES:
             return {
                "is_sanctioned": True,
                "reason": f"Wallet address is linked to {BLOCKED_ADDRESSES[wallet_address]}.",
                "match_score": 100,
                "matched_entry": wallet_address
            }
            
        # 3. Name Fuzzy Matching
        clean_name = name.upper().strip()
        
        # Determine best match
        # process.extractOne returns (match, score)
        best_match = process.extractOne(clean_name, SDN_LIST_NAMES, scorer=fuzz.token_sort_ratio)
        
        if best_match:
            matched_name, score = best_match
            if score >= self.similarity_threshold:
                self.logger.warning("Sanctions Hit Detected", 
                                  input_name=name, 
                                  matched_name=matched_name, 
                                  score=score)
                return {
                    "is_sanctioned": True,
                    "reason": f"Name matched blocked entity '{matched_name}' with {score}% confidence.",
                    "match_score": score,
                    "matched_entry": matched_name
                }
        
        return {
            "is_sanctioned": False,
            "reason": "Clear",
            "match_score": 0,
            "matched_entry": None
        }
