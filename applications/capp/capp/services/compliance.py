"""
Compliance Service for CAPP

Handles regulatory compliance requirements across African countries including
KYC/AML, sanctions screening, and country-specific regulations.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
import structlog

from applications.capp.capp.models.payments import PaymentRoute, Country, CrossBorderPayment
from applications.capp.capp.config.settings import get_settings
from packages.intelligence.compliance.agent import AIComplianceAgent
import datetime
import csv
import io

logger = structlog.get_logger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from applications.capp.capp.repositories.payment import PaymentRepository



class ComplianceResult(BaseModel):
    """Result of compliance check"""
    is_compliant: bool
    risk_score: float
    risk_level: str  # low, medium, high
    violations: List[str]
    required_actions: List[str]
    country_specific_requirements: Dict[str, List[str]]
    reasoning: Optional[str] = None # Added for AI reasoning


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
        
        # Initialize AI Agent
        self.ai_agent = AIComplianceAgent()
    
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
            
    async def check_travel_rule(self, payment: CrossBorderPayment) -> bool:
        """
        Check Travel Rule Compliance (FATF Recommendation 16).
        Ensures originator and beneficiary information is complete for transactions > threshold.
        """
        # Global Threshold ~ $1000 USD
        TRAVEL_RULE_THRESHOLD_USD = 1000.00
        
        # Convert amount to USD (Mock conversion)
        amount_usd = float(payment.amount) # Assuming base is USD-pegged for simplicity or already converted
        
        if amount_usd < TRAVEL_RULE_THRESHOLD_USD:
            return True
            
        # Check Required Fields
        sender_ok = all ([
            payment.sender.name,
            payment.sender.address or payment.sender.id_number or payment.sender.date_of_birth
        ])
        
        recipient_ok = all([
            payment.recipient.name,
            payment.recipient.bank_account or payment.recipient.mmo_account
        ])
        
        if not (sender_ok and recipient_ok):
            self.logger.warning("Travel Rule Violation", payment_id=str(payment.payment_id))
            return False
            
        return True
    
    async def check_route_compliance(self, route: PaymentRoute, from_country: Country, to_country: Country, payment: Optional[CrossBorderPayment] = None) -> ComplianceResult:
        """
        Check compliance for a payment route
        
        Args:
            route: The payment route to check
            from_country: Source country
            to_country: Destination country
            payment: The full payment object (required for AI checks)
            
        Returns:
            ComplianceResult: Compliance check result
        """
        try:
            # If payment context is available, use AI Agent for deep analysis
            if payment:
                 self.logger.info("Delegating compliance check to AI Agent", payment_id=str(payment.payment_id))
                 ai_result = await self.ai_agent.evaluate_transaction(payment)
                 
                 return ComplianceResult(
                     is_compliant=ai_result.get("is_compliant", False),
                     risk_score=ai_result.get("risk_score", 1.0),
                     risk_level=self._determine_risk_level(ai_result.get("risk_score", 1.0)),
                     violations=ai_result.get("violations", []),
                     required_actions=ai_result.get("required_actions", []),
                     country_specific_requirements={}, # Could populate if needed
                     reasoning=ai_result.get("reasoning", "AI Analysis completed.")
                 )

            # Fallback to legacy rule-based check if no payment object
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
            
            # Compliance Shield Logic
            # If Risk is Medium or High but not explicitly Rejected, flag for review
            should_review = False
            if risk_level in ["medium", "high"] and is_compliant: # Compliant but risky
                should_review = True
                
            if should_review:
                return ComplianceResult(
                    is_compliant=False, # Pause for review
                    risk_score=risk_score,
                    risk_level=risk_level,
                    violations=["Transaction flagged for institutional review"],
                    required_actions=["Manual Approval Required"],
                    country_specific_requirements={
                        from_country: from_regulations.get("special_requirements", []),
                        to_country: to_regulations.get("special_requirements", [])
                    }
                )

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
    async def get_supported_countries(self) -> List[Country]:
        """Get list of supported countries with regulations"""
        return list(self.country_regulations.keys())

    async def generate_report(self, user_id: UUID, report_type: str, year: int, session: AsyncSession) -> Dict[str, str]:

        """
        Generate a compliance report (CSV or PDF/Text) for a user for a specific year.
        """
        repo = PaymentRepository(session)
        # Fetch all payments for now, perform in-memory filtering for year for MVP convenience
        # In prod, repo should support date range filtering
        payments = await repo.get_by_user(user_id, limit=1000)
        
        filtered_payments = [
            p for p in payments 
            if p.created_at.year == year
        ]
        
        if report_type.upper() == "CSV":
            filename = f"capp_compliance_{year}.csv"
            output = io.StringIO()
            fieldnames = ["Date", "Payment ID", "Type", "Amount", "Currency", "Status", "Reference", "Description"]
            writer = csv.DictWriter(output, fieldnames=fieldnames)

            writer.writeheader()
            for p in filtered_payments:
                writer.writerow({
                    "Date": p.created_at.isoformat(),
                    "Payment ID": str(p.id), # Assuming ID matches model field roughly
                    "Type": p.payment_type,
                    "Amount": str(p.amount),
                    "Currency": p.from_currency, # Use from_currency as main currency
                    "Status": p.status,
                    "Reference": p.reference_id,
                    "Description": p.description or ""
                })
            content = output.getvalue()
            output.close()

        else:
            # Mock PDF as Text
            filename = f"capp_compliance_{year}.txt"
            content = f"CAPP WALLET - COMPLIANCE REPORT {year}\n"
            content += f"User ID: {user_id}\n"
            content += f"Generated: {datetime.datetime.now()}\n"
            content += "="*50 + "\n\n"
            for p in filtered_payments:
                content += f"Transaction: {p.reference_id}\n"
                content += f"Date: {p.created_at}\n"
                content += f"Type: {p.payment_type}\n"
                content += f"Amount: {p.amount} {p.from_currency}\n"
                content += f"Status: {p.status}\n"
                content += "-"*30 + "\n"
                
        return {"filename": filename, "content": content} 