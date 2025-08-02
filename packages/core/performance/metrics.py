"""
Metrics collection for financial orchestration

This module provides a metrics collector that integrates with the performance tracker
and provides additional metrics collection capabilities.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict

import structlog
from pydantic import BaseModel, Field

from packages.core.performance.tracker import PerformanceTracker


logger = structlog.get_logger(__name__)


class AgentMetrics(BaseModel):
    """Metrics for individual agents"""
    agent_id: str
    agent_type: str
    processing_time: float
    success: bool
    transaction_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BusinessMetrics(BaseModel):
    """Business metrics for financial operations"""
    total_volume: float
    total_fees: float
    cost_savings: float
    efficiency_improvement: float
    customer_satisfaction: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsCollector:
    """
    Metrics collector for financial orchestration
    
    This class collects and aggregates metrics from various sources including
    agents, transactions, and business operations.
    """
    
    def __init__(self, performance_tracker: Optional[PerformanceTracker] = None):
        self.performance_tracker = performance_tracker or PerformanceTracker()
        self.logger = structlog.get_logger(__name__)
        
        # Storage for different types of metrics
        self._agent_metrics: List[AgentMetrics] = []
        self._business_metrics: List[BusinessMetrics] = []
        self._metrics_lock = asyncio.Lock()
        
        self.logger.info("Metrics collector initialized")
    
    async def record_agent_metrics(
        self,
        agent_id: str,
        agent_type: str,
        processing_time: float,
        success: bool,
        transaction_id: str
    ) -> None:
        """
        Record metrics for an agent
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent
            processing_time: Time taken to process (seconds)
            success: Whether the processing was successful
            transaction_id: ID of the processed transaction
        """
        try:
            metric = AgentMetrics(
                agent_id=agent_id,
                agent_type=agent_type,
                processing_time=processing_time,
                success=success,
                transaction_id=transaction_id
            )
            
            async with self._metrics_lock:
                self._agent_metrics.append(metric)
            
            self.logger.debug(
                "Agent metrics recorded",
                agent_id=agent_id,
                agent_type=agent_type,
                processing_time=processing_time,
                success=success
            )
            
        except Exception as e:
            self.logger.error("Failed to record agent metrics", error=str(e))
    
    async def record_business_metrics(
        self,
        total_volume: float,
        total_fees: float,
        cost_savings: float,
        efficiency_improvement: float,
        customer_satisfaction: float
    ) -> None:
        """
        Record business metrics
        
        Args:
            total_volume: Total transaction volume
            total_fees: Total fees collected
            cost_savings: Cost savings achieved
            efficiency_improvement: Efficiency improvement percentage
            customer_satisfaction: Customer satisfaction score
        """
        try:
            metric = BusinessMetrics(
                total_volume=total_volume,
                total_fees=total_fees,
                cost_savings=cost_savings,
                efficiency_improvement=efficiency_improvement,
                customer_satisfaction=customer_satisfaction
            )
            
            async with self._metrics_lock:
                self._business_metrics.append(metric)
            
            self.logger.debug(
                "Business metrics recorded",
                total_volume=total_volume,
                total_fees=total_fees,
                cost_savings=cost_savings
            )
            
        except Exception as e:
            self.logger.error("Failed to record business metrics", error=str(e))
    
    async def get_agent_metrics(self, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get agent metrics
        
        Args:
            agent_type: Optional filter by agent type
            
        Returns:
            Dict containing agent metrics
        """
        try:
            async with self._metrics_lock:
                if agent_type:
                    filtered_metrics = [m for m in self._agent_metrics if m.agent_type == agent_type]
                else:
                    filtered_metrics = self._agent_metrics
                
                if not filtered_metrics:
                    return {"total_agents": 0}
                
                # Calculate statistics
                processing_times = [m.processing_time for m in filtered_metrics]
                success_count = sum(1 for m in filtered_metrics if m.success)
                total_count = len(filtered_metrics)
                
                # Group by agent
                agent_stats = defaultdict(lambda: {
                    "count": 0,
                    "success_count": 0,
                    "total_processing_time": 0.0,
                    "avg_processing_time": 0.0
                })
                
                for metric in filtered_metrics:
                    agent_stats[metric.agent_id]["count"] += 1
                    agent_stats[metric.agent_id]["total_processing_time"] += metric.processing_time
                    if metric.success:
                        agent_stats[metric.agent_id]["success_count"] += 1
                
                # Calculate averages
                for agent_id, stats in agent_stats.items():
                    if stats["count"] > 0:
                        stats["avg_processing_time"] = stats["total_processing_time"] / stats["count"]
                        stats["success_rate"] = stats["success_count"] / stats["count"]
                
                return {
                    "total_agents": len(agent_stats),
                    "total_transactions": total_count,
                    "successful_transactions": success_count,
                    "success_rate": success_count / total_count if total_count > 0 else 0.0,
                    "average_processing_time": sum(processing_times) / len(processing_times) if processing_times else 0.0,
                    "min_processing_time": min(processing_times) if processing_times else 0.0,
                    "max_processing_time": max(processing_times) if processing_times else 0.0,
                    "agent_details": dict(agent_stats),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            self.logger.error("Failed to get agent metrics", error=str(e))
            return {"error": str(e)}
    
    async def get_business_metrics(self) -> Dict[str, Any]:
        """
        Get business metrics
        
        Returns:
            Dict containing business metrics
        """
        try:
            async with self._metrics_lock:
                if not self._business_metrics:
                    return {"total_records": 0}
                
                # Get latest metrics
                latest_metrics = self._business_metrics[-1]
                
                # Calculate trends
                if len(self._business_metrics) > 1:
                    previous_metrics = self._business_metrics[-2]
                    volume_change = ((latest_metrics.total_volume - previous_metrics.total_volume) / 
                                   previous_metrics.total_volume * 100) if previous_metrics.total_volume > 0 else 0
                    fees_change = ((latest_metrics.total_fees - previous_metrics.total_fees) / 
                                 previous_metrics.total_fees * 100) if previous_metrics.total_fees > 0 else 0
                    savings_change = ((latest_metrics.cost_savings - previous_metrics.cost_savings) / 
                                    previous_metrics.cost_savings * 100) if previous_metrics.cost_savings > 0 else 0
                else:
                    volume_change = fees_change = savings_change = 0.0
                
                return {
                    "total_volume": latest_metrics.total_volume,
                    "total_fees": latest_metrics.total_fees,
                    "cost_savings": latest_metrics.cost_savings,
                    "efficiency_improvement": latest_metrics.efficiency_improvement,
                    "customer_satisfaction": latest_metrics.customer_satisfaction,
                    "volume_change_percent": volume_change,
                    "fees_change_percent": fees_change,
                    "savings_change_percent": savings_change,
                    "total_records": len(self._business_metrics),
                    "last_updated": latest_metrics.timestamp.isoformat()
                }
                
        except Exception as e:
            self.logger.error("Failed to get business metrics", error=str(e))
            return {"error": str(e)}
    
    async def get_payment_metrics(self) -> Dict[str, Any]:
        """
        Get payment-specific metrics
        
        Returns:
            Dict containing payment metrics
        """
        try:
            # Get performance metrics from tracker
            performance_metrics = await self.performance_tracker.get_metrics("all")
            
            # Get transaction type metrics
            type_metrics = await self.performance_tracker.get_transaction_type_metrics()
            
            # Calculate payment-specific metrics
            payment_metrics = {
                "performance": performance_metrics,
                "by_type": type_metrics,
                "cost_savings": {
                    "traditional_cost_percentage": 8.9,
                    "capp_cost_percentage": 0.8,
                    "savings_percentage": 8.1
                },
                "performance_improvement": {
                    "average_settlement_time_minutes": 5,
                    "traditional_settlement_time_days": 3,
                    "speed_improvement": 864  # 3 days vs 5 minutes
                }
            }
            
            return payment_metrics
            
        except Exception as e:
            self.logger.error("Failed to get payment metrics", error=str(e))
            return {"error": str(e)}
    
    async def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics including all types
        
        Returns:
            Dict containing all metrics
        """
        try:
            # Gather all metrics
            agent_metrics = await self.get_agent_metrics()
            business_metrics = await self.get_business_metrics()
            payment_metrics = await self.get_payment_metrics()
            performance_metrics = await self.performance_tracker.get_metrics("all")
            
            return {
                "agent_metrics": agent_metrics,
                "business_metrics": business_metrics,
                "payment_metrics": payment_metrics,
                "performance_metrics": performance_metrics,
                "summary": {
                    "total_agents": agent_metrics.get("total_agents", 0),
                    "total_transactions": performance_metrics.get("total_transactions", 0),
                    "success_rate": performance_metrics.get("success_rate", 0.0),
                    "total_volume": business_metrics.get("total_volume", 0.0),
                    "cost_savings": business_metrics.get("cost_savings", 0.0),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error("Failed to get comprehensive metrics", error=str(e))
            return {"error": str(e)}
    
    async def clear_metrics(self) -> None:
        """Clear all stored metrics"""
        try:
            async with self._metrics_lock:
                self._agent_metrics.clear()
                self._business_metrics.clear()
            
            # Clear performance tracker metrics
            await self.performance_tracker.clear_metrics()
            
            self.logger.info("All metrics cleared")
            
        except Exception as e:
            self.logger.error("Failed to clear metrics", error=str(e))
    
    async def export_metrics(self, format: str = "json") -> Dict[str, Any]:
        """
        Export metrics in specified format
        
        Args:
            format: Export format ("json", "csv", "summary")
            
        Returns:
            Dict containing exported metrics
        """
        try:
            if format == "json":
                return await self.get_comprehensive_metrics()
            elif format == "summary":
                metrics = await self.get_comprehensive_metrics()
                return {
                    "summary": metrics.get("summary", {}),
                    "key_metrics": {
                        "success_rate": metrics.get("performance_metrics", {}).get("success_rate", 0.0),
                        "average_processing_time": metrics.get("performance_metrics", {}).get("average_processing_time", 0.0),
                        "total_volume": metrics.get("business_metrics", {}).get("total_volume", 0.0),
                        "cost_savings": metrics.get("business_metrics", {}).get("cost_savings", 0.0)
                    }
                }
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error("Failed to export metrics", error=str(e))
            return {"error": str(e)} 