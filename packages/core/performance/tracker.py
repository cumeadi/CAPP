"""
Performance tracking for financial orchestration

This module provides performance monitoring and tracking capabilities
for the orchestration system.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict, deque
import statistics

import structlog
from pydantic import BaseModel, Field

from packages.core.agents.financial_base import TransactionType


logger = structlog.get_logger(__name__)


class PerformanceMetrics(BaseModel):
    """Performance metrics for transactions"""
    transaction_id: str
    transaction_type: str
    amount: float
    processing_time: float
    success: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PerformanceSummary(BaseModel):
    """Summary of performance metrics"""
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    success_rate: float
    average_processing_time: float
    median_processing_time: float
    min_processing_time: float
    max_processing_time: float
    total_amount_processed: float
    average_amount: float
    throughput_per_minute: float
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PerformanceTracker:
    """
    Performance tracker for monitoring orchestration performance
    
    This class tracks and analyzes performance metrics for financial transactions
    including processing times, success rates, throughput, and amounts.
    """
    
    def __init__(self, enabled: bool = True, sampling_rate: float = 1.0, max_samples: int = 10000):
        self.enabled = enabled
        self.sampling_rate = sampling_rate
        self.max_samples = max_samples
        
        # Storage for metrics
        self._metrics: deque = deque(maxlen=max_samples)
        self._metrics_lock = asyncio.Lock()
        
        # Performance summaries by time window
        self._hourly_summaries: Dict[str, PerformanceSummary] = {}
        self._daily_summaries: Dict[str, PerformanceSummary] = {}
        
        # Real-time counters
        self._current_hour_count = 0
        self._current_day_count = 0
        self._current_hour_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        self._current_day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        self.logger = structlog.get_logger(__name__)
        
        if enabled:
            self.logger.info("Performance tracker initialized", sampling_rate=sampling_rate, max_samples=max_samples)
    
    async def record_transaction_metrics(
        self,
        transaction_id: str,
        transaction_type: str,
        amount: float,
        processing_time: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record metrics for a transaction
        
        Args:
            transaction_id: Unique identifier for the transaction
            transaction_type: Type of transaction
            amount: Transaction amount
            processing_time: Time taken to process (seconds)
            success: Whether the transaction was successful
            metadata: Additional metadata
        """
        if not self.enabled:
            return
        
        # Apply sampling
        if asyncio.get_event_loop().time() % 1.0 > self.sampling_rate:
            return
        
        try:
            metric = PerformanceMetrics(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                amount=amount,
                processing_time=processing_time,
                success=success,
                metadata=metadata or {}
            )
            
            async with self._metrics_lock:
                self._metrics.append(metric)
                await self._update_summaries(metric)
            
            self.logger.debug(
                "Transaction metrics recorded",
                transaction_id=transaction_id,
                processing_time=processing_time,
                success=success
            )
            
        except Exception as e:
            self.logger.error("Failed to record transaction metrics", error=str(e))
    
    async def _update_summaries(self, metric: PerformanceMetrics) -> None:
        """Update performance summaries"""
        try:
            # Update hourly summary
            hour_key = metric.timestamp.strftime("%Y-%m-%d-%H")
            if hour_key not in self._hourly_summaries:
                self._hourly_summaries[hour_key] = PerformanceSummary(
                    total_transactions=0,
                    successful_transactions=0,
                    failed_transactions=0,
                    success_rate=0.0,
                    average_processing_time=0.0,
                    median_processing_time=0.0,
                    min_processing_time=float('inf'),
                    max_processing_time=0.0,
                    total_amount_processed=0.0,
                    average_amount=0.0,
                    throughput_per_minute=0.0
                )
            
            summary = self._hourly_summaries[hour_key]
            summary.total_transactions += 1
            
            if metric.success:
                summary.successful_transactions += 1
            else:
                summary.failed_transactions += 1
            
            summary.success_rate = summary.successful_transactions / summary.total_transactions
            summary.total_amount_processed += metric.amount
            summary.average_amount = summary.total_amount_processed / summary.total_transactions
            
            # Update processing time statistics
            processing_times = [m.processing_time for m in self._get_metrics_for_hour(hour_key)]
            if processing_times:
                summary.average_processing_time = statistics.mean(processing_times)
                summary.median_processing_time = statistics.median(processing_times)
                summary.min_processing_time = min(processing_times)
                summary.max_processing_time = max(processing_times)
            
            # Calculate throughput (transactions per minute)
            hour_start = datetime.strptime(hour_key, "%Y-%m-%d-%H").replace(tzinfo=timezone.utc)
            hour_end = hour_start + timedelta(hours=1)
            hour_metrics = [m for m in self._metrics if hour_start <= m.timestamp < hour_end]
            summary.throughput_per_minute = len(hour_metrics) / 60.0
            
            summary.last_updated = datetime.now(timezone.utc)
            
            # Update daily summary
            day_key = metric.timestamp.strftime("%Y-%m-%d")
            if day_key not in self._daily_summaries:
                self._daily_summaries[day_key] = PerformanceSummary(
                    total_transactions=0,
                    successful_transactions=0,
                    failed_transactions=0,
                    success_rate=0.0,
                    average_processing_time=0.0,
                    median_processing_time=0.0,
                    min_processing_time=float('inf'),
                    max_processing_time=0.0,
                    total_amount_processed=0.0,
                    average_amount=0.0,
                    throughput_per_minute=0.0
                )
            
            daily_summary = self._daily_summaries[day_key]
            daily_summary.total_transactions += 1
            
            if metric.success:
                daily_summary.successful_transactions += 1
            else:
                daily_summary.failed_transactions += 1
            
            daily_summary.success_rate = daily_summary.successful_transactions / daily_summary.total_transactions
            daily_summary.total_amount_processed += metric.amount
            daily_summary.average_amount = daily_summary.total_amount_processed / daily_summary.total_transactions
            
            # Update daily processing time statistics
            daily_processing_times = [m.processing_time for m in self._get_metrics_for_day(day_key)]
            if daily_processing_times:
                daily_summary.average_processing_time = statistics.mean(daily_processing_times)
                daily_summary.median_processing_time = statistics.median(daily_processing_times)
                daily_summary.min_processing_time = min(daily_processing_times)
                daily_summary.max_processing_time = max(daily_processing_times)
            
            # Calculate daily throughput
            day_start = datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            day_end = day_start + timedelta(days=1)
            day_metrics = [m for m in self._metrics if day_start <= m.timestamp < day_end]
            daily_summary.throughput_per_minute = len(day_metrics) / (24 * 60.0)
            
            daily_summary.last_updated = datetime.now(timezone.utc)
            
        except Exception as e:
            self.logger.error("Failed to update performance summaries", error=str(e))
    
    def _get_metrics_for_hour(self, hour_key: str) -> List[PerformanceMetrics]:
        """Get metrics for a specific hour"""
        try:
            hour_start = datetime.strptime(hour_key, "%Y-%m-%d-%H").replace(tzinfo=timezone.utc)
            hour_end = hour_start + timedelta(hours=1)
            return [m for m in self._metrics if hour_start <= m.timestamp < hour_end]
        except Exception as e:
            self.logger.error("Failed to get metrics for hour", error=str(e))
            return []
    
    def _get_metrics_for_day(self, day_key: str) -> List[PerformanceMetrics]:
        """Get metrics for a specific day"""
        try:
            day_start = datetime.strptime(day_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            day_end = day_start + timedelta(days=1)
            return [m for m in self._metrics if day_start <= m.timestamp < day_end]
        except Exception as e:
            self.logger.error("Failed to get metrics for day", error=str(e))
            return []
    
    async def get_metrics(self, time_window: str = "all") -> Dict[str, Any]:
        """
        Get performance metrics
        
        Args:
            time_window: Time window for metrics ("all", "hour", "day", "week")
            
        Returns:
            Dict containing performance metrics
        """
        try:
            if not self.enabled:
                return {"enabled": False}
            
            async with self._metrics_lock:
                if time_window == "all":
                    return await self._get_all_metrics()
                elif time_window == "hour":
                    return await self._get_hourly_metrics()
                elif time_window == "day":
                    return await self._get_daily_metrics()
                elif time_window == "week":
                    return await self._get_weekly_metrics()
                else:
                    raise ValueError(f"Unknown time window: {time_window}")
                    
        except Exception as e:
            self.logger.error("Failed to get metrics", error=str(e))
            return {"error": str(e)}
    
    async def _get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all time"""
        try:
            if not self._metrics:
                return {"total_transactions": 0}
            
            processing_times = [m.processing_time for m in self._metrics]
            amounts = [m.amount for m in self._metrics]
            success_count = sum(1 for m in self._metrics if m.success)
            
            return {
                "total_transactions": len(self._metrics),
                "successful_transactions": success_count,
                "failed_transactions": len(self._metrics) - success_count,
                "success_rate": success_count / len(self._metrics) if self._metrics else 0.0,
                "average_processing_time": statistics.mean(processing_times) if processing_times else 0.0,
                "median_processing_time": statistics.median(processing_times) if processing_times else 0.0,
                "min_processing_time": min(processing_times) if processing_times else 0.0,
                "max_processing_time": max(processing_times) if processing_times else 0.0,
                "total_amount_processed": sum(amounts),
                "average_amount": statistics.mean(amounts) if amounts else 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error("Failed to get all metrics", error=str(e))
            return {"error": str(e)}
    
    async def _get_hourly_metrics(self) -> Dict[str, Any]:
        """Get metrics for the current hour"""
        try:
            current_hour = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
            return {
                "current_hour": self._hourly_summaries.get(current_hour, {}),
                "recent_hours": dict(list(self._hourly_summaries.items())[-24:])  # Last 24 hours
            }
        except Exception as e:
            self.logger.error("Failed to get hourly metrics", error=str(e))
            return {"error": str(e)}
    
    async def _get_daily_metrics(self) -> Dict[str, Any]:
        """Get metrics for the current day"""
        try:
            current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return {
                "current_day": self._daily_summaries.get(current_day, {}),
                "recent_days": dict(list(self._daily_summaries.items())[-7:])  # Last 7 days
            }
        except Exception as e:
            self.logger.error("Failed to get daily metrics", error=str(e))
            return {"error": str(e)}
    
    async def _get_weekly_metrics(self) -> Dict[str, Any]:
        """Get metrics for the current week"""
        try:
            # Get metrics for the last 7 days
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            week_metrics = [m for m in self._metrics if m.timestamp >= week_ago]
            
            if not week_metrics:
                return {"total_transactions": 0}
            
            processing_times = [m.processing_time for m in week_metrics]
            amounts = [m.amount for m in week_metrics]
            success_count = sum(1 for m in week_metrics if m.success)
            
            return {
                "total_transactions": len(week_metrics),
                "successful_transactions": success_count,
                "failed_transactions": len(week_metrics) - success_count,
                "success_rate": success_count / len(week_metrics) if week_metrics else 0.0,
                "average_processing_time": statistics.mean(processing_times) if processing_times else 0.0,
                "median_processing_time": statistics.median(processing_times) if processing_times else 0.0,
                "min_processing_time": min(processing_times) if processing_times else 0.0,
                "max_processing_time": max(processing_times) if processing_times else 0.0,
                "total_amount_processed": sum(amounts),
                "average_amount": statistics.mean(amounts) if amounts else 0.0,
                "throughput_per_day": len(week_metrics) / 7.0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error("Failed to get weekly metrics", error=str(e))
            return {"error": str(e)}
    
    async def get_transaction_type_metrics(self) -> Dict[str, Any]:
        """Get metrics broken down by transaction type"""
        try:
            if not self.enabled or not self._metrics:
                return {}
            
            type_metrics = defaultdict(lambda: {
                "count": 0,
                "success_count": 0,
                "total_amount": 0.0,
                "processing_times": []
            })
            
            for metric in self._metrics:
                type_metrics[metric.transaction_type]["count"] += 1
                type_metrics[metric.transaction_type]["total_amount"] += metric.amount
                type_metrics[metric.transaction_type]["processing_times"].append(metric.processing_time)
                
                if metric.success:
                    type_metrics[metric.transaction_type]["success_count"] += 1
            
            # Calculate statistics for each type
            result = {}
            for tx_type, metrics in type_metrics.items():
                processing_times = metrics["processing_times"]
                result[tx_type] = {
                    "count": metrics["count"],
                    "success_count": metrics["success_count"],
                    "success_rate": metrics["success_count"] / metrics["count"] if metrics["count"] > 0 else 0.0,
                    "total_amount": metrics["total_amount"],
                    "average_amount": metrics["total_amount"] / metrics["count"] if metrics["count"] > 0 else 0.0,
                    "average_processing_time": statistics.mean(processing_times) if processing_times else 0.0,
                    "median_processing_time": statistics.median(processing_times) if processing_times else 0.0,
                    "min_processing_time": min(processing_times) if processing_times else 0.0,
                    "max_processing_time": max(processing_times) if processing_times else 0.0
                }
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to get transaction type metrics", error=str(e))
            return {"error": str(e)}
    
    async def clear_metrics(self) -> None:
        """Clear all stored metrics"""
        try:
            async with self._metrics_lock:
                self._metrics.clear()
                self._hourly_summaries.clear()
                self._daily_summaries.clear()
            
            self.logger.info("Performance metrics cleared")
            
        except Exception as e:
            self.logger.error("Failed to clear metrics", error=str(e))
    
    async def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts based on thresholds"""
        try:
            alerts = []
            
            if not self.enabled or not self._metrics:
                return alerts
            
            # Get recent metrics (last hour)
            hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_metrics = [m for m in self._metrics if m.timestamp >= hour_ago]
            
            if not recent_metrics:
                return alerts
            
            # Check success rate
            success_rate = sum(1 for m in recent_metrics if m.success) / len(recent_metrics)
            if success_rate < 0.95:  # 95% threshold
                alerts.append({
                    "type": "low_success_rate",
                    "severity": "warning",
                    "message": f"Success rate is {success_rate:.2%} (below 95% threshold)",
                    "value": success_rate,
                    "threshold": 0.95
                })
            
            # Check average processing time
            avg_processing_time = statistics.mean([m.processing_time for m in recent_metrics])
            if avg_processing_time > 30.0:  # 30 seconds threshold
                alerts.append({
                    "type": "high_processing_time",
                    "severity": "warning",
                    "message": f"Average processing time is {avg_processing_time:.2f}s (above 30s threshold)",
                    "value": avg_processing_time,
                    "threshold": 30.0
                })
            
            # Check throughput
            throughput_per_minute = len(recent_metrics) / 60.0
            if throughput_per_minute < 1.0:  # 1 transaction per minute threshold
                alerts.append({
                    "type": "low_throughput",
                    "severity": "info",
                    "message": f"Throughput is {throughput_per_minute:.2f} transactions/minute (below 1/min threshold)",
                    "value": throughput_per_minute,
                    "threshold": 1.0
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error("Failed to get performance alerts", error=str(e))
            return [] 