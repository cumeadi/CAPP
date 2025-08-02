"""
Agent Templates Package

Reusable agent templates that extract proven logic from CAPP agents,
delivering 91% cost reduction through intelligent multi-objective optimization.

These templates can be configured and customized for different use cases
while preserving the core intelligence that makes the system work.
"""

from .payment_optimizer import (
    PaymentOptimizerAgent,
    PaymentOptimizerConfig,
    OptimizationStrategy,
    RouteType,
    RouteScore,
    OptimizationResult
)

from .compliance_checker import (
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
    # Payment Optimizer
    "PaymentOptimizerAgent",
    "PaymentOptimizerConfig",
    "OptimizationStrategy",
    "RouteType",
    "RouteScore",
    "OptimizationResult",
    
    # Compliance Checker
    "ComplianceCheckerAgent",
    "ComplianceCheckerConfig",
    "ComplianceLevel",
    "CheckType",
    "ComplianceCheck",
    "ComplianceResult",
    "SanctionsResult",
    "RegulatoryReport",
] 