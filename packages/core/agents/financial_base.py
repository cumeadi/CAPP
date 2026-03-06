"""
Financial-specific base agent classes

This module provides specialized base classes for financial applications
with domain-specific validation, compliance checking, and financial metrics.
"""

from abc import abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Awaitable, Dict, List, Optional, Any, Union
from enum import Enum

import structlog
from pydantic import BaseModel, Field, validator

from .base import BaseFinancialAgent, AgentConfig, ProcessingResult


logger = structlog.get_logger(__name__)


class TransactionType(str, Enum):
    """Types of financial transactions"""
    PAYMENT = "payment"
    TRANSFER = "transfer"
    EXCHANGE = "exchange"
    SETTLEMENT = "settlement"
    COMPLIANCE = "compliance"
    ROUTING = "routing"
    LIQUIDITY = "liquidity"


class TransactionStatus(str, Enum):
    """Status of financial transactions"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SETTLING = "settling"


class ComplianceLevel(str, Enum):
    """Compliance levels for financial transactions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FinancialTransaction(BaseModel):
    """Base model for financial transactions"""
    id: str
    transaction_type: TransactionType
    amount: Decimal
    currency: str
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Compliance
    compliance_level: ComplianceLevel = ComplianceLevel.MEDIUM
    risk_score: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v
    
    @validator('risk_score')
    def validate_risk_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Risk score must be between 0 and 1')
        return v


class FinancialProcessingResult(ProcessingResult):
    """Extended processing result for financial transactions"""
    transaction_type: TransactionType
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    compliance_level: Optional[ComplianceLevel] = None
    risk_score: Optional[float] = None
    fees: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    settlement_time: Optional[float] = None


class FinancialAgentConfig(AgentConfig):
    """Configuration for financial agents"""
    # Financial-specific settings
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    supported_currencies: List[str] = Field(default_factory=list)
    compliance_required: bool = True
    risk_threshold: float = 0.8
    
    # Processing preferences
    prioritize_speed: bool = False
    prioritize_cost: bool = True
    prioritize_compliance: bool = True
    
    # Timeouts
    compliance_timeout: float = 30.0
    settlement_timeout: float = 60.0


# ---------------------------------------------------------------------------
# Loader type aliases
# ---------------------------------------------------------------------------

# FeeLoader: returns (base_fee, amount_fee_pct, compliance_surcharge) as Decimals
# for the given (transaction_type, compliance_level).
FeeLoader = Callable[
    [str, str],
    Awaitable[tuple],  # (Decimal base_fee, Decimal amount_fee_pct, Decimal surcharge)
]

# RiskLoader: returns a list of (rule_type, condition_value, risk_increment) rows.
RiskLoader = Callable[[], Awaitable[List[Dict[str, Any]]]]

# ---------------------------------------------------------------------------
# Default (hardcoded) fee and risk data — preserved as fallback
# ---------------------------------------------------------------------------

async def _default_fee_loader(transaction_type: str, compliance_level: str) -> tuple:
    """Fallback fee schedule matching original financial_base.py constants."""
    base_fee = Decimal('0.01')
    amount_fee_pct = Decimal('0.005')
    surcharge = Decimal('0')
    if compliance_level == 'critical':
        surcharge = Decimal('5.00')
    elif compliance_level == 'high':
        surcharge = Decimal('2.00')
    return base_fee, amount_fee_pct, surcharge


async def _default_risk_loader() -> List[Dict[str, Any]]:
    """Fallback risk rules matching original financial_base.py constants."""
    return [
        {"rule_type": "base",              "condition_value": None,       "risk_increment": 0.1},
        {"rule_type": "amount_threshold",  "condition_value": "10000",    "risk_increment": 0.2},
        {"rule_type": "amount_threshold",  "condition_value": "1000",     "risk_increment": 0.1},
        {"rule_type": "compliance_level",  "condition_value": "critical", "risk_increment": 0.3},
        {"rule_type": "compliance_level",  "condition_value": "high",     "risk_increment": 0.2},
    ]


def make_db_fee_loader(db_session_factory: Callable) -> FeeLoader:
    """
    Factory that returns a FeeLoader backed by the fee_schedules table.

    Args:
        db_session_factory: Zero-argument callable returning a SQLAlchemy Session.
    """
    async def _loader(transaction_type: str, compliance_level: str) -> tuple:
        try:
            db = db_session_factory()
            try:
                from sqlalchemy import text
                row = db.execute(
                    text(
                        "SELECT base_fee, amount_fee_pct, compliance_surcharge "
                        "FROM fee_schedules "
                        "WHERE transaction_type IN (:tx_type, 'default') "
                        "  AND compliance_level = :level "
                        "  AND is_active = true "
                        "ORDER BY CASE WHEN transaction_type = :tx_type THEN 0 ELSE 1 END "
                        "LIMIT 1"
                    ),
                    {"tx_type": transaction_type, "level": compliance_level},
                ).fetchone()
                if row:
                    return Decimal(str(row[0])), Decimal(str(row[1])), Decimal(str(row[2]))
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "DB fee schedule lookup failed — using defaults",
                error=str(exc),
            )
        return await _default_fee_loader(transaction_type, compliance_level)

    return _loader


def make_db_risk_loader(db_session_factory: Callable) -> RiskLoader:
    """
    Factory that returns a RiskLoader backed by the risk_rules table.

    Args:
        db_session_factory: Zero-argument callable returning a SQLAlchemy Session.
    """
    async def _loader() -> List[Dict[str, Any]]:
        try:
            db = db_session_factory()
            try:
                from sqlalchemy import text
                rows = db.execute(
                    text(
                        "SELECT rule_type, condition_value, risk_increment "
                        "FROM risk_rules "
                        "WHERE is_active = true"
                    )
                ).fetchall()
                return [
                    {
                        "rule_type": r[0],
                        "condition_value": r[1],
                        "risk_increment": float(r[2]),
                    }
                    for r in rows
                ]
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "DB risk rules lookup failed — using defaults",
                error=str(exc),
            )
        return await _default_risk_loader()

    return _loader


class BaseFinancialAgent(BaseFinancialAgent[FinancialTransaction]):
    """
    Base class for financial agents with domain-specific functionality

    Extends the generic base agent with financial domain knowledge:
    - Amount validation
    - Currency validation
    - Compliance checking
    - Risk assessment
    - Financial metrics
    """

    def __init__(
        self,
        config: FinancialAgentConfig,
        fee_loader: Optional[FeeLoader] = None,
        risk_loader: Optional[RiskLoader] = None,
    ):
        super().__init__(config)
        self.financial_config = config
        self.logger = structlog.get_logger(f"financial.{self.agent_type}.{self.agent_id}")
        self._fee_loader: FeeLoader = fee_loader or _default_fee_loader
        self._risk_loader: RiskLoader = risk_loader or _default_risk_loader
    
    async def validate_transaction(self, transaction: FinancialTransaction) -> bool:
        """
        Validate financial transaction with domain-specific rules
        
        Args:
            transaction: The financial transaction to validate
            
        Returns:
            bool: True if transaction is valid, False otherwise
        """
        try:
            # Basic validation
            if not await super().validate_transaction(transaction):
                return False
            
            # Amount validation
            if not await self._validate_amount(transaction):
                return False
            
            # Currency validation
            if not await self._validate_currency(transaction):
                return False
            
            # Compliance validation
            if self.financial_config.compliance_required:
                if not await self._validate_compliance(transaction):
                    return False
            
            # Risk validation
            if not await self._validate_risk(transaction):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Transaction validation failed", error=str(e))
            return False
    
    async def _validate_amount(self, transaction: FinancialTransaction) -> bool:
        """Validate transaction amount"""
        try:
            # Check minimum amount
            if (self.financial_config.min_amount and 
                transaction.amount < self.financial_config.min_amount):
                self.logger.warning(
                    "Transaction amount below minimum",
                    amount=transaction.amount,
                    min_amount=self.financial_config.min_amount
                )
                return False
            
            # Check maximum amount
            if (self.financial_config.max_amount and 
                transaction.amount > self.financial_config.max_amount):
                self.logger.warning(
                    "Transaction amount above maximum",
                    amount=transaction.amount,
                    max_amount=self.financial_config.max_amount
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Amount validation failed", error=str(e))
            return False
    
    async def _validate_currency(self, transaction: FinancialTransaction) -> bool:
        """Validate transaction currency"""
        try:
            # Check if currency is supported
            if (self.financial_config.supported_currencies and 
                transaction.currency not in self.financial_config.supported_currencies):
                self.logger.warning(
                    "Currency not supported",
                    currency=transaction.currency,
                    supported_currencies=self.financial_config.supported_currencies
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Currency validation failed", error=str(e))
            return False
    
    async def _validate_compliance(self, transaction: FinancialTransaction) -> bool:
        """Validate compliance requirements"""
        try:
            # Basic compliance check - can be overridden by specific agents
            # In real implementation, this would check against compliance rules
            return True
            
        except Exception as e:
            self.logger.error("Compliance validation failed", error=str(e))
            return False
    
    async def _validate_risk(self, transaction: FinancialTransaction) -> bool:
        """Validate risk assessment"""
        try:
            # Check risk threshold
            if transaction.risk_score > self.financial_config.risk_threshold:
                self.logger.warning(
                    "Transaction risk too high",
                    risk_score=transaction.risk_score,
                    threshold=self.financial_config.risk_threshold
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Risk validation failed", error=str(e))
            return False
    
    async def assess_risk(self, transaction: FinancialTransaction) -> float:
        """
        Assess risk for a financial transaction
        
        Args:
            transaction: The transaction to assess
            
        Returns:
            float: Risk score between 0 and 1
        """
        try:
            rules = await self._risk_loader()
            base_risk = 0.0
            compliance_str = transaction.compliance_level.value

            for rule in rules:
                rtype = rule.get("rule_type", "")
                condition = rule.get("condition_value")
                increment = float(rule.get("risk_increment", 0))

                if rtype == "base":
                    base_risk += increment
                elif rtype == "amount_threshold" and condition is not None:
                    threshold = Decimal(str(condition))
                    # Only the highest-matching threshold contributes.
                    # Rules are ordered high→low by convention (as seeded).
                    if transaction.amount > threshold:
                        base_risk += increment
                        break  # stop after first matching amount threshold
                elif rtype == "compliance_level" and condition is not None:
                    if compliance_str == condition:
                        base_risk += increment

            # Ensure risk score is between 0 and 1
            return min(max(base_risk, 0.0), 1.0)

        except Exception as e:
            self.logger.error("Risk assessment failed", error=str(e))
            return 1.0  # Return high risk on error
    
    async def calculate_fees(self, transaction: FinancialTransaction) -> Decimal:
        """
        Calculate fees for a financial transaction
        
        Args:
            transaction: The transaction to calculate fees for
            
        Returns:
            Decimal: Calculated fees
        """
        try:
            tx_type = transaction.transaction_type.value
            compliance_str = transaction.compliance_level.value

            base_fee, amount_fee_pct, compliance_surcharge = await self._fee_loader(
                tx_type, compliance_str
            )

            amount_fee = transaction.amount * amount_fee_pct
            total_fee = base_fee + amount_fee + compliance_surcharge
            return total_fee

        except Exception as e:
            self.logger.error("Fee calculation failed", error=str(e))
            return Decimal('0')
    
    async def process_transaction(self, transaction: FinancialTransaction) -> FinancialProcessingResult:
        """
        Process a financial transaction
        
        Args:
            transaction: The transaction to process
            
        Returns:
            FinancialProcessingResult: The processing result
        """
        try:
            # Update transaction status
            transaction.status = TransactionStatus.PROCESSING
            transaction.updated_at = datetime.now(timezone.utc)
            
            # Assess risk
            risk_score = await self.assess_risk(transaction)
            transaction.risk_score = risk_score
            
            # Calculate fees
            fees = await self.calculate_fees(transaction)
            
            # Process the transaction (to be implemented by subclasses)
            result = await self._process_financial_transaction(transaction)
            
            # Create financial processing result
            return FinancialProcessingResult(
                success=result.success,
                transaction_id=transaction.id,
                status=transaction.status.value,
                message=result.message,
                error_code=result.error_code,
                processing_time=result.processing_time,
                metadata=result.metadata,
                transaction_type=transaction.transaction_type,
                amount=transaction.amount,
                currency=transaction.currency,
                compliance_level=transaction.compliance_level,
                risk_score=risk_score,
                fees=fees
            )
            
        except Exception as e:
            self.logger.error("Financial transaction processing failed", error=str(e))
            return FinancialProcessingResult(
                success=False,
                transaction_id=transaction.id,
                status=TransactionStatus.FAILED.value,
                message=f"Processing failed: {str(e)}",
                error_code="PROCESSING_ERROR",
                transaction_type=transaction.transaction_type,
                amount=transaction.amount,
                currency=transaction.currency
            )
    
    @abstractmethod
    async def _process_financial_transaction(self, transaction: FinancialTransaction) -> ProcessingResult:
        """
        Process the financial transaction (to be implemented by subclasses)
        
        Args:
            transaction: The transaction to process
            
        Returns:
            ProcessingResult: The processing result
        """
        pass
    
    async def get_financial_metrics(self) -> Dict[str, Any]:
        """Get financial-specific metrics"""
        try:
            base_metrics = await self.get_health_status()
            
            # Add financial-specific metrics
            financial_metrics = {
                **base_metrics,
                "total_amount_processed": 0.0,  # To be implemented
                "average_transaction_amount": 0.0,  # To be implemented
                "total_fees_collected": 0.0,  # To be implemented
                "average_risk_score": 0.0,  # To be implemented
                "compliance_violations": 0,  # To be implemented
            }
            
            return financial_metrics
            
        except Exception as e:
            self.logger.error("Failed to get financial metrics", error=str(e))
            return {} 