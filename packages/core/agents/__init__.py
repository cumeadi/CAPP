"""
Core Agents Package

Financial agents for payment processing, optimization, and compliance.
Includes reusable agent templates that extract proven logic from CAPP.
"""

from .base import BaseFinancialAgent, AgentConfig
from .financial_base import FinancialTransaction, TransactionResult
from .agent_factory import AgentFactory
from .agent_registry import AgentRegistry

# Agent Templates
from .templates import (
    PaymentOptimizerAgent,
    PaymentOptimizerConfig,
    OptimizationStrategy,
    RouteType,
    RouteScore,
    OptimizationResult,
    ComplianceCheckerAgent,
    ComplianceCheckerConfig,
    ComplianceLevel,
    CheckType,
    ComplianceCheck,
    ComplianceResult,
    SanctionsResult,
    RegulatoryReport
)

__all__ = [
    # Base classes
    "BaseFinancialAgent",
    "AgentConfig",
    "FinancialTransaction",
    "TransactionResult",
    
    # Factory and Registry
    "AgentFactory",
    "AgentRegistry",
    
    # Agent Templates
    "PaymentOptimizerAgent",
    "PaymentOptimizerConfig",
    "OptimizationStrategy",
    "RouteType",
    "RouteScore",
    "OptimizationResult",
    "ComplianceCheckerAgent",
    "ComplianceCheckerConfig",
    "ComplianceLevel",
    "CheckType",
    "ComplianceCheck",
    "ComplianceResult",
    "SanctionsResult",
    "RegulatoryReport",
] 