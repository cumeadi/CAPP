"""
Unit tests for the consolidated ConsensusEngine.

Covers:
- initialize() lifecycle
- reach_consensus() with ProcessingResult objects (orchestrator path)
- reach_consensus() with AgentResult objects (framework SDK path)
- VotingEngine end-to-end session (simple majority and weighted majority)
"""

import pytest
import asyncio
from typing import Any

from packages.core.consensus.mechanisms import (
    ConsensusEngine,
    ConsensusConfig,
    ConsensusType,
    AgentConsensusResult,
)
from packages.core.consensus.voting import (
    VotingEngine,
    VotingSession,
    VotingStrategy,
    Vote,
)
from packages.core.agents.base import ProcessingResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_processing_result(success: bool, txn_id: str = "txn-1") -> ProcessingResult:
    return ProcessingResult(
        success=success,
        transaction_id=txn_id,
        status="completed" if success else "failed",
        message="ok" if success else "err",
        processing_time=0.1,
    )


class _AgentResult:
    """Minimal stand-in for sdk.canza_agents.framework.AgentResult."""

    def __init__(self, agent_id: str, agent_type: str, success: bool, confidence: float):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.success = success
        self.confidence = confidence
        self.result: dict = {}
        self.processing_time = 0.0
        self.metadata: dict = {}


# ---------------------------------------------------------------------------
# ConsensusEngine — lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initialize_is_callable():
    engine = ConsensusEngine()
    await engine.initialize()  # must not raise


@pytest.mark.asyncio
async def test_default_config_applied():
    engine = ConsensusEngine()
    assert engine.config.threshold == 0.7
    assert engine.config.consensus_type == ConsensusType.MAJORITY


# ---------------------------------------------------------------------------
# ConsensusEngine — ProcessingResult path (orchestrator)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reach_consensus_majority_success():
    engine = ConsensusEngine(ConsensusConfig(min_agents=2, threshold=0.5))
    results = [
        make_processing_result(True, "t1"),
        make_processing_result(True, "t1"),
        make_processing_result(False, "t1"),
    ]
    result = await engine.reach_consensus(results)
    assert isinstance(result, ProcessingResult)
    assert result.success is True


@pytest.mark.asyncio
async def test_reach_consensus_majority_failure():
    engine = ConsensusEngine(ConsensusConfig(min_agents=2, threshold=0.5))
    results = [
        make_processing_result(False, "t2"),
        make_processing_result(False, "t2"),
        make_processing_result(True, "t2"),
    ]
    result = await engine.reach_consensus(results)
    assert isinstance(result, ProcessingResult)
    assert result.success is False


@pytest.mark.asyncio
async def test_reach_consensus_empty_results():
    engine = ConsensusEngine()
    result = await engine.reach_consensus([])
    assert isinstance(result, ProcessingResult)
    assert result.success is False
    assert result.error_code == "NO_RESULTS"


@pytest.mark.asyncio
async def test_reach_consensus_insufficient_agents():
    engine = ConsensusEngine(ConsensusConfig(min_agents=3, threshold=0.5))
    results = [make_processing_result(True, "t3")]
    result = await engine.reach_consensus(results)
    assert result.success is False
    assert result.error_code == "INSUFFICIENT_AGENTS"


# ---------------------------------------------------------------------------
# ConsensusEngine — AgentResult path (framework SDK)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reach_consensus_agent_results_approve():
    engine = ConsensusEngine()
    agents = [
        _AgentResult("a1", "optimizer", True, 0.9),
        _AgentResult("a2", "compliance", True, 0.8),
        _AgentResult("a3", "risk", False, 0.3),
    ]
    result = await engine.reach_consensus(agents, threshold=0.6)
    assert isinstance(result, AgentConsensusResult)
    assert result.consensus_reached is True
    assert result.recommended_action == "approve"
    assert len(result.agent_recommendations) == 3


@pytest.mark.asyncio
async def test_reach_consensus_agent_results_reject():
    engine = ConsensusEngine()
    agents = [
        _AgentResult("a1", "optimizer", False, 0.9),
        _AgentResult("a2", "compliance", False, 0.8),
        _AgentResult("a3", "risk", True, 0.1),
    ]
    result = await engine.reach_consensus(agents, threshold=0.6)
    assert isinstance(result, AgentConsensusResult)
    assert result.consensus_reached is False
    assert result.recommended_action == "reject"


@pytest.mark.asyncio
async def test_reach_consensus_agent_recommendations_shape():
    engine = ConsensusEngine()
    agents = [_AgentResult("a1", "optimizer", True, 1.0)]
    result = await engine.reach_consensus(agents, threshold=0.0)
    rec = result.agent_recommendations[0]
    assert "agent_id" in rec
    assert "agent_type" in rec
    assert "recommendation" in rec
    assert "confidence" in rec


# ---------------------------------------------------------------------------
# VotingEngine — end-to-end voting session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_voting_session_simple_majority_passes():
    engine = VotingEngine()
    session = VotingSession(
        session_id="sess-001",
        strategy=VotingStrategy.SIMPLE_MAJORITY,
        threshold=0.5,
        min_votes=2,
        max_votes=10,
    )
    await engine.create_voting_session(session)

    await engine.cast_vote("sess-001", Vote(agent_id="a1", agent_type="optimizer", vote_value=True, confidence=1.0))
    await engine.cast_vote("sess-001", Vote(agent_id="a2", agent_type="compliance", vote_value=True, confidence=1.0))
    await engine.cast_vote("sess-001", Vote(agent_id="a3", agent_type="risk", vote_value=False, confidence=1.0))

    voting_result = await engine.get_voting_result("sess-001")
    assert voting_result is not None
    assert voting_result.passed is True
    assert voting_result.total_votes == 3
    assert voting_result.vote_distribution["true"] == 2
    assert voting_result.vote_distribution["false"] == 1


@pytest.mark.asyncio
async def test_voting_session_simple_majority_fails():
    engine = VotingEngine()
    session = VotingSession(
        session_id="sess-002",
        strategy=VotingStrategy.SIMPLE_MAJORITY,
        threshold=0.67,
        min_votes=2,
        max_votes=10,
    )
    await engine.create_voting_session(session)

    await engine.cast_vote("sess-002", Vote(agent_id="a1", agent_type="optimizer", vote_value=True, confidence=1.0))
    await engine.cast_vote("sess-002", Vote(agent_id="a2", agent_type="compliance", vote_value=False, confidence=1.0))
    await engine.cast_vote("sess-002", Vote(agent_id="a3", agent_type="risk", vote_value=False, confidence=1.0))

    voting_result = await engine.get_voting_result("sess-002")
    assert voting_result is not None
    assert voting_result.passed is False


@pytest.mark.asyncio
async def test_voting_session_weighted_majority():
    engine = VotingEngine()
    session = VotingSession(
        session_id="sess-003",
        strategy=VotingStrategy.WEIGHTED_MAJORITY,
        threshold=0.5,
        min_votes=2,
        max_votes=10,
        agent_weights={"high-trust": 3.0, "low-trust": 1.0},
    )
    await engine.create_voting_session(session)

    # high-trust votes True (weight 3), low-trust votes False (weight 1)
    await engine.cast_vote("sess-003", Vote(agent_id="high-trust", agent_type="optimizer", vote_value=True, confidence=1.0))
    await engine.cast_vote("sess-003", Vote(agent_id="low-trust", agent_type="risk", vote_value=False, confidence=1.0))

    voting_result = await engine.get_voting_result("sess-003")
    assert voting_result is not None
    assert voting_result.passed is True  # 3/(3+1) = 0.75 > 0.5


@pytest.mark.asyncio
async def test_voting_session_insufficient_votes():
    engine = VotingEngine()
    session = VotingSession(
        session_id="sess-004",
        strategy=VotingStrategy.SIMPLE_MAJORITY,
        threshold=0.5,
        min_votes=3,
        max_votes=10,
    )
    await engine.create_voting_session(session)

    await engine.cast_vote("sess-004", Vote(agent_id="a1", agent_type="optimizer", vote_value=True, confidence=1.0))

    voting_result = await engine.get_voting_result("sess-004")
    assert voting_result is not None
    assert voting_result.passed is False
    assert voting_result.metadata.get("error") == "Insufficient votes"


@pytest.mark.asyncio
async def test_voting_session_close_and_cleanup():
    engine = VotingEngine()
    session = VotingSession(
        session_id="sess-005",
        strategy=VotingStrategy.UNANIMOUS,
        threshold=1.0,
        min_votes=2,
        max_votes=5,
    )
    await engine.create_voting_session(session)

    await engine.cast_vote("sess-005", Vote(agent_id="a1", agent_type="optimizer", vote_value=True, confidence=1.0))
    await engine.cast_vote("sess-005", Vote(agent_id="a2", agent_type="compliance", vote_value=True, confidence=1.0))

    result = await engine.get_voting_result("sess-005")
    assert result.passed is True

    await engine.close_voting_session("sess-005")
    assert "sess-005" not in engine.active_sessions
