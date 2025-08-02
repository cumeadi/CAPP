"""
Compliance Service for CAPP

Handles regulatory compliance requirements across African countries including
KYC/AML, sanctions screening, and country-specific regulations.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
import structlog

from .models.payments import PaymentRoute, Country
from .config.settings import get_settings

logger = structlog.get_logger(__name__)


class ComplianceResult(BaseModel):
    """Result of compliance check"""
    is_compliant: bool
    risk_score: float
    risk_level: str  # low, medium, high
    violations: List[str]
    required_actions: List[str]
    country_specific_requirements: Dict[str, List[str]]


class ComplianceService:
    """
    Compliance Service
    
    Handles regulatory compliance for cross-border payments including:
    - KYC/AML requirements
    - Sanctions screening
    - Country-specific regulations
    - Risk assessment
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        
        # Load country-specific regulations
        self.country_regulations = self._load_country_regulations()
    
    def _load_country_regulations(self) -> Dict[str, Dict]:
        """Load country-specific regulatory requirements"""
        return {
            "KE": {  # Kenya
                "kyc_required": True,
                "aml_threshold": 1000000,  # KES
                "max_daily_limit": 70000,  # KES
                "required_documents": ["national_id", "phone_number"],
                "restricted_countries": ["SO", "SD"],
                "special_requirements": ["mpesa_registration"]
            },
            "NG": {  # Nigeria
                "kyc_required": True,
                "aml_threshold": 5000000,  # NGN
                "max_daily_limit": 500000,  # NGN
                "required_documents": ["national_id", "bvn"],
                "restricted_countries": [],
                "special_requirements": ["bvn_verification"]
            },
            "UG": {  # Uganda
                "kyc_required": True,
                "aml_threshold": 2000000,  # UGX
                "max_daily_limit": 1000000,  # UGX
                "required_documents": ["national_id", "phone_number"],
                "restricted_countries": [],
                "special_requirements": ["mobile_money_registration"]
            },
            "GH": {  # Ghana
                "kyc_required": True,
                "aml_threshold": 50000,  # GHS
                "max_daily_limit": 10000,  # GHS
                "required_documents": ["national_id", "phone_number"],
                "restricted_countries": [],
                "special_requirements": ["ghana_card_verification"]
            },
            "ZA": {  # South Africa
                "kyc_required": True,
                "aml_threshold": 25000,  # ZAR
                "max_daily_limit": 5000,  # ZAR
                "required_documents": ["national_id", "proof_of_address"],
                "restricted_countries": [],
                "special_requirements": ["fica_compliance"]
            }
        }
    
    async def check_route_compliance(self, route: PaymentRoute, from_country: Country, to_country: Country) -> ComplianceResult:
        """
        Check compliance for a payment route
        
        Args:
            route: The payment route to check
            from_country: Source country
            to_country: Destination country
            
        Returns:
            ComplianceResult: Compliance check result
        """
        try:
            violations = []
            required_actions = []
            risk_score = 0.0
            
            # Check country-specific requirements
            from_regulations = self.country_regulations.get(from_country, {})
            to_regulations = self.country_regulations.get(to_country, {})
            
            # Check for restricted countries
            if to_country in from_regulations.get("restricted_countries", []):
                violations.append(f"Payments to {to_country} are restricted from {from_country}")
                risk_score += 0.8
            
            if from_country in to_regulations.get("restricted_countries", []):
                violations.append(f"Payments from {from_country} are restricted to {to_country}")
                risk_score += 0.8
            
            # Check corridor-specific requirements
            corridor_requirements = self._get_corridor_requirements(from_country, to_country)
            required_actions.extend(corridor_requirements)
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Check if compliant
            is_compliant = len(violations) == 0
            
            return ComplianceResult(
                is_compliant=is_compliant,
                risk_score=risk_score,
                risk_level=risk_level,
                violations=violations,
                required_actions=required_actions,
                country_specific_requirements={
                    from_country: from_regulations.get("special_requirements", []),
                    to_country: to_regulations.get("special_requirements", [])
                }
            )
            
        except Exception as e:
            self.logger.error("Compliance check failed", error=str(e))
            return ComplianceResult(
                is_compliant=False,
                risk_score=1.0,
                risk_level="high",
                violations=["Compliance check failed"],
                required_actions=["Manual review required"],
                country_specific_requirements={}
            )
    
    def _get_corridor_requirements(self, from_country: Country, to_country: Country) -> List[str]:
        """Get corridor-specific compliance requirements"""
        requirements = []
        
        # East Africa corridor requirements
        if from_country in ["KE", "UG", "TZ", "RW"] and to_country in ["KE", "UG", "TZ", "RW"]:
            requirements.append("east_africa_community_verification")
        
        # West Africa corridor requirements
        if from_country in ["NG", "GH", "SN", "CI"] and to_country in ["NG", "GH", "SN", "CI"]:
            requirements.append("ecowas_verification")
        
        # Southern Africa corridor requirements
        if from_country in ["ZA", "BW", "ZM", "MW"] and to_country in ["ZA", "BW", "ZM", "MW"]:
            requirements.append("sadc_verification")
        
        return requirements
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score"""
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.7:
            return "medium"
        else:
            return "high"
    
    async def check_kyc_compliance(self, sender_country: Country, recipient_country: Country, amount: float) -> ComplianceResult:
        """
        Check KYC compliance requirements
        
        Args:
            sender_country: Sender's country
            recipient_country: Recipient's country
            amount: Payment amount
            
        Returns:
            ComplianceResult: KYC compliance result
        """
        try:
            violations = []
            required_actions = []
            risk_score = 0.0
            
            # Check sender country KYC requirements
            sender_regulations = self.country_regulations.get(sender_country, {})
            if sender_regulations.get("kyc_required", False):
                required_actions.extend(sender_regulations.get("required_documents", []))
                
                # Check AML threshold
                aml_threshold = sender_regulations.get("aml_threshold", 0)
                if amount > aml_threshold:
                    violations.append(f"Amount exceeds AML threshold for {sender_country}")
                    risk_score += 0.5
                
                # Check daily limit
                daily_limit = sender_regulations.get("max_daily_limit", float('inf'))
                if amount > daily_limit:
                    violations.append(f"Amount exceeds daily limit for {sender_country}")
                    risk_score += 0.3
            
            # Check recipient country KYC requirements
            recipient_regulations = self.country_regulations.get(recipient_country, {})
            if recipient_regulations.get("kyc_required", False):
                required_actions.extend(recipient_regulations.get("required_documents", []))
                
                # Check AML threshold
                aml_threshold = recipient_regulations.get("aml_threshold", 0)
                if amount > aml_threshold:
                    violations.append(f"Amount exceeds AML threshold for {recipient_country}")
                    risk_score += 0.5
                
                # Check daily limit
                daily_limit = recipient_regulations.get("max_daily_limit", float('inf'))
                if amount > daily_limit:
                    violations.append(f"Amount exceeds daily limit for {recipient_country}")
                    risk_score += 0.3
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Check if compliant
            is_compliant = len(violations) == 0
            
            return ComplianceResult(
                is_compliant=is_compliant,
                risk_score=risk_score,
                risk_level=risk_level,
                violations=violations,
                required_actions=list(set(required_actions)),  # Remove duplicates
                country_specific_requirements={
                    sender_country: sender_regulations.get("special_requirements", []),
                    recipient_country: recipient_regulations.get("special_requirements", [])
                }
            )
            
        except Exception as e:
            self.logger.error("KYC compliance check failed", error=str(e))
            return ComplianceResult(
                is_compliant=False,
                risk_score=1.0,
                risk_level="high",
                violations=["KYC compliance check failed"],
                required_actions=["Manual review required"],
                country_specific_requirements={}
            )
    
    async def check_sanctions(self, sender_country: Country, recipient_country: Country) -> ComplianceResult:
        """
        Check sanctions screening
        
        Args:
            sender_country: Sender's country
            recipient_country: Recipient's country
            
        Returns:
            ComplianceResult: Sanctions check result
        """
        try:
            violations = []
            required_actions = []
            risk_score = 0.0
            
            # Check against sanctions lists
            sanctioned_countries = ["SO", "SD", "LY", "ER"]  # Example sanctioned countries
            
            if sender_country in sanctioned_countries:
                violations.append(f"Sender country {sender_country} is under sanctions")
                risk_score += 0.9
            
            if recipient_country in sanctioned_countries:
                violations.append(f"Recipient country {recipient_country} is under sanctions")
                risk_score += 0.9
            
            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            
            # Check if compliant
            is_compliant = len(violations) == 0
            
            return ComplianceResult(
                is_compliant=is_compliant,
                risk_score=risk_score,
                risk_level=risk_level,
                violations=violations,
                required_actions=required_actions,
                country_specific_requirements={}
            )
            
        except Exception as e:
            self.logger.error("Sanctions check failed", error=str(e))
            return ComplianceResult(
                is_compliant=False,
                risk_score=1.0,
                risk_level="high",
                violations=["Sanctions check failed"],
                required_actions=["Manual review required"],
                country_specific_requirements={}
            )
    
    async def get_country_regulations(self, country: Country) -> Dict:
        """Get regulatory requirements for a specific country"""
        return self.country_regulations.get(country, {})
    
    async def get_supported_countries(self) -> List[Country]:
        """Get list of supported countries with regulations"""
        return list(self.country_regulations.keys()) 