"""
Voting mechanisms for consensus decision making

This module provides various voting strategies for coordinating multiple agents
in financial processing workflows.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import statistics

import structlog
from pydantic import BaseModel, Field

from packages.core.agents.base import ProcessingResult

logger = structlog.get_logger(__name__)


class VotingStrategy(str, Enum):
    """Types of voting strategies"""
    SIMPLE_MAJORITY = "simple_majority"
    WEIGHTED_MAJORITY = "weighted_majority"
    UNANIMOUS = "unanimous"
    SUPER_MAJORITY = "super_majority"
    RANKED_CHOICE = "ranked_choice"
    APPROVAL = "approval"


class Vote(BaseModel):
    """Individual vote from an agent"""
    agent_id: str
    agent_type: str
    vote_value: Union[bool, float, str]
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VotingSession(BaseModel):
    """Voting session configuration"""
    session_id: str
    strategy: VotingStrategy
    threshold: float = 0.5
    timeout: float = 30.0
    min_votes: int = 2
    max_votes: int = 10
    agent_weights: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VotingResult(BaseModel):
    """Result of a voting session"""
    session_id: str
    strategy: VotingStrategy
    total_votes: int
    passed: bool
    vote_ratio: float
    winning_vote: Optional[Union[bool, float, str]] = None
    vote_distribution: Dict[str, int] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VotingEngine:
    """
    Voting engine for consensus decision making
    
    This class implements various voting strategies to coordinate
    multiple agents in decision-making processes.
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.active_sessions: Dict[str, VotingSession] = {}
        self.vote_history: Dict[str, List[Vote]] = {}
        
    async def create_voting_session(self, session_config: VotingSession) -> str:
        """
        Create a new voting session
        
        Args:
            session_config: Configuration for the voting session
            
        Returns:
            str: Session ID
        """
        session_id = session_config.session_id
        self.active_sessions[session_id] = session_config
        self.vote_history[session_id] = []
        
        self.logger.info(
            "Voting session created",
            session_id=session_id,
            strategy=session_config.strategy,
            threshold=session_config.threshold
        )
        
        return session_id
    
    async def cast_vote(self, session_id: str, vote: Vote) -> bool:
        """
        Cast a vote in a voting session
        
        Args:
            session_id: ID of the voting session
            vote: Vote to cast
            
        Returns:
            bool: True if vote was accepted
        """
        if session_id not in self.active_sessions:
            self.logger.error("Voting session not found", session_id=session_id)
            return False
            
        session = self.active_sessions[session_id]
        
        # Check if we've reached max votes
        if len(self.vote_history[session_id]) >= session.max_votes:
            self.logger.warning("Max votes reached for session", session_id=session_id)
            return False
            
        # Add vote to history
        self.vote_history[session_id].append(vote)
        
        self.logger.info(
            "Vote cast",
            session_id=session_id,
            agent_id=vote.agent_id,
            vote_value=vote.vote_value,
            confidence=vote.confidence
        )
        
        return True
    
    async def get_voting_result(self, session_id: str) -> Optional[VotingResult]:
        """
        Get the result of a voting session
        
        Args:
            session_id: ID of the voting session
            
        Returns:
            VotingResult: Result of the voting session
        """
        if session_id not in self.active_sessions:
            return None
            
        session = self.active_sessions[session_id]
        votes = self.vote_history[session_id]
        
        if len(votes) < session.min_votes:
            return VotingResult(
                session_id=session_id,
                strategy=session.strategy,
                total_votes=len(votes),
                passed=False,
                vote_ratio=0.0,
                metadata={"error": "Insufficient votes"}
            )
        
        # Apply voting strategy
        result = await self._apply_voting_strategy(session, votes)
        
        return result
    
    async def _apply_voting_strategy(self, session: VotingSession, votes: List[Vote]) -> VotingResult:
        """
        Apply the specified voting strategy
        
        Args:
            session: Voting session configuration
            votes: List of votes cast
            
        Returns:
            VotingResult: Result of applying the strategy
        """
        if session.strategy == VotingStrategy.SIMPLE_MAJORITY:
            return await self._simple_majority_vote(session, votes)
        elif session.strategy == VotingStrategy.WEIGHTED_MAJORITY:
            return await self._weighted_majority_vote(session, votes)
        elif session.strategy == VotingStrategy.UNANIMOUS:
            return await self._unanimous_vote(session, votes)
        elif session.strategy == VotingStrategy.SUPER_MAJORITY:
            return await self._super_majority_vote(session, votes)
        elif session.strategy == VotingStrategy.RANKED_CHOICE:
            return await self._ranked_choice_vote(session, votes)
        elif session.strategy == VotingStrategy.APPROVAL:
            return await self._approval_vote(session, votes)
        else:
            raise ValueError(f"Unknown voting strategy: {session.strategy}")
    
    async def _simple_majority_vote(self, session: VotingSession, votes: List[Vote]) -> VotingResult:
        """Simple majority voting"""
        true_votes = sum(1 for vote in votes if vote.vote_value is True)
        false_votes = sum(1 for vote in votes if vote.vote_value is False)
        
        total_votes = len(votes)
        vote_ratio = true_votes / total_votes if total_votes > 0 else 0.0
        passed = vote_ratio >= session.threshold
        
        return VotingResult(
            session_id=session.session_id,
            strategy=session.strategy,
            total_votes=total_votes,
            passed=passed,
            vote_ratio=vote_ratio,
            winning_vote=passed,
            vote_distribution={"true": true_votes, "false": false_votes}
        )
    
    async def _weighted_majority_vote(self, session: VotingSession, votes: List[Vote]) -> VotingResult:
        """Weighted majority voting"""
        weighted_true = 0.0
        weighted_false = 0.0
        total_weight = 0.0
        
        for vote in votes:
            weight = session.agent_weights.get(vote.agent_id, 1.0) * vote.confidence
            total_weight += weight
            
            if vote.vote_value is True:
                weighted_true += weight
            elif vote.vote_value is False:
                weighted_false += weight
        
        vote_ratio = weighted_true / total_weight if total_weight > 0 else 0.0
        passed = vote_ratio >= session.threshold
        
        return VotingResult(
            session_id=session.session_id,
            strategy=session.strategy,
            total_votes=len(votes),
            passed=passed,
            vote_ratio=vote_ratio,
            winning_vote=passed,
            vote_distribution={"weighted_true": weighted_true, "weighted_false": weighted_false}
        )
    
    async def _unanimous_vote(self, session: VotingSession, votes: List[Vote]) -> VotingResult:
        """Unanimous voting - all votes must be True"""
        all_true = all(vote.vote_value is True for vote in votes)
        vote_ratio = 1.0 if all_true else 0.0
        
        return VotingResult(
            session_id=session.session_id,
            strategy=session.strategy,
            total_votes=len(votes),
            passed=all_true,
            vote_ratio=vote_ratio,
            winning_vote=all_true,
            vote_distribution={"unanimous": len(votes) if all_true else 0}
        )
    
    async def _super_majority_vote(self, session: VotingSession, votes: List[Vote]) -> VotingResult:
        """Super majority voting - requires higher threshold"""
        true_votes = sum(1 for vote in votes if vote.vote_value is True)
        total_votes = len(votes)
        vote_ratio = true_votes / total_votes if total_votes > 0 else 0.0
        
        # Super majority typically requires 2/3 or 3/4 majority
        super_majority_threshold = max(session.threshold, 0.67)
        passed = vote_ratio >= super_majority_threshold
        
        return VotingResult(
            session_id=session.session_id,
            strategy=session.strategy,
            total_votes=total_votes,
            passed=passed,
            vote_ratio=vote_ratio,
            winning_vote=passed,
            vote_distribution={"true": true_votes, "false": total_votes - true_votes}
        )
    
    async def _ranked_choice_vote(self, session: VotingSession, votes: List[Vote]) -> VotingResult:
        """Ranked choice voting"""
        # For simplicity, we'll treat vote_value as a ranking score
        if not all(isinstance(vote.vote_value, (int, float)) for vote in votes):
            raise ValueError("Ranked choice voting requires numeric vote values")
        
        scores = [float(vote.vote_value) for vote in votes]
        avg_score = statistics.mean(scores)
        
        # Pass if average score is above threshold
        passed = avg_score >= session.threshold
        
        return VotingResult(
            session_id=session.session_id,
            strategy=session.strategy,
            total_votes=len(votes),
            passed=passed,
            vote_ratio=avg_score,
            winning_vote=avg_score,
            vote_distribution={"average_score": avg_score, "min_score": min(scores), "max_score": max(scores)}
        )
    
    async def _approval_vote(self, session: VotingSession, votes: List[Vote]) -> VotingResult:
        """Approval voting - multiple options can be approved"""
        # Count approvals for each option
        approval_counts = {}
        
        for vote in votes:
            if isinstance(vote.vote_value, str):
                if vote.vote_value not in approval_counts:
                    approval_counts[vote.vote_value] = 0
                approval_counts[vote.vote_value] += 1
        
        if not approval_counts:
            return VotingResult(
                session_id=session.session_id,
                strategy=session.strategy,
                total_votes=len(votes),
                passed=False,
                vote_ratio=0.0,
                vote_distribution=approval_counts
            )
        
        # Find the option with most approvals
        winning_option = max(approval_counts.items(), key=lambda x: x[1])
        max_approvals = winning_option[1]
        vote_ratio = max_approvals / len(votes)
        passed = vote_ratio >= session.threshold
        
        return VotingResult(
            session_id=session.session_id,
            strategy=session.strategy,
            total_votes=len(votes),
            passed=passed,
            vote_ratio=vote_ratio,
            winning_vote=winning_option[0],
            vote_distribution=approval_counts
        )
    
    async def close_voting_session(self, session_id: str) -> None:
        """
        Close a voting session
        
        Args:
            session_id: ID of the voting session to close
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self.logger.info("Voting session closed", session_id=session_id)
    
    async def get_voting_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about voting activity
        
        Returns:
            Dict[str, Any]: Voting metrics
        """
        total_sessions = len(self.vote_history)
        total_votes = sum(len(votes) for votes in self.vote_history.values())
        
        strategy_counts = {}
        for session in self.active_sessions.values():
            strategy = session.strategy
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": len(self.active_sessions),
            "total_votes": total_votes,
            "strategy_distribution": strategy_counts,
            "average_votes_per_session": total_votes / total_sessions if total_sessions > 0 else 0
        }
