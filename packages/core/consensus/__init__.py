"""
Consensus Module

Handles multi-agent consensus mechanisms for payment decisions.
"""

from .mechanisms import ConsensusEngine, ConsensusConfig, ConsensusResult, ConsensusType, AgentConsensusResult
from .voting import VotingEngine, VotingStrategy, Vote, VotingSession, VotingResult
from .agreement import AgreementProtocol

__all__ = [
    "ConsensusEngine",
    "ConsensusConfig",
    "ConsensusResult",
    "ConsensusType",
    "AgentConsensusResult",
    "VotingEngine",
    "VotingStrategy",
    "Vote",
    "VotingSession",
    "VotingResult",
    "AgreementProtocol",
]
