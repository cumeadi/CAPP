"""
Core Agents Package

Financial agents for payment processing, optimization, and compliance.
Includes reusable agent templates that extract proven logic from CAPP.
"""

# Core base classes — lightweight, no heavy integration dependencies.
from .base import BaseFinancialAgent, AgentConfig
from .financial_base import FinancialTransaction, FinancialProcessingResult
from .agent_registry import AgentRegistry

# Heavy imports (templates, factory, integrations) are deferred so that
# importing a single sub-module (e.g. packages.core.agents.base) does NOT
# drag in the full integration/provider stack.
def __getattr__(name):
    _TEMPLATE_NAMES = {
        "PaymentOptimizerAgent", "PaymentOptimizerConfig", "OptimizationStrategy",
        "RouteType", "RouteScore", "OptimizationResult",
        "ComplianceCheckerAgent", "ComplianceCheckerConfig", "ComplianceLevel",
        "CheckType", "ComplianceCheck", "ComplianceResult",
        "SanctionsResult", "RegulatoryReport",
    }
    if name in _TEMPLATE_NAMES:
        from .templates import (  # noqa: PLC0415
            PaymentOptimizerAgent, PaymentOptimizerConfig, OptimizationStrategy,
            RouteType, RouteScore, OptimizationResult,
            ComplianceCheckerAgent, ComplianceCheckerConfig, ComplianceLevel,
            CheckType, ComplianceCheck, ComplianceResult,
            SanctionsResult, RegulatoryReport,
        )
        return locals()[name]
    if name == "AgentFactory":
        from .agent_factory import AgentFactory  # noqa: PLC0415
        return AgentFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Base classes
    "BaseFinancialAgent",
    "AgentConfig",
    "FinancialTransaction",
    "FinancialProcessingResult",

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
