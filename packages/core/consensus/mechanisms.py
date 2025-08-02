"""
Consensus mechanisms for multi-agent decision making

This module provides consensus algorithms for coordinating multiple agents
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


class ConsensusType(str, Enum):
    """Types of consensus mechanisms"""
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    UNANIMOUS = "unanimous"
    THRESHOLD = "threshold"
    MEDIAN = "median"
    AVERAGE = "average"


class ConsensusConfig(BaseModel):
    """Configuration for consensus mechanisms"""
    consensus_type: ConsensusType = ConsensusType.MAJORITY
    threshold: float = 0.7  # 70% agreement required
    timeout: float = 30.0  # seconds
    min_agents: int = 2
    max_agents: int = 10
    
    # Weighted consensus settings
    agent_weights: Dict[str, float] = Field(default_factory=dict)
    
    # Threshold consensus settings
    success_threshold: float = 0.8
    failure_threshold: float = 0.2


class ConsensusResult(BaseModel):
    """Result of consensus mechanism"""
    success: bool
    consensus_reached: bool
    agreement_ratio: float
    selected_result: Optional[ProcessingResult] = None
    all_results: List[ProcessingResult]
    consensus_type: ConsensusType
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConsensusEngine:
    """
    Consensus engine for multi-agent decision making
    
    This class implements various consensus mechanisms to coordinate
    multiple agents processing the same transaction.
    """
    
    def __init__(self, config: ConsensusConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        self.logger.info("Consensus engine initialized", config=config.dict())
    
    async def reach_consensus(self, results: List[ProcessingResult]) -> ProcessingResult:
        """
        Reach consensus among multiple agent results
        
        Args:
            results: List of processing results from different agents
            
        Returns:
            ProcessingResult: The consensus result
        """
        try:
            if not results:
                return ProcessingResult(
                    success=False,
                    transaction_id="unknown",
                    status="failed",
                    message="No results to reach consensus on",
                    error_code="NO_RESULTS"
                )
            
            if len(results) < self.config.min_agents:
                return ProcessingResult(
                    success=False,
                    transaction_id=results[0].transaction_id,
                    status="failed",
                    message=f"Insufficient agents for consensus: {len(results)} < {self.config.min_agents}",
                    error_code="INSUFFICIENT_AGENTS"
                )
            
            # Apply consensus mechanism
            consensus_result = await self._apply_consensus_mechanism(results)
            
            if consensus_result.consensus_reached:
                self.logger.info(
                    "Consensus reached",
                    consensus_type=self.config.consensus_type,
                    agreement_ratio=consensus_result.agreement_ratio,
                    success=consensus_result.success
                )
                return consensus_result.selected_result
            else:
                self.logger.warning(
                    "Consensus not reached",
                    consensus_type=self.config.consensus_type,
                    agreement_ratio=consensus_result.agreement_ratio
                )
                
                # Return the most common result or first successful result
                return self._get_fallback_result(results)
                
        except Exception as e:
            self.logger.error("Consensus mechanism failed", error=str(e))
            return ProcessingResult(
                success=False,
                transaction_id=results[0].transaction_id if results else "unknown",
                status="failed",
                message=f"Consensus mechanism failed: {str(e)}",
                error_code="CONSENSUS_ERROR"
            )
    
    async def _apply_consensus_mechanism(self, results: List[ProcessingResult]) -> ConsensusResult:
        """Apply the configured consensus mechanism"""
        try:
            if self.config.consensus_type == ConsensusType.MAJORITY:
                return await self._majority_consensus(results)
            elif self.config.consensus_type == ConsensusType.WEIGHTED:
                return await self._weighted_consensus(results)
            elif self.config.consensus_type == ConsensusType.UNANIMOUS:
                return await self._unanimous_consensus(results)
            elif self.config.consensus_type == ConsensusType.THRESHOLD:
                return await self._threshold_consensus(results)
            elif self.config.consensus_type == ConsensusType.MEDIAN:
                return await self._median_consensus(results)
            elif self.config.consensus_type == ConsensusType.AVERAGE:
                return await self._average_consensus(results)
            else:
                raise ValueError(f"Unknown consensus type: {self.config.consensus_type}")
                
        except Exception as e:
            self.logger.error("Consensus mechanism application failed", error=str(e))
            raise
    
    async def _majority_consensus(self, results: List[ProcessingResult]) -> ConsensusResult:
        """Majority consensus - most common result wins"""
        try:
            # Count successful vs failed results
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            total_results = len(results)
            success_count = len(successful_results)
            failure_count = len(failed_results)
            
            # Calculate agreement ratio
            if success_count > failure_count:
                agreement_ratio = success_count / total_results
                consensus_reached = agreement_ratio >= self.config.threshold
                selected_result = successful_results[0] if successful_results else results[0]
                success = True
            else:
                agreement_ratio = failure_count / total_results
                consensus_reached = agreement_ratio >= self.config.threshold
                selected_result = failed_results[0] if failed_results else results[0]
                success = False
            
            return ConsensusResult(
                success=success,
                consensus_reached=consensus_reached,
                agreement_ratio=agreement_ratio,
                selected_result=selected_result,
                all_results=results,
                consensus_type=ConsensusType.MAJORITY
            )
            
        except Exception as e:
            self.logger.error("Majority consensus failed", error=str(e))
            raise
    
    async def _weighted_consensus(self, results: List[ProcessingResult]) -> ConsensusResult:
        """Weighted consensus - results weighted by agent importance"""
        try:
            if not self.config.agent_weights:
                # Fall back to majority consensus if no weights defined
                return await self._majority_consensus(results)
            
            # Calculate weighted scores
            success_weight = 0.0
            failure_weight = 0.0
            total_weight = 0.0
            
            for result in results:
                # Get agent weight (default to 1.0 if not specified)
                agent_id = getattr(result, 'agent_id', 'default')
                weight = self.config.agent_weights.get(agent_id, 1.0)
                
                if result.success:
                    success_weight += weight
                else:
                    failure_weight += weight
                
                total_weight += weight
            
            if total_weight == 0:
                return await self._majority_consensus(results)
            
            # Calculate agreement ratio
            if success_weight > failure_weight:
                agreement_ratio = success_weight / total_weight
                consensus_reached = agreement_ratio >= self.config.threshold
                selected_result = next((r for r in results if r.success), results[0])
                success = True
            else:
                agreement_ratio = failure_weight / total_weight
                consensus_reached = agreement_ratio >= self.config.threshold
                selected_result = next((r for r in results if not r.success), results[0])
                success = False
            
            return ConsensusResult(
                success=success,
                consensus_reached=consensus_reached,
                agreement_ratio=agreement_ratio,
                selected_result=selected_result,
                all_results=results,
                consensus_type=ConsensusType.WEIGHTED
            )
            
        except Exception as e:
            self.logger.error("Weighted consensus failed", error=str(e))
            raise
    
    async def _unanimous_consensus(self, results: List[ProcessingResult]) -> ConsensusResult:
        """Unanimous consensus - all agents must agree"""
        try:
            # Check if all results have the same success status
            success_statuses = [r.success for r in results]
            all_success = all(success_statuses)
            all_failure = not any(success_statuses)
            
            if all_success:
                agreement_ratio = 1.0
                consensus_reached = True
                selected_result = results[0]
                success = True
            elif all_failure:
                agreement_ratio = 1.0
                consensus_reached = True
                selected_result = results[0]
                success = False
            else:
                agreement_ratio = 0.0
                consensus_reached = False
                selected_result = results[0]
                success = False
            
            return ConsensusResult(
                success=success,
                consensus_reached=consensus_reached,
                agreement_ratio=agreement_ratio,
                selected_result=selected_result,
                all_results=results,
                consensus_type=ConsensusType.UNANIMOUS
            )
            
        except Exception as e:
            self.logger.error("Unanimous consensus failed", error=str(e))
            raise
    
    async def _threshold_consensus(self, results: List[ProcessingResult]) -> ConsensusResult:
        """Threshold consensus - requires minimum success/failure ratio"""
        try:
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            total_results = len(results)
            success_ratio = len(successful_results) / total_results
            failure_ratio = len(failed_results) / total_results
            
            # Check success threshold
            if success_ratio >= self.config.success_threshold:
                consensus_reached = True
                selected_result = successful_results[0] if successful_results else results[0]
                success = True
                agreement_ratio = success_ratio
            # Check failure threshold
            elif failure_ratio >= self.config.success_threshold:
                consensus_reached = True
                selected_result = failed_results[0] if failed_results else results[0]
                success = False
                agreement_ratio = failure_ratio
            else:
                consensus_reached = False
                selected_result = results[0]
                success = False
                agreement_ratio = max(success_ratio, failure_ratio)
            
            return ConsensusResult(
                success=success,
                consensus_reached=consensus_reached,
                agreement_ratio=agreement_ratio,
                selected_result=selected_result,
                all_results=results,
                consensus_type=ConsensusType.THRESHOLD
            )
            
        except Exception as e:
            self.logger.error("Threshold consensus failed", error=str(e))
            raise
    
    async def _median_consensus(self, results: List[ProcessingResult]) -> ConsensusResult:
        """Median consensus - select the median result based on processing time"""
        try:
            # Sort results by processing time
            sorted_results = sorted(results, key=lambda r: r.processing_time or 0)
            median_index = len(sorted_results) // 2
            selected_result = sorted_results[median_index]
            
            # Calculate agreement ratio based on how close results are to median
            median_time = selected_result.processing_time or 0
            close_results = [
                r for r in results 
                if abs((r.processing_time or 0) - median_time) <= median_time * 0.1
            ]
            agreement_ratio = len(close_results) / len(results)
            consensus_reached = agreement_ratio >= self.config.threshold
            
            return ConsensusResult(
                success=selected_result.success,
                consensus_reached=consensus_reached,
                agreement_ratio=agreement_ratio,
                selected_result=selected_result,
                all_results=results,
                consensus_type=ConsensusType.MEDIAN
            )
            
        except Exception as e:
            self.logger.error("Median consensus failed", error=str(e))
            raise
    
    async def _average_consensus(self, results: List[ProcessingResult]) -> ConsensusResult:
        """Average consensus - combine results based on average metrics"""
        try:
            # Calculate average processing time
            processing_times = [r.processing_time or 0 for r in results]
            avg_processing_time = statistics.mean(processing_times) if processing_times else 0
            
            # Find result closest to average
            closest_result = min(results, key=lambda r: abs((r.processing_time or 0) - avg_processing_time))
            
            # Calculate agreement ratio
            close_results = [
                r for r in results 
                if abs((r.processing_time or 0) - avg_processing_time) <= avg_processing_time * 0.1
            ]
            agreement_ratio = len(close_results) / len(results)
            consensus_reached = agreement_ratio >= self.config.threshold
            
            return ConsensusResult(
                success=closest_result.success,
                consensus_reached=consensus_reached,
                agreement_ratio=agreement_ratio,
                selected_result=closest_result,
                all_results=results,
                consensus_type=ConsensusType.AVERAGE
            )
            
        except Exception as e:
            self.logger.error("Average consensus failed", error=str(e))
            raise
    
    def _get_fallback_result(self, results: List[ProcessingResult]) -> ProcessingResult:
        """Get fallback result when consensus is not reached"""
        try:
            # Try to find a successful result
            successful_results = [r for r in results if r.success]
            if successful_results:
                return successful_results[0]
            
            # Return the first result if no successful results
            return results[0]
            
        except Exception as e:
            self.logger.error("Failed to get fallback result", error=str(e))
            return ProcessingResult(
                success=False,
                transaction_id="unknown",
                status="failed",
                message="Failed to get fallback result",
                error_code="FALLBACK_ERROR"
            )
    
    async def get_consensus_metrics(self) -> Dict[str, Any]:
        """Get consensus engine metrics"""
        try:
            return {
                "consensus_type": self.config.consensus_type,
                "threshold": self.config.threshold,
                "timeout": self.config.timeout,
                "min_agents": self.config.min_agents,
                "max_agents": self.config.max_agents,
                "agent_weights": self.config.agent_weights
            }
        except Exception as e:
            self.logger.error("Failed to get consensus metrics", error=str(e))
            return {} 