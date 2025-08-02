"""
Metrics Service for CAPP

Collects and aggregates performance metrics across the CAPP system including
payment processing, agent performance, and system health.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone
from decimal import Decimal
import structlog

from .config.settings import get_settings
from .core.redis import get_cache

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """
    Metrics Collector
    
    Collects and aggregates performance metrics for:
    - Payment processing performance
    - Agent performance
    - System health
    - Business metrics
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.logger = structlog.get_logger(__name__)
    
    async def record_payment_metrics(self, payment_id: str, amount: Decimal, processing_time: float, success: bool, corridor: str):
        """Record payment processing metrics"""
        try:
            # Record basic payment metrics
            await self.cache.hincrby("metrics:payments:total", "count", 1)
            await self.cache.hincrby("metrics:payments:total", "volume", int(amount * 100))  # Store as cents
            
            if success:
                await self.cache.hincrby("metrics:payments:successful", "count", 1)
                await self.cache.hincrby("metrics:payments:successful", "volume", int(amount * 100))
            else:
                await self.cache.hincrby("metrics:payments:failed", "count", 1)
                await self.cache.hincrby("metrics:payments:failed", "volume", int(amount * 100))
            
            # Record processing time
            await self.cache.lpush("metrics:processing_times", processing_time)
            await self.cache.ltrim("metrics:processing_times", 0, 999)  # Keep last 1000
            
            # Record corridor metrics
            await self.cache.hincrby(f"metrics:corridors:{corridor}", "count", 1)
            await self.cache.hincrby(f"metrics:corridors:{corridor}", "volume", int(amount * 100))
            
            self.logger.debug("Payment metrics recorded", payment_id=payment_id, amount=amount, processing_time=processing_time)
            
        except Exception as e:
            self.logger.error("Failed to record payment metrics", error=str(e))
    
    async def record_agent_metrics(self, agent_id: str, agent_type: str, processing_time: float, success: bool, payment_amount: str):
        """Record agent performance metrics"""
        try:
            # Record agent performance
            await self.cache.hincrby(f"metrics:agents:{agent_id}", "total_tasks", 1)
            await self.cache.hincrby(f"metrics:agents:{agent_id}", "successful_tasks", 1 if success else 0)
            await self.cache.hincrby(f"metrics:agents:{agent_id}", "failed_tasks", 0 if success else 1)
            
            # Record processing time
            await self.cache.lpush(f"metrics:agents:{agent_id}:processing_times", processing_time)
            await self.cache.ltrim(f"metrics:agents:{agent_id}:processing_times", 0, 99)  # Keep last 100
            
            # Record agent type metrics
            await self.cache.hincrby(f"metrics:agent_types:{agent_type}", "total_tasks", 1)
            await self.cache.hincrby(f"metrics:agent_types:{agent_type}", "successful_tasks", 1 if success else 0)
            
            self.logger.debug("Agent metrics recorded", agent_id=agent_id, agent_type=agent_type, success=success)
            
        except Exception as e:
            self.logger.error("Failed to record agent metrics", error=str(e))
    
    async def record_system_metrics(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record system-level metrics"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            metric_data = {
                "value": value,
                "timestamp": timestamp,
                "tags": tags or {}
            }
            
            await self.cache.lpush(f"metrics:system:{metric_name}", str(metric_data))
            await self.cache.ltrim(f"metrics:system:{metric_name}", 0, 999)  # Keep last 1000
            
            self.logger.debug("System metrics recorded", metric_name=metric_name, value=value)
            
        except Exception as e:
            self.logger.error("Failed to record system metrics", error=str(e))
    
    async def get_payment_metrics(self, time_period: str = "24h") -> Dict:
        """Get payment processing metrics"""
        try:
            # Get total metrics
            total_count = await self.cache.hget("metrics:payments:total", "count") or 0
            total_volume = await self.cache.hget("metrics:payments:total", "volume") or 0
            
            # Get successful metrics
            successful_count = await self.cache.hget("metrics:payments:successful", "count") or 0
            successful_volume = await self.cache.hget("metrics:payments:successful", "volume") or 0
            
            # Get failed metrics
            failed_count = await self.cache.hget("metrics:payments:failed", "count") or 0
            failed_volume = await self.cache.hget("metrics:payments:failed", "volume") or 0
            
            # Calculate success rate
            success_rate = 0.0
            if total_count > 0:
                success_rate = float(successful_count) / float(total_count)
            
            # Get average processing time
            processing_times = await self.cache.lrange("metrics:processing_times", 0, -1)
            avg_processing_time = 0.0
            if processing_times:
                times = [float(t) for t in processing_times]
                avg_processing_time = sum(times) / len(times)
            
            return {
                "total_count": int(total_count),
                "total_volume": float(total_volume) / 100,  # Convert from cents
                "successful_count": int(successful_count),
                "successful_volume": float(successful_volume) / 100,
                "failed_count": int(failed_count),
                "failed_volume": float(failed_volume) / 100,
                "success_rate": success_rate,
                "average_processing_time": avg_processing_time,
                "time_period": time_period
            }
            
        except Exception as e:
            self.logger.error("Failed to get payment metrics", error=str(e))
            return {}
    
    async def get_agent_metrics(self, agent_id: str = None) -> Dict:
        """Get agent performance metrics"""
        try:
            if agent_id:
                # Get specific agent metrics
                total_tasks = await self.cache.hget(f"metrics:agents:{agent_id}", "total_tasks") or 0
                successful_tasks = await self.cache.hget(f"metrics:agents:{agent_id}", "successful_tasks") or 0
                failed_tasks = await self.cache.hget(f"metrics:agents:{agent_id}", "failed_tasks") or 0
                
                # Get processing times
                processing_times = await self.cache.lrange(f"metrics:agents:{agent_id}:processing_times", 0, -1)
                avg_processing_time = 0.0
                if processing_times:
                    times = [float(t) for t in processing_times]
                    avg_processing_time = sum(times) / len(times)
                
                success_rate = 0.0
                if total_tasks > 0:
                    success_rate = float(successful_tasks) / float(total_tasks)
                
                return {
                    "agent_id": agent_id,
                    "total_tasks": int(total_tasks),
                    "successful_tasks": int(successful_tasks),
                    "failed_tasks": int(failed_tasks),
                    "success_rate": success_rate,
                    "average_processing_time": avg_processing_time
                }
            else:
                # Get all agent metrics
                # This would require scanning all agent keys
                return {}
                
        except Exception as e:
            self.logger.error("Failed to get agent metrics", error=str(e))
            return {}
    
    async def get_corridor_metrics(self) -> Dict:
        """Get payment corridor metrics"""
        try:
            # Get all corridor keys
            corridor_keys = await self.cache.keys("metrics:corridors:*")
            
            corridor_metrics = {}
            for key in corridor_keys:
                corridor = key.split(":")[-1]
                count = await self.cache.hget(key, "count") or 0
                volume = await self.cache.hget(key, "volume") or 0
                
                corridor_metrics[corridor] = {
                    "count": int(count),
                    "volume": float(volume) / 100  # Convert from cents
                }
            
            return corridor_metrics
            
        except Exception as e:
            self.logger.error("Failed to get corridor metrics", error=str(e))
            return {}
    
    async def get_system_health_metrics(self) -> Dict:
        """Get system health metrics"""
        try:
            # Get system metrics
            system_metrics = {}
            
            # Get memory usage
            memory_usage = await self.cache.lrange("metrics:system:memory_usage", 0, 0)
            if memory_usage:
                system_metrics["memory_usage"] = float(memory_usage[0])
            
            # Get CPU usage
            cpu_usage = await self.cache.lrange("metrics:system:cpu_usage", 0, 0)
            if cpu_usage:
                system_metrics["cpu_usage"] = float(cpu_usage[0])
            
            # Get active connections
            active_connections = await self.cache.lrange("metrics:system:active_connections", 0, 0)
            if active_connections:
                system_metrics["active_connections"] = int(active_connections[0])
            
            return system_metrics
            
        except Exception as e:
            self.logger.error("Failed to get system health metrics", error=str(e))
            return {}
    
    async def get_business_metrics(self) -> Dict:
        """Get business metrics"""
        try:
            # Get payment metrics
            payment_metrics = await self.get_payment_metrics()
            
            # Get corridor metrics
            corridor_metrics = await self.get_corridor_metrics()
            
            # Calculate total volume by corridor
            total_volume_by_corridor = sum(corridor["volume"] for corridor in corridor_metrics.values())
            
            # Get top corridors
            top_corridors = sorted(
                corridor_metrics.items(),
                key=lambda x: x[1]["volume"],
                reverse=True
            )[:5]
            
            return {
                "total_payments": payment_metrics.get("total_count", 0),
                "total_volume": payment_metrics.get("total_volume", 0),
                "success_rate": payment_metrics.get("success_rate", 0),
                "average_processing_time": payment_metrics.get("average_processing_time", 0),
                "total_volume_by_corridor": total_volume_by_corridor,
                "top_corridors": dict(top_corridors),
                "corridor_count": len(corridor_metrics)
            }
            
        except Exception as e:
            self.logger.error("Failed to get business metrics", error=str(e))
            return {}
    
    async def reset_metrics(self, metric_type: str = None):
        """Reset metrics (for testing or maintenance)"""
        try:
            if metric_type == "payments" or metric_type is None:
                await self.cache.delete("metrics:payments:total")
                await self.cache.delete("metrics:payments:successful")
                await self.cache.delete("metrics:payments:failed")
                await self.cache.delete("metrics:processing_times")
            
            if metric_type == "agents" or metric_type is None:
                agent_keys = await self.cache.keys("metrics:agents:*")
                for key in agent_keys:
                    await self.cache.delete(key)
            
            if metric_type == "corridors" or metric_type is None:
                corridor_keys = await self.cache.keys("metrics:corridors:*")
                for key in corridor_keys:
                    await self.cache.delete(key)
            
            if metric_type == "system" or metric_type is None:
                system_keys = await self.cache.keys("metrics:system:*")
                for key in system_keys:
                    await self.cache.delete(key)
            
            self.logger.info("Metrics reset", metric_type=metric_type)
            
        except Exception as e:
            self.logger.error("Failed to reset metrics", error=str(e)) 