"""
Compliance Agent for CAPP

Handles regulatory compliance validation, sanctions screening,
and automated regulatory reporting for cross-border payments.
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field
import structlog

from applications.capp.capp.agents.base import BasePaymentAgent, AgentConfig
from applications.capp.capp.models.payments import (
    CrossBorderPayment, PaymentResult, PaymentStatus, PaymentRoute,
    Country, Currency
)
from applications.capp.capp.services.compliance import ComplianceService
from applications.capp.capp.services.sanctions import SanctionsService
from applications.capp.capp.services.fraud import FraudDetectionService
from applications.capp.capp.core.redis import get_cache
from applications.capp.capp.config.settings import get_settings

from packages.intelligence.compliance.agent import AIComplianceAgent
from packages.intelligence.core.gemini_provider import GeminiProvider

logger = structlog.get_logger(__name__)


# ... (Configs remain same) - Fixed: Restoring missing configs
class ComplianceConfig(AgentConfig):
    """Configuration for compliance agent"""
    agent_type: str = "compliance"
    
    # Compliance thresholds
    kyc_threshold_amount: float = 1000.0  # USD equivalent
    aml_threshold_amount: float = 3000.0  # USD equivalent
    enhanced_due_diligence_threshold: float = 10000.0  # USD equivalent
    
    # Screening settings
    sanctions_check_enabled: bool = True
    pep_check_enabled: bool = True
    adverse_media_check_enabled: bool = True
    
    # Risk scoring
    high_risk_score_threshold: float = 0.7
    medium_risk_score_threshold: float = 0.4
    
    # Reporting settings
    regulatory_reporting_enabled: bool = True
    report_generation_interval: int = 3600  # 1 hour
    retention_period_days: int = 2555  # 7 years
    
    # Performance settings
    max_concurrent_checks: int = 20
    check_timeout: int = 30  # seconds


class ComplianceCheck(BaseModel):
    """Individual compliance check result"""
    check_id: str
    check_type: str  # kyc, aml, sanctions, pep, adverse_media
    status: str  # passed, failed, pending, error
    risk_score: float
    details: Dict[str, Any]
    timestamp: datetime
    duration_ms: int


class ComplianceResult(BaseModel):
    """Overall compliance validation result"""
    success: bool
    payment_id: str
    overall_risk_score: float
    risk_level: str  # low, medium, high
    checks: List[ComplianceCheck]
    violations: List[str]
    required_actions: List[str]
    is_compliant: bool
    message: str


class SanctionsResult(BaseModel):
    """Sanctions screening result"""
    success: bool
    parties_checked: List[str]
    matches_found: List[str]
    risk_score: float
    is_compliant: bool
    violations: List[str]
    message: str


class RegulatoryReport(BaseModel):
    """Regulatory compliance report"""
    report_id: str
    report_type: str  # daily, weekly, monthly, ad_hoc
    period_start: datetime
    period_end: datetime
    total_transactions: int
    total_volume: Decimal
    compliance_rate: float
    violations_count: int
    risk_distribution: Dict[str, int]
    generated_at: datetime
    content: Dict[str, Any]

class ComplianceAgent(BasePaymentAgent):
    """
    Compliance Agent
    
    Handles regulatory compliance for cross-border payments:
    - Multi-jurisdiction compliance validation
    - Real-time sanctions screening (OFAC)
    - Risk scoring and assessment (Fraud Detection)
    - Automated regulatory reporting
    - KYC/AML compliance checks
    """
    
    def __init__(self, config: ComplianceConfig):
        super().__init__(config)
        self.config = config
        self.cache = get_cache()
        self.compliance_service = ComplianceService()
        self.sanctions_service = SanctionsService()
        self.sanctions_service = SanctionsService()
        self.fraud_service = FraudDetectionService()
        
        # Initialize AI Agent
        self.ai_agent = self._initialize_ai_agent()
        
        # Compliance tracking
        
        # Compliance tracking
        self.compliance_checks: Dict[str, List[ComplianceCheck]] = {}
        self.regulatory_reports: List[RegulatoryReport] = []
        self.violations_log: List[Dict[str, Any]] = []
        
        # Risk scoring cache
        self.risk_scores: Dict[str, float] = {}
        
        # Start reporting task
        self._start_regulatory_reporting()
    
    def _start_regulatory_reporting(self):
        """Start the regulatory reporting task"""
        async def reporting_task():
            while True:
                try:
                    await self._generate_regulatory_reports()
                    await asyncio.sleep(self.config.report_generation_interval)
                except Exception as e:
                    self.logger.error("Regulatory reporting error", error=str(e))
                    await asyncio.sleep(300)  # 5 minutes delay on error
        
        # Start the task
        asyncio.create_task(reporting_task())
        
    def _initialize_ai_agent(self) -> AIComplianceAgent:
        """Initialize the AI Compliance Agent with available provider"""
        settings = get_settings()
        provider = None
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            try:
                provider = GeminiProvider(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL or "gemini-pro")
                self.logger.info("Initialized Compliance Agent with Gemini Provider")
            except Exception as e:
                self.logger.warning("Failed to init Gemini Provider, using Mock", error=str(e))
        
        return AIComplianceAgent(provider=provider)
    
    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        """
        Process payment for compliance validation
        
        Args:
            payment: The payment to validate
            
        Returns:
            PaymentResult: The compliance validation result
        """
        try:
            self.logger.info(
                "Processing compliance for payment",
                payment_id=payment.payment_id,
                amount=payment.amount,
                from_country=payment.sender.country,
                to_country=payment.recipient.country
            )
            
            # Perform comprehensive compliance validation
            compliance_result = await self.validate_payment_compliance(payment)
            
            if not compliance_result.is_compliant:
                # Log violation
                await self._log_violation(payment, compliance_result)
                
                return PaymentResult(
                    success=False,
                    payment_id=payment.payment_id,
                    status=PaymentStatus.FAILED,
                    message=f"Compliance validation failed: {', '.join(compliance_result.violations)}",
                    error_code="COMPLIANCE_VIOLATION"
                )
            
            # Store compliance result
            self.compliance_checks[str(payment.payment_id)] = compliance_result.checks
            
            self.logger.info(
                "Compliance validation completed",
                payment_id=payment.payment_id,
                risk_level=compliance_result.risk_level,
                risk_score=compliance_result.overall_risk_score
            )
            
            return PaymentResult(
                success=True,
                payment_id=payment.payment_id,
                status=PaymentStatus.PROCESSING,
                message="Compliance validation passed"
            )
            
        except Exception as e:
            self.logger.error("Compliance processing failed", error=str(e))
            return PaymentResult(
                success=False,
                payment_id=payment.payment_id,
                status=PaymentStatus.FAILED,
                message=f"Compliance processing failed: {str(e)}",
                error_code="COMPLIANCE_ERROR"
            )
    
    async def validate_payment(self, payment: CrossBorderPayment) -> bool:
        """Validate if payment can be processed by this agent"""
        try:
            # Check if payment has required fields
            if not payment.payment_id or not payment.amount:
                return False
            
            # Check if sender and recipient information is complete
            if not payment.sender or not payment.recipient:
                return False
            
            # Check if countries are valid
            if not payment.sender.country or not payment.recipient.country:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Payment validation failed", error=str(e))
            return False
    
    async def validate_payment_compliance(self, payment: CrossBorderPayment) -> ComplianceResult:
        """
        Comprehensive compliance validation for payment
        
        Args:
            payment: The payment to validate
            
        Returns:
            ComplianceResult: The compliance validation result
        """
        try:
            start_time = datetime.now(timezone.utc)
            checks = []
            violations = []
            required_actions = []
            
            # 1. KYC Compliance Check
            kyc_check = await self._perform_kyc_check(payment)
            checks.append(kyc_check)
            
            if kyc_check.status == "failed":
                violations.extend(kyc_check.details.get("violations", []))
                required_actions.extend(kyc_check.details.get("required_actions", []))
            
            # 2. AML Compliance Check
            aml_check = await self._perform_aml_check(payment)
            checks.append(aml_check)
            
            if aml_check.status == "failed":
                violations.extend(aml_check.details.get("violations", []))
                required_actions.extend(aml_check.details.get("required_actions", []))
            
            # 3. Sanctions Screening
            sanctions_check = await self._perform_sanctions_check(payment)
            checks.append(sanctions_check)
            
            if sanctions_check.status == "failed":
                violations.extend(sanctions_check.details.get("violations", []))
                required_actions.extend(sanctions_check.details.get("required_actions", []))
            
            # 4. PEP Screening (if enabled)
            if self.config.pep_check_enabled:
                pep_check = await self._perform_pep_check(payment)
                checks.append(pep_check)
                
                if pep_check.status == "failed":
                    violations.extend(pep_check.details.get("violations", []))
                    required_actions.extend(pep_check.details.get("required_actions", []))
            
            # 5. Adverse Media Screening (if enabled)
            if self.config.adverse_media_check_enabled:
                media_check = await self._perform_adverse_media_check(payment)
                checks.append(media_check)
                
                if media_check.status == "failed":
                    violations.extend(media_check.details.get("violations", []))
                    required_actions.extend(media_check.details.get("required_actions", []))
            
            # Calculate overall risk score
            overall_risk_score = self._calculate_overall_risk_score(checks)
            risk_level = self._determine_risk_level(overall_risk_score)
            
            # Determine compliance status
            is_compliant = len(violations) == 0 and overall_risk_score < self.config.high_risk_score_threshold
            
            # --- AI AUTONOMOUS REVIEW ---
            # If standard checks failed or are borderline (Medium Risk), consult AI
            if (not is_compliant) or (risk_level == "medium"):
                self.logger.info("Triggering AI Autonomous Review", risk_level=risk_level, violations=violations)
                
                ai_check = await self._perform_ai_risk_assessment(payment, violations)
                checks.append(ai_check)
                
                # If AI says "SAFE", we can override logical violations (e.g. false positives)
                # But only if risk score wasn't extreme (e.g. > 0.9)
                if ai_check.status == "passed" and overall_risk_score < 0.9:
                    self.logger.info("AI Overrode Compliance Failure", reasoning=ai_check.details.get("reasoning"))
                    is_compliant = True
                    violations = [] # Clear violations
                    overall_risk_score = 0.5 # Reset to medium/safe
                    risk_level = "medium"
                    required_actions.append("AI Approved: Monitored")
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            self.logger.info(
                "Compliance validation completed",
                payment_id=payment.payment_id,
                risk_score=overall_risk_score,
                risk_level=risk_level,
                is_compliant=is_compliant,
                violations_count=len(violations),
                processing_time_ms=processing_time
            )
            
            return ComplianceResult(
                success=is_compliant,
                payment_id=str(payment.payment_id),
                overall_risk_score=overall_risk_score,
                risk_level=risk_level,
                checks=checks,
                violations=violations,
                required_actions=required_actions,
                is_compliant=is_compliant,
                message="Compliance validation completed"
            )
            
        except Exception as e:
            self.logger.error("Compliance validation failed", error=str(e))
            return ComplianceResult(
                success=False,
                payment_id=str(payment.payment_id),
                overall_risk_score=1.0,
                risk_level="high",
                checks=[],
                violations=[f"Compliance validation error: {str(e)}"],
                required_actions=["Contact compliance team"],
                is_compliant=False,
                message=f"Compliance validation failed: {str(e)}"
            )
    
    async def check_sanctions(self, parties: List[Dict[str, Any]]) -> SanctionsResult:
        """
        Real-time sanctions screening
        
        Args:
            parties: List of parties to screen (sender, recipient, etc.)
            
        Returns:
            SanctionsResult: Sanctions screening result
        """
        try:
            self.logger.info("Performing sanctions screening", parties_count=len(parties))
            
            matches_found = []
            risk_score = 0.0
            
            # Extract party information and screen
            parties_to_check = []
            
            for party in parties:
                name = party.get("name")
                # Also check wallet if available (not currently in party dict but good to have)
                wallet = party.get("wallet_address")
                country = party.get("country")
                
                if name:
                    parties_to_check.append(name)
                    result = await self.sanctions_service.screening_check(
                        name=name,
                        wallet_address=wallet,
                        country=country
                    )
                    
                    if result["is_sanctioned"]:
                        matches_found.append(f"{name} ({result['reason']})")
                        risk_score = max(risk_score, 1.0) # Sanctions hit is auto-fail
            
            is_compliant = len(matches_found) == 0
            
            self.logger.info(
                "Sanctions screening completed",
                parties_checked=parties_to_check,
                matches_found=matches_found,
                risk_score=risk_score,
                is_compliant=is_compliant
            )
            
            return SanctionsResult(
                success=True,
                parties_checked=parties_to_check,
                matches_found=matches_found,
                risk_score=risk_score,
                is_compliant=is_compliant,
                violations=matches_found,
                message="Sanctions screening completed"
            )
            
        except Exception as e:
            self.logger.error("Sanctions screening failed", error=str(e))
            return SanctionsResult(
                success=False,
                parties_checked=[],
                matches_found=[],
                risk_score=1.0,
                is_compliant=False,
                violations=[f"Sanctions screening error: {str(e)}"],
                message=f"Sanctions screening failed: {str(e)}"
            )
    
    async def generate_regulatory_report(self, payments: List[CrossBorderPayment]) -> RegulatoryReport:
        """
        Generate automated regulatory compliance report
        
        Args:
            payments: List of payments for the reporting period
            
        Returns:
            RegulatoryReport: Generated regulatory report
        """
        try:
            self.logger.info("Generating regulatory report", payments_count=len(payments))
            
            # Calculate report period
            if payments:
                period_start = min(p.created_at for p in payments)
                period_end = max(p.created_at for p in payments)
            else:
                period_start = datetime.now(timezone.utc)
                period_end = datetime.now(timezone.utc)
            
            # Calculate metrics
            total_transactions = len(payments)
            total_volume = sum(p.amount for p in payments)
            
            # Calculate compliance rate
            compliant_payments = [p for p in payments if p.status != PaymentStatus.FAILED]
            compliance_rate = len(compliant_payments) / total_transactions if total_transactions > 0 else 1.0
            
            # Count violations
            violations_count = len(self.violations_log)
            
            # Calculate risk distribution
            risk_distribution = {"low": 0, "medium": 0, "high": 0}
            for payment in payments:
                risk_score = self.risk_scores.get(str(payment.payment_id), 0.0)
                if risk_score < self.config.medium_risk_score_threshold:
                    risk_distribution["low"] += 1
                elif risk_score < self.config.high_risk_score_threshold:
                    risk_distribution["medium"] += 1
                else:
                    risk_distribution["high"] += 1
            
            # Generate report content
            report_content = {
                "summary": {
                    "total_transactions": total_transactions,
                    "total_volume": float(total_volume),
                    "compliance_rate": compliance_rate,
                    "violations_count": violations_count
                },
                "risk_analysis": {
                    "risk_distribution": risk_distribution,
                    "high_risk_transactions": risk_distribution["high"],
                    "average_risk_score": sum(self.risk_scores.values()) / len(self.risk_scores) if self.risk_scores else 0.0
                },
                "violations": self.violations_log[-10:],  # Last 10 violations
                "recommendations": self._generate_compliance_recommendations(payments)
            }
            
            report = RegulatoryReport(
                report_id=f"reg_report_{datetime.now().timestamp()}",
                report_type="daily",
                period_start=period_start,
                period_end=period_end,
                total_transactions=total_transactions,
                total_volume=total_volume,
                compliance_rate=compliance_rate,
                violations_count=violations_count,
                risk_distribution=risk_distribution,
                generated_at=datetime.now(timezone.utc),
                content=report_content
            )
            
            # Store report
            self.regulatory_reports.append(report)
            
            self.logger.info(
                "Regulatory report generated",
                report_id=report.report_id,
                compliance_rate=compliance_rate,
                violations_count=violations_count
            )
            
            return report
            
        except Exception as e:
            self.logger.error("Failed to generate regulatory report", error=str(e))
            raise
    
    async def _perform_kyc_check(self, payment: CrossBorderPayment) -> ComplianceCheck:
        """Perform KYC compliance check"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Check KYC compliance using compliance service
            kyc_result = await self.compliance_service.check_kyc_compliance(
                payment.sender.country,
                payment.recipient.country,
                float(payment.amount)
            )
            
            # Calculate risk score based on amount and countries
            risk_score = 0.0
            if payment.amount > Decimal(str(self.config.enhanced_due_diligence_threshold)):
                risk_score += 0.3
            if payment.sender.country in ["NGN", "GHS"]:  # High-risk countries for demo
                risk_score += 0.2
            
            processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return ComplianceCheck(
                check_id=f"kyc_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="kyc",
                status="passed" if kyc_result.is_compliant else "failed",
                risk_score=risk_score,
                details={
                    "is_compliant": kyc_result.is_compliant,
                    "violations": kyc_result.violations,
                    "required_actions": kyc_result.required_actions,
                    "threshold_amount": self.config.kyc_threshold_amount
                },
                timestamp=datetime.now(timezone.utc),
                duration_ms=processing_time
            )
            
        except Exception as e:
            self.logger.error("KYC check failed", error=str(e))
            return ComplianceCheck(
                check_id=f"kyc_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="kyc",
                status="error",
                risk_score=1.0,
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            )
    
    async def _perform_aml_check(self, payment: CrossBorderPayment) -> ComplianceCheck:
        """Perform AML compliance check using FraudDetectionService"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Call Fraud Service
            fraud_result = await self.fraud_service.analyze_transaction(
                user_id=str(payment.sender.dict().get("sender_id", "anonymous")),
                amount=float(payment.amount)
            )
            
            risk_score = fraud_result["risk_score"]
            violations = fraud_result["flags"]
            required_actions = []
            
            if risk_score > 0.5:
                 required_actions.append("EDD Required")

            processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return ComplianceCheck(
                check_id=f"aml_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="aml",
                status="passed" if risk_score < self.config.high_risk_score_threshold else "failed",
                risk_score=risk_score,
                details={
                    "violations": violations,
                    "required_actions": required_actions,
                    "is_high_risk": fraud_result["is_high_risk"]
                },
                timestamp=datetime.now(timezone.utc),
                duration_ms=processing_time
            )
            
        except Exception as e:
            self.logger.error("AML check failed", error=str(e))
            return ComplianceCheck(
                check_id=f"aml_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="aml",
                status="error",
                risk_score=1.0,
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            )
    
    async def _perform_sanctions_check(self, payment: CrossBorderPayment) -> ComplianceCheck:
        """Perform sanctions screening"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Perform sanctions check - Convert models to dicts
            sanctions_result = await self.check_sanctions([
                payment.sender.dict(), 
                payment.recipient.dict()
            ])
            
            processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return ComplianceCheck(
                check_id=f"sanctions_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="sanctions",
                status="passed" if sanctions_result.is_compliant else "failed",
                risk_score=sanctions_result.risk_score,
                details={
                    "parties_checked": sanctions_result.parties_checked,
                    "matches_found": sanctions_result.matches_found,
                    "violations": sanctions_result.violations
                },
                timestamp=datetime.now(timezone.utc),
                duration_ms=processing_time
            )
            
        except Exception as e:
            self.logger.error("Sanctions check failed", error=str(e))
            return ComplianceCheck(
                check_id=f"sanctions_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="sanctions",
                status="error",
                risk_score=1.0,
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            )
    
    async def _perform_pep_check(self, payment: CrossBorderPayment) -> ComplianceCheck:
        """Perform PEP (Politically Exposed Person) screening"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Mock PEP check
            risk_score = 0.0
            violations = []
            
            # Check for PEP indicators in names
            pep_indicators = ["minister", "president", "governor", "senator", "official"]
            sender_name = payment.sender.name.lower()
            recipient_name = payment.recipient.name.lower()
            
            for indicator in pep_indicators:
                if indicator in sender_name or indicator in recipient_name:
                    risk_score += 0.3
                    violations.append(f"PEP indicator found: {indicator}")
            
            processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return ComplianceCheck(
                check_id=f"pep_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="pep",
                status="passed" if risk_score < 0.5 else "failed",
                risk_score=risk_score,
                details={
                    "violations": violations,
                    "pep_indicators_checked": pep_indicators
                },
                timestamp=datetime.now(timezone.utc),
                duration_ms=processing_time
            )
            
        except Exception as e:
            self.logger.error("PEP check failed", error=str(e))
            return ComplianceCheck(
                check_id=f"pep_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="pep",
                status="error",
                risk_score=1.0,
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            )
    
    async def _perform_adverse_media_check(self, payment: CrossBorderPayment) -> ComplianceCheck:
        """Perform adverse media screening"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Mock adverse media check
            risk_score = 0.0
            violations = []
            
            # Simulate media screening
            adverse_terms = ["fraud", "money laundering", "terrorism", "corruption"]
            sender_name = payment.sender.name.lower()
            recipient_name = payment.recipient.name.lower()
            
            for term in adverse_terms:
                if term in sender_name or term in recipient_name:
                    risk_score += 0.4
                    violations.append(f"Adverse media indicator: {term}")
            
            processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return ComplianceCheck(
                check_id=f"media_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="adverse_media",
                status="passed" if risk_score < 0.5 else "failed",
                risk_score=risk_score,
                details={
                    "violations": violations,
                    "adverse_terms_checked": adverse_terms
                },
                timestamp=datetime.now(timezone.utc),
                duration_ms=processing_time
            )
            
        except Exception as e:
            self.logger.error("Adverse media check failed", error=str(e))
            return ComplianceCheck(
                check_id=f"media_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="adverse_media",
                status="error",
                risk_score=1.0,
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            )
    
    async def _perform_ai_risk_assessment(self, payment: CrossBorderPayment, current_violations: List[str]) -> ComplianceCheck:
        """Perform AI-based Autonomous Risk Assessment"""
        start_time = datetime.now(timezone.utc)
        try:
            # Call package agent
            ai_result = await self.ai_agent.evaluate_transaction(payment)
            
            is_compliant = ai_result.get("is_compliant", False)
            risk_score = ai_result.get("risk_score", 0.5)
            reasoning = ai_result.get("reasoning", "No reasoning provided")
            
            processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return ComplianceCheck(
                check_id=f"ai_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="ai_review",
                status="passed" if is_compliant else "failed",
                risk_score=risk_score,
                details={
                    "reasoning": reasoning,
                    "violations_context": current_violations,
                    "model_decision": "APPROVE" if is_compliant else "REJECT"
                },
                timestamp=datetime.now(timezone.utc),
                duration_ms=processing_time
            )
        except Exception as e:
            self.logger.error("AI check failed", error=str(e))
            return ComplianceCheck(
                check_id=f"ai_{payment.payment_id}_{datetime.now().timestamp()}",
                check_type="ai_review",
                status="error",
                risk_score=1.0,
                details={"error": str(e)},
                timestamp=datetime.now(timezone.utc),
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            )

    def _calculate_overall_risk_score(self, checks: List[ComplianceCheck]) -> float:
        """Calculate overall risk score from individual checks"""
        if not checks:
            return 0.0
        
        # Weight different check types
        weights = {
            "kyc": 0.3,
            "aml": 0.3,
            "sanctions": 0.2,
            "pep": 0.1,
            "adverse_media": 0.1
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for check in checks:
            weight = weights.get(check.check_type, 0.1)
            weighted_score += check.risk_score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level based on score"""
        if risk_score >= self.config.high_risk_score_threshold:
            return "high"
        elif risk_score >= self.config.medium_risk_score_threshold:
            return "medium"
        else:
            return "low"
    
    async def _log_violation(self, payment: CrossBorderPayment, compliance_result: ComplianceResult):
        """Log compliance violation"""
        violation = {
            "payment_id": str(payment.payment_id),
            "timestamp": datetime.now(timezone.utc),
            "amount": float(payment.amount),
            "from_country": payment.sender.country,
            "to_country": payment.recipient.country,
            "risk_score": compliance_result.overall_risk_score,
            "risk_level": compliance_result.risk_level,
            "violations": compliance_result.violations,
            "required_actions": compliance_result.required_actions
        }
        
        self.violations_log.append(violation)
        
        # Store in cache for reporting
        await self.cache.set(
            f"compliance_violation:{payment.payment_id}",
            violation,
            86400  # 24 hours TTL
        )
    
    def _generate_compliance_recommendations(self, payments: List[CrossBorderPayment]) -> List[str]:
        """Generate compliance recommendations based on payment data"""
        recommendations = []
        
        if not payments:
            return recommendations
        
        # Analyze patterns and generate recommendations
        high_risk_count = sum(1 for p in payments if self.risk_scores.get(str(p.payment_id), 0) > 0.7)
        
        if high_risk_count > len(payments) * 0.1:  # More than 10% high risk
            recommendations.append("Consider implementing additional screening for high-risk transactions")
        
        if len(self.violations_log) > 5:
            recommendations.append("Review compliance procedures and enhance monitoring")
        
        if any(p.amount > Decimal("10000") for p in payments):
            recommendations.append("Implement enhanced due diligence for large transactions")
        
        return recommendations
    
    async def _generate_regulatory_reports(self):
        """Generate periodic regulatory reports"""
        try:
            # Get payments from the last 24 hours (mock data)
            # In real implementation, this would query the database
            mock_payments = []  # This would be actual payment data
            
            if mock_payments:
                report = await self.generate_regulatory_report(mock_payments)
                self.logger.info("Generated regulatory report", report_id=report.report_id)
            
        except Exception as e:
            self.logger.error("Failed to generate regulatory reports", error=str(e))
    
    async def get_compliance_analytics(self) -> Dict[str, Any]:
        """Get compliance analytics"""
        try:
            total_checks = sum(len(checks) for checks in self.compliance_checks.values())
            passed_checks = sum(
                sum(1 for check in checks if check.status == "passed")
                for checks in self.compliance_checks.values()
            )
            
            compliance_rate = passed_checks / total_checks if total_checks > 0 else 1.0
            
            return {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "compliance_rate": compliance_rate,
                "violations_count": len(self.violations_log),
                "reports_generated": len(self.regulatory_reports),
                "average_risk_score": sum(self.risk_scores.values()) / len(self.risk_scores) if self.risk_scores else 0.0
            }
            
        except Exception as e:
            self.logger.error("Failed to get compliance analytics", error=str(e))
            return {} 