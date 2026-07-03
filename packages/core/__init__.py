"""
Canza Platform Core Package

Core orchestration logic for payment processing, including:
- Payment flow orchestration
- Multi-agent consensus mechanisms
- Base agent framework
- Performance monitoring and metrics
"""

__version__ = "0.1.0"
__author__ = "Canza Team"

# Lazily re-exported so that importing individual sub-packages (e.g.
# packages.core.consensus.mechanisms) does NOT trigger the entire dependency
# chain of every module in this package.  Callers that use these top-level
# names still work; they just pay the import cost on first access.

def __getattr__(name):
    if name == "PaymentOrchestrator":
        from .orchestration import PaymentOrchestrator
        return PaymentOrchestrator
    if name == "ConsensusEngine":
        from .consensus import ConsensusEngine
        return ConsensusEngine
    if name == "BaseAgent":
        from .agents import BaseFinancialAgent as BaseAgent
        return BaseAgent
    if name == "MetricsCollector":
        from .performance import MetricsCollector
        return MetricsCollector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PaymentOrchestrator",
    "ConsensusEngine",
    "BaseAgent",
    "MetricsCollector",
]
