"""
Performance monitor for real-time monitoring and alerting

This module provides real-time performance monitoring and alerting
capabilities for the orchestration system.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
import statistics

import structlog
from pydantic import BaseModel, Field

from packages.core.performance.tracker import PerformanceTracker
from packages.core.performance.metrics import MetricsCollector

logger = structlog.get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class AlertRule(BaseModel):
    """Rule for performance alerts"""
    rule_id: str
    name: str
    description: str
    metric: str
    condition: str  # >, <, >=, <=, ==, !=
    threshold: float
    severity: AlertSeverity
    duration: float = 60.0  # seconds
    enabled: bool = True
    auto_resolve: bool = True
    auto_resolve_threshold: Optional[float] = None
    notification_channels: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Alert(BaseModel):
    """Performance alert"""
    alert_id: str
    rule_id: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    metric_value: float
    threshold: float
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationChannel(BaseModel):
    """Notification channel configuration"""
    channel_id: str
    name: str
    type: str  # email, slack, webhook, etc.
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PerformanceMonitor:
    """
    Performance monitor for real-time monitoring and alerting
    
    This class provides real-time performance monitoring and alerting
    capabilities for the orchestration system.
    """
    
    def __init__(self, 
                 performance_tracker: PerformanceTracker,
                 metrics_collector: MetricsCollector):
        self.performance_tracker = performance_tracker
        self.metrics_collector = metrics_collector
        self.logger = structlog.get_logger(__name__)
        
        # Alert rules and alerts
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Notification channels
        self.notification_channels: Dict[str, NotificationChannel] = {}
        
        # Monitoring task
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Notification handlers
        self.notification_handlers: Dict[str, Callable] = {}
        
        # Initialize default alert rules
        self._initialize_default_rules()
        
        self.logger.info("Performance monitor initialized")
    
    def _initialize_default_rules(self) -> None:
        """Initialize default alert rules"""
        default_rules = [
            AlertRule(
                rule_id="high_latency",
                name="High Processing Latency",
                description="Alert when average processing time exceeds threshold",
                metric="average_processing_time",
                condition=">",
                threshold=10.0,
                severity=AlertSeverity.WARNING,
                duration=300.0,
                auto_resolve=True,
                auto_resolve_threshold=5.0
            ),
            AlertRule(
                rule_id="low_success_rate",
                name="Low Success Rate",
                description="Alert when success rate drops below threshold",
                metric="success_rate",
                condition="<",
                threshold=0.95,
                severity=AlertSeverity.ERROR,
                duration=180.0,
                auto_resolve=True,
                auto_resolve_threshold=0.98
            ),
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate",
                description="Alert when error rate exceeds threshold",
                metric="error_rate",
                condition=">",
                threshold=0.05,
                severity=AlertSeverity.CRITICAL,
                duration=120.0,
                auto_resolve=True,
                auto_resolve_threshold=0.01
            ),
            AlertRule(
                rule_id="low_throughput",
                name="Low Throughput",
                description="Alert when throughput drops below threshold",
                metric="throughput_per_minute",
                condition="<",
                threshold=5.0,
                severity=AlertSeverity.WARNING,
                duration=600.0,
                auto_resolve=True,
                auto_resolve_threshold=10.0
            )
        ]
        
        for rule in default_rules:
            self.add_alert_rule(rule)
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """
        Add an alert rule
        
        Args:
            rule: Alert rule to add
        """
        self.alert_rules[rule.rule_id] = rule
        
        self.logger.info(
            "Alert rule added",
            rule_id=rule.rule_id,
            name=rule.name,
            severity=rule.severity
        )
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """
        Remove an alert rule
        
        Args:
            rule_id: ID of the rule to remove
            
        Returns:
            bool: True if rule was removed
        """
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            self.logger.info("Alert rule removed", rule_id=rule_id)
            return True
        return False
    
    def add_notification_channel(self, channel: NotificationChannel) -> None:
        """
        Add a notification channel
        
        Args:
            channel: Notification channel to add
        """
        self.notification_channels[channel.channel_id] = channel
        
        self.logger.info(
            "Notification channel added",
            channel_id=channel.channel_id,
            name=channel.name,
            type=channel.type
        )
    
    def remove_notification_channel(self, channel_id: str) -> bool:
        """
        Remove a notification channel
        
        Args:
            channel_id: ID of the channel to remove
            
        Returns:
            bool: True if channel was removed
        """
        if channel_id in self.notification_channels:
            del self.notification_channels[channel_id]
            self.logger.info("Notification channel removed", channel_id=channel_id)
            return True
        return False
    
    def register_notification_handler(self, channel_type: str, handler: Callable) -> None:
        """
        Register a notification handler
        
        Args:
            channel_type: Type of notification channel
            handler: Notification handler function
        """
        self.notification_handlers[channel_type] = handler
        
        self.logger.info(
            "Notification handler registered",
            channel_type=channel_type
        )
    
    async def start_monitoring(self, interval: float = 30.0) -> None:
        """
        Start the monitoring process
        
        Args:
            interval: Monitoring check interval in seconds
        """
        if self.monitoring_task is None or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
            
            self.logger.info(
                "Performance monitoring started",
                interval=interval
            )
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring process"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            
            self.logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self, interval: float) -> None:
        """Main monitoring loop"""
        while True:
            try:
                await self._check_alerts()
                await asyncio.sleep(interval)
            except Exception as e:
                self.logger.error(
                    "Error in monitoring loop",
                    error=str(e)
                )
                await asyncio.sleep(10.0)  # Short delay on error
    
    async def _check_alerts(self) -> None:
        """Check all alert rules"""
        # Get current performance metrics
        metrics = await self.performance_tracker.get_metrics()
        
        # Check each alert rule
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue
            
            # Get metric value
            metric_value = self._extract_metric_value(metrics, rule.metric)
            if metric_value is None:
                continue
            
            # Check if alert should be triggered
            should_trigger = self._evaluate_condition(metric_value, rule.condition, rule.threshold)
            
            if should_trigger:
                await self._trigger_alert(rule, metric_value)
            else:
                # Check if alert should be auto-resolved
                if rule.auto_resolve and rule.auto_resolve_threshold is not None:
                    should_resolve = self._evaluate_condition(metric_value, rule.condition, rule.auto_resolve_threshold)
                    if not should_resolve:
                        await self._resolve_alert(rule.rule_id, "Auto-resolved")
    
    def _extract_metric_value(self, metrics: Dict[str, Any], metric_name: str) -> Optional[float]:
        """
        Extract metric value from metrics dictionary
        
        Args:
            metrics: Metrics dictionary
            metric_name: Name of the metric to extract
            
        Returns:
            float: Metric value if found
        """
        # Handle nested metric paths
        if "." in metric_name:
            parts = metric_name.split(".")
            value = metrics
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            return float(value) if value is not None else None
        
        # Direct metric access
        if metric_name in metrics:
            return float(metrics[metric_name])
        
        return None
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """
        Evaluate a condition
        
        Args:
            value: Metric value
            condition: Condition operator
            threshold: Threshold value
            
        Returns:
            bool: True if condition is met
        """
        if condition == ">":
            return value > threshold
        elif condition == "<":
            return value < threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return value == threshold
        elif condition == "!=":
            return value != threshold
        else:
            return False
    
    async def _trigger_alert(self, rule: AlertRule, metric_value: float) -> None:
        """
        Trigger an alert
        
        Args:
            rule: Alert rule that was triggered
            metric_value: Current metric value
        """
        # Check if alert is already active
        if rule.rule_id in self.active_alerts:
            return
        
        # Create alert
        alert = Alert(
            alert_id=f"{rule.rule_id}_{datetime.now(timezone.utc).timestamp()}",
            rule_id=rule.rule_id,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            message=f"{rule.name}: {rule.metric} = {metric_value:.2f} {rule.condition} {rule.threshold}",
            metric_value=metric_value,
            threshold=rule.threshold
        )
        
        # Add to active alerts
        self.active_alerts[rule.rule_id] = alert
        self.alert_history.append(alert)
        
        # Send notifications
        await self._send_notifications(alert, rule)
        
        self.logger.warning(
            "Alert triggered",
            alert_id=alert.alert_id,
            rule_id=rule.rule_id,
            severity=rule.severity,
            metric_value=metric_value,
            threshold=rule.threshold
        )
    
    async def _resolve_alert(self, rule_id: str, reason: str) -> None:
        """
        Resolve an alert
        
        Args:
            rule_id: ID of the rule to resolve
            reason: Reason for resolution
        """
        if rule_id not in self.active_alerts:
            return
        
        alert = self.active_alerts[rule_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        
        # Remove from active alerts
        del self.active_alerts[rule_id]
        
        self.logger.info(
            "Alert resolved",
            alert_id=alert.alert_id,
            rule_id=rule_id,
            reason=reason
        )
    
    async def acknowledge_alert(self, rule_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert
        
        Args:
            rule_id: ID of the rule to acknowledge
            acknowledged_by: User who acknowledged the alert
            
        Returns:
            bool: True if alert was acknowledged
        """
        if rule_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[rule_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by
        
        self.logger.info(
            "Alert acknowledged",
            alert_id=alert.alert_id,
            rule_id=rule_id,
            acknowledged_by=acknowledged_by
        )
        
        return True
    
    async def _send_notifications(self, alert: Alert, rule: AlertRule) -> None:
        """
        Send notifications for an alert
        
        Args:
            alert: Alert to send notifications for
            rule: Alert rule
        """
        for channel_id in rule.notification_channels:
            channel = self.notification_channels.get(channel_id)
            if not channel or not channel.enabled:
                continue
            
            handler = self.notification_handlers.get(channel.type)
            if handler:
                try:
                    await handler(channel, alert, rule)
                except Exception as e:
                    self.logger.error(
                        "Failed to send notification",
                        channel_id=channel_id,
                        channel_type=channel.type,
                        error=str(e)
                    )
    
    async def get_active_alerts(self) -> List[Alert]:
        """
        Get all active alerts
        
        Returns:
            List[Alert]: List of active alerts
        """
        return list(self.active_alerts.values())
    
    async def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """
        Get alert history
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List[Alert]: Alert history
        """
        return self.alert_history[-limit:] if self.alert_history else []
    
    async def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        Get monitoring summary
        
        Returns:
            Dict[str, Any]: Monitoring summary
        """
        total_rules = len(self.alert_rules)
        enabled_rules = len([r for r in self.alert_rules.values() if r.enabled])
        active_alerts = len(self.active_alerts)
        total_alerts = len(self.alert_history)
        
        # Count alerts by severity
        alerts_by_severity = {}
        for alert in self.alert_history:
            severity = alert.severity
            alerts_by_severity[severity] = alerts_by_severity.get(severity, 0) + 1
        
        # Count notification channels
        total_channels = len(self.notification_channels)
        enabled_channels = len([c for c in self.notification_channels.values() if c.enabled])
        
        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "active_alerts": active_alerts,
            "total_alerts": total_alerts,
            "alerts_by_severity": alerts_by_severity,
            "total_channels": total_channels,
            "enabled_channels": enabled_channels,
            "recent_alerts": [
                {
                    "alert_id": alert.alert_id,
                    "rule_id": alert.rule_id,
                    "severity": alert.severity,
                    "status": alert.status,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat()
                }
                for alert in self.alert_history[-10:] if self.alert_history
            ]
        }
    
    async def clear_alert_history(self) -> None:
        """Clear alert history"""
        self.alert_history.clear()
        self.logger.info("Alert history cleared")
    
    async def shutdown(self) -> None:
        """Shutdown the performance monitor"""
        await self.stop_monitoring()
        self.logger.info("Performance monitor shutdown completed")


# Default notification handlers
async def email_notification_handler(channel: NotificationChannel, alert: Alert, rule: AlertRule) -> None:
    """Default email notification handler"""
    # This would send an email notification
    # Implementation would depend on email service integration
    logger.info(
        "Email notification sent",
        channel_id=channel.channel_id,
        alert_id=alert.alert_id,
        severity=alert.severity
    )


async def slack_notification_handler(channel: NotificationChannel, alert: Alert, rule: AlertRule) -> None:
    """Default Slack notification handler"""
    # This would send a Slack notification
    # Implementation would depend on Slack API integration
    logger.info(
        "Slack notification sent",
        channel_id=channel.channel_id,
        alert_id=alert.alert_id,
        severity=alert.severity
    )


async def webhook_notification_handler(channel: NotificationChannel, alert: Alert, rule: AlertRule) -> None:
    """Default webhook notification handler"""
    # This would send a webhook notification
    # Implementation would depend on webhook configuration
    logger.info(
        "Webhook notification sent",
        channel_id=channel.channel_id,
        alert_id=alert.alert_id,
        severity=alert.severity
    )


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(performance_tracker: Optional[PerformanceTracker] = None,
                           metrics_collector: Optional[MetricsCollector] = None) -> Optional[PerformanceMonitor]:
    """
    Get the global performance monitor instance
    
    Args:
        performance_tracker: Performance tracker instance
        metrics_collector: Metrics collector instance
        
    Returns:
        PerformanceMonitor: Global performance monitor instance
    """
    global _performance_monitor
    
    if _performance_monitor is None:
        if not all([performance_tracker, metrics_collector]):
            return None
        
        _performance_monitor = PerformanceMonitor(
            performance_tracker=performance_tracker,
            metrics_collector=metrics_collector
        )
        
        # Register default notification handlers
        _performance_monitor.register_notification_handler("email", email_notification_handler)
        _performance_monitor.register_notification_handler("slack", slack_notification_handler)
        _performance_monitor.register_notification_handler("webhook", webhook_notification_handler)
    
    return _performance_monitor


def set_performance_monitor(monitor: PerformanceMonitor) -> None:
    """
    Set the global performance monitor instance
    
    Args:
        monitor: Performance monitor instance
    """
    global _performance_monitor
    _performance_monitor = monitor
