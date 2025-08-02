"""
Metrics collector for performance monitoring

This module provides comprehensive metrics collection and aggregation
for the orchestration system performance monitoring.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from collections import defaultdict, deque
import statistics
import json

import structlog
from pydantic import BaseModel, Field

from packages.core.performance.tracker import PerformanceMetrics, PerformanceSummary
from packages.core.agents.financial_base import TransactionType

logger = structlog.get_logger(__name__)


class MetricType(str, Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


class MetricDefinition(BaseModel):
    """Definition of a metric"""
    name: str
    type: MetricType
    description: str
    unit: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricValue(BaseModel):
    """Value of a metric"""
    name: str
    value: Union[int, float, str]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricAggregation(BaseModel):
    """Aggregated metric data"""
    name: str
    type: MetricType
    count: int
    sum: float
    min: float
    max: float
    mean: float
    median: float
    std_dev: float
    percentiles: Dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = Field(default_factory=dict)


class MetricsCollectorConfig(BaseModel):
    """Configuration for metrics collector"""
    enabled: bool = True
    collection_interval: float = 60.0  # seconds
    retention_period: float = 86400.0  # 24 hours in seconds
    max_metrics_per_type: int = 10000
    aggregation_enabled: bool = True
    export_enabled: bool = True
    export_format: str = "json"  # json, prometheus, influxdb
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricsCollector:
    """
    Metrics collector for performance monitoring
    
    This class provides comprehensive metrics collection and aggregation
    for monitoring the performance of the orchestration system.
    """
    
    def __init__(self, config: MetricsCollectorConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Metric storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=config.max_metrics_per_type))
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        self.aggregations: Dict[str, MetricAggregation] = {}
        
        # Performance tracking integration
        self.performance_tracker = None
        
        # Export handlers
        self.export_handlers: Dict[str, Callable] = {}
        
        # Collection task
        self.collection_task: Optional[asyncio.Task] = None
        
        if config.enabled:
            self.logger.info("Metrics collector initialized", config=config.dict())
            self._start_collection_task()
    
    def register_metric(self, definition: MetricDefinition) -> None:
        """
        Register a new metric definition
        
        Args:
            definition: Metric definition to register
        """
        self.metric_definitions[definition.name] = definition
        
        self.logger.info(
            "Metric registered",
            name=definition.name,
            type=definition.type,
            description=definition.description
        )
    
    def record_metric(self, name: str, value: Union[int, float, str], 
                     labels: Optional[Dict[str, str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a metric value
        
        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels for the metric
            metadata: Optional metadata
        """
        if not self.config.enabled:
            return
        
        metric_value = MetricValue(
            name=name,
            value=value,
            labels=labels or {},
            metadata=metadata or {}
        )
        
        self.metrics[name].append(metric_value)
        
        self.logger.debug(
            "Metric recorded",
            name=name,
            value=value,
            labels=labels
        )
    
    def increment_counter(self, name: str, value: int = 1,
                         labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric
        
        Args:
            name: Counter name
            value: Increment value (default: 1)
            labels: Optional labels
        """
        self.record_metric(name, value, labels, {"metric_type": "counter"})
    
    def set_gauge(self, name: str, value: float,
                  labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric value
        
        Args:
            name: Gauge name
            value: Gauge value
            labels: Optional labels
        """
        self.record_metric(name, value, labels, {"metric_type": "gauge"})
    
    def record_histogram(self, name: str, value: float,
                        labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record a histogram metric
        
        Args:
            name: Histogram name
            value: Histogram value
            labels: Optional labels
        """
        self.record_metric(name, value, labels, {"metric_type": "histogram"})
    
    def record_timer(self, name: str, duration: float,
                    labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record a timer metric
        
        Args:
            name: Timer name
            duration: Duration in seconds
            labels: Optional labels
        """
        self.record_metric(name, duration, labels, {"metric_type": "timer"})
    
    async def record_transaction_metrics(self, metrics: PerformanceMetrics) -> None:
        """
        Record transaction performance metrics
        
        Args:
            metrics: Performance metrics to record
        """
        if not self.config.enabled:
            return
        
        # Record processing time
        self.record_timer(
            "transaction_processing_time",
            metrics.processing_time,
            {
                "transaction_type": metrics.transaction_type,
                "success": str(metrics.success)
            }
        )
        
        # Record transaction amount
        self.record_histogram(
            "transaction_amount",
            metrics.amount,
            {
                "transaction_type": metrics.transaction_type,
                "success": str(metrics.success)
            }
        )
        
        # Record success/failure
        self.increment_counter(
            "transaction_total",
            labels={"transaction_type": metrics.transaction_type}
        )
        
        if metrics.success:
            self.increment_counter(
                "transaction_success",
                labels={"transaction_type": metrics.transaction_type}
            )
        else:
            self.increment_counter(
                "transaction_failure",
                labels={"transaction_type": metrics.transaction_type}
            )
    
    async def aggregate_metrics(self) -> Dict[str, MetricAggregation]:
        """
        Aggregate collected metrics
        
        Returns:
            Dict[str, MetricAggregation]: Aggregated metrics
        """
        if not self.config.aggregation_enabled:
            return {}
        
        aggregations = {}
        
        for name, values in self.metrics.items():
            if not values:
                continue
            
            # Filter numeric values for aggregation
            numeric_values = []
            for value in values:
                if isinstance(value.value, (int, float)):
                    numeric_values.append(float(value.value))
            
            if not numeric_values:
                continue
            
            # Calculate statistics
            count = len(numeric_values)
            sum_val = sum(numeric_values)
            min_val = min(numeric_values)
            max_val = max(numeric_values)
            mean_val = statistics.mean(numeric_values)
            median_val = statistics.median(numeric_values)
            std_dev = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0
            
            # Calculate percentiles
            percentiles = {}
            for p in [50, 75, 90, 95, 99]:
                try:
                    percentiles[f"p{p}"] = statistics.quantiles(numeric_values, n=100)[p-1]
                except (IndexError, ValueError):
                    percentiles[f"p{p}"] = max_val
            
            # Get metric definition
            definition = self.metric_definitions.get(name, MetricDefinition(
                name=name,
                type=MetricType.GAUGE,
                description=f"Auto-generated metric: {name}"
            ))
            
            aggregation = MetricAggregation(
                name=name,
                type=definition.type,
                count=count,
                sum=sum_val,
                min=min_val,
                max=max_val,
                mean=mean_val,
                median=median_val,
                std_dev=std_dev,
                percentiles=percentiles
            )
            
            aggregations[name] = aggregation
        
        self.aggregations = aggregations
        return aggregations
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics
        
        Returns:
            Dict[str, Any]: Metrics summary
        """
        summary = {
            "total_metrics": len(self.metrics),
            "total_definitions": len(self.metric_definitions),
            "total_aggregations": len(self.aggregations),
            "collection_enabled": self.config.enabled,
            "aggregation_enabled": self.config.aggregation_enabled
        }
        
        # Add metric counts by type
        metric_counts = defaultdict(int)
        for definition in self.metric_definitions.values():
            metric_counts[definition.type] += 1
        
        summary["metrics_by_type"] = dict(metric_counts)
        
        # Add recent aggregations
        if self.aggregations:
            summary["recent_aggregations"] = {
                name: {
                    "count": agg.count,
                    "mean": agg.mean,
                    "min": agg.min,
                    "max": agg.max
                }
                for name, agg in self.aggregations.items()
            }
        
        return summary
    
    async def get_metric_data(self, name: str, 
                             time_window: Optional[timedelta] = None) -> List[MetricValue]:
        """
        Get metric data for a specific metric
        
        Args:
            name: Metric name
            time_window: Optional time window to filter data
            
        Returns:
            List[MetricValue]: Metric data
        """
        if name not in self.metrics:
            return []
        
        values = list(self.metrics[name])
        
        if time_window:
            cutoff_time = datetime.now(timezone.utc) - time_window
            values = [v for v in values if v.timestamp >= cutoff_time]
        
        return values
    
    async def get_metric_aggregation(self, name: str) -> Optional[MetricAggregation]:
        """
        Get aggregation for a specific metric
        
        Args:
            name: Metric name
            
        Returns:
            MetricAggregation: Metric aggregation if available
        """
        return self.aggregations.get(name)
    
    def register_export_handler(self, format_name: str, handler: Callable) -> None:
        """
        Register an export handler
        
        Args:
            format_name: Format name (e.g., 'json', 'prometheus')
            handler: Export handler function
        """
        self.export_handlers[format_name] = handler
        
        self.logger.info(
            "Export handler registered",
            format=format_name
        )
    
    async def export_metrics(self, format_name: str = "json") -> Optional[str]:
        """
        Export metrics in the specified format
        
        Args:
            format_name: Export format
            
        Returns:
            str: Exported metrics data
        """
        if not self.config.export_enabled:
            return None
        
        handler = self.export_handlers.get(format_name)
        if not handler:
            self.logger.warning("No export handler found", format=format_name)
            return None
        
        try:
            # Aggregate metrics first
            await self.aggregate_metrics()
            
            # Export using handler
            result = await handler(self.metrics, self.aggregations, self.metric_definitions)
            
            self.logger.info(
                "Metrics exported",
                format=format_name,
                metrics_count=len(self.metrics)
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Failed to export metrics",
                format=format_name,
                error=str(e)
            )
            return None
    
    async def export_json(self, metrics: Dict, aggregations: Dict, definitions: Dict) -> str:
        """Export metrics as JSON"""
        export_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                name: [value.dict() for value in values]
                for name, values in metrics.items()
            },
            "aggregations": {
                name: agg.dict() for name, agg in aggregations.items()
            },
            "definitions": {
                name: def_.dict() for name, def_ in definitions.items()
            }
        }
        
        return json.dumps(export_data, indent=2, default=str)
    
    async def export_prometheus(self, metrics: Dict, aggregations: Dict, definitions: Dict) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # Add metric definitions as comments
        for name, definition in definitions.items():
            lines.append(f"# HELP {name} {definition.description}")
            lines.append(f"# TYPE {name} {definition.type}")
        
        # Add metric values
        for name, values in metrics.items():
            for value in values:
                labels_str = ""
                if value.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in value.labels.items()]
                    labels_str = "{" + ",".join(label_pairs) + "}"
                
                lines.append(f"{name}{labels_str} {value.value}")
        
        return "\n".join(lines)
    
    def _start_collection_task(self) -> None:
        """Start the periodic collection task"""
        if self.collection_task is None or self.collection_task.done():
            self.collection_task = asyncio.create_task(self._collection_loop())
    
    async def _collection_loop(self) -> None:
        """Periodic collection loop"""
        while self.config.enabled:
            try:
                # Aggregate metrics
                await self.aggregate_metrics()
                
                # Export metrics if enabled
                if self.config.export_enabled:
                    await self.export_metrics(self.config.export_format)
                
                # Clean up old metrics
                await self._cleanup_old_metrics()
                
                # Wait for next collection interval
                await asyncio.sleep(self.config.collection_interval)
                
            except Exception as e:
                self.logger.error(
                    "Error in collection loop",
                    error=str(e)
                )
                await asyncio.sleep(5.0)  # Short delay on error
    
    async def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics based on retention period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.config.retention_period)
        
        for name, values in self.metrics.items():
            # Remove old values
            self.metrics[name] = deque(
                (v for v in values if v.timestamp >= cutoff_time),
                maxlen=self.config.max_metrics_per_type
            )
    
    async def shutdown(self) -> None:
        """Shutdown the metrics collector"""
        self.logger.info("Shutting down metrics collector")
        
        # Stop collection task
        if self.collection_task and not self.collection_task.done():
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        # Final export
        if self.config.export_enabled:
            await self.export_metrics(self.config.export_format)
        
        self.logger.info("Metrics collector shutdown completed")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(config: Optional[MetricsCollectorConfig] = None) -> MetricsCollector:
    """
    Get the global metrics collector instance
    
    Args:
        config: Collector configuration (only used for first initialization)
        
    Returns:
        MetricsCollector: Global metrics collector instance
    """
    global _metrics_collector
    
    if _metrics_collector is None:
        if config is None:
            config = MetricsCollectorConfig()
        _metrics_collector = MetricsCollector(config)
        
        # Register default export handlers
        _metrics_collector.register_export_handler("json", _metrics_collector.export_json)
        _metrics_collector.register_export_handler("prometheus", _metrics_collector.export_prometheus)
    
    return _metrics_collector


def set_metrics_collector(collector: MetricsCollector) -> None:
    """
    Set the global metrics collector instance
    
    Args:
        collector: Metrics collector instance
    """
    global _metrics_collector
    _metrics_collector = collector
