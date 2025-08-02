"""
Financial-specific base agent classes

This module provides specialized base classes for financial applications
with domain-specific validation, compliance checking, and financial metrics.
"""

from abc import abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
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
    
    def __init__(self, config: FinancialAgentConfig):
        super().__init__(config)
        self.financial_config = config
        self.logger = structlog.get_logger(f"financial.{self.agent_type}.{self.agent_id}")
    
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
            # Base risk assessment - can be overridden by specific agents
            base_risk = 0.1
            
            # Amount-based risk
            if transaction.amount > Decimal('10000'):
                base_risk += 0.2
            elif transaction.amount > Decimal('1000'):
                base_risk += 0.1
            
            # Compliance-based risk
            if transaction.compliance_level == ComplianceLevel.CRITICAL:
                base_risk += 0.3
            elif transaction.compliance_level == ComplianceLevel.HIGH:
                base_risk += 0.2
            
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
            # Base fee calculation - can be overridden by specific agents
            base_fee = Decimal('0.01')  # 1% base fee
            
            # Amount-based fee
            amount_fee = transaction.amount * Decimal('0.005')  # 0.5% of amount
            
            # Compliance-based fee
            compliance_fee = Decimal('0')
            if transaction.compliance_level == ComplianceLevel.CRITICAL:
                compliance_fee = Decimal('5.00')
            elif transaction.compliance_level == ComplianceLevel.HIGH:
                compliance_fee = Decimal('2.00')
            
            total_fee = base_fee + amount_fee + compliance_fee
            
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