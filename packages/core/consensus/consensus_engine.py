"""
Re-exports ConsensusEngine from the canonical implementation.

All callers should import from this module or from
``packages.core.consensus`` directly.  The previous stub that lived here
has been removed; ``mechanisms.py`` is the single source of truth.
"""

from packages.core.consensus.mechanisms import (  # noqa: F401
    ConsensusEngine,
    ConsensusConfig,
    ConsensusResult,
    ConsensusType,
    AgentConsensusResult,
)
