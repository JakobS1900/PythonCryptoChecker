"""
Real-time monitoring and alerting system for platform health.
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from logger import logger
from database.unified_models import User, GameSession


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """System alert."""
    id: str
    level: AlertLevel
    title: str
    message: str
    metric: str
    value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False


class MetricCollector:
    """Collects various system and application metrics."""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system resource metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # Network metrics (if available)
            network_io = psutil.net_io_counters()
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "core_count": cpu_count,
                    "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                },
                "memory": {
                    "usage_percent": memory_percent,
                    "used_gb": round(memory_used_gb, 2),
                    "total_gb": round(memory_total_gb, 2),
                    "available_gb": round(memory.available / (1024**3), 2)
                },
                "disk": {
                    "usage_percent": disk_percent,
                    "used_gb": round(disk_used_gb, 2),
                    "total_gb": round(disk_total_gb, 2),
                    "free_gb": round(disk.free / (1024**3), 2)
                },
                "network": {
                    "bytes_sent": network_io.bytes_sent,
                    "bytes_recv": network_io.bytes_recv,
                    "packets_sent": network_io.packets_sent,
                    "packets_recv": network_io.packets_recv
                },
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    async def collect_application_metrics(self, session: AsyncSession) -> Dict[str, Any]:
        """Collect application-specific metrics."""
        try:
            now = datetime.utcnow()
            last_hour = now - timedelta(hours=1)
            last_5min = now - timedelta(minutes=5)
            
            # User activity metrics
            active_users_result = await session.execute(
                select(func.count(func.distinct(User.id))).where(
                    User.last_login >= last_hour
                )
            )
            active_users_hour = active_users_result.scalar() or 0
            
            recent_users_result = await session.execute(
                select(func.count(func.distinct(User.id))).where(
                    User.last_login >= last_5min
                )
            )
            active_users_5min = recent_users_result.scalar() or 0
            
            # Gaming activity metrics
            games_hour_result = await session.execute(
                select(func.count(GameSession.id)).where(
                    GameSession.created_at >= last_hour
                )
            )
            games_last_hour = games_hour_result.scalar() or 0
            
            games_5min_result = await session.execute(
                select(func.count(GameSession.id)).where(
                    GameSession.created_at >= last_5min
                )
            )
            games_last_5min = games_5min_result.scalar() or 0
            
            # Error rate (would need error logging in production)
            error_rate = 0.0  # Placeholder
            
            # Response time (would need request tracking in production)
            avg_response_time = 150.0  # milliseconds
            
            return {
                "users": {
                    "active_last_hour": active_users_hour,
                    "active_last_5min": active_users_5min,
                    "activity_rate": games_last_hour / max(active_users_hour, 1)
                },
                "gaming": {
                    "games_last_hour": games_last_hour,
                    "games_last_5min": games_last_5min,
                    "games_per_minute": games_last_5min / 5.0
                },
                "performance": {
                    "error_rate_percent": error_rate,
                    "avg_response_time_ms": avg_response_time
                },
                "health": {
                    "database_connected": True,  # Would check actual DB connection
                    "cache_healthy": True,       # Would check cache if implemented
                    "api_responsive": True       # Would check API health
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")
            return {}


class AlertManager:
    """Manages system alerts and notifications."""
    
    def __init__(self):
        self.alerts = {}
        self.alert_handlers = {}
        self.thresholds = {
            "cpu_usage": {"warning": 70.0, "critical": 90.0},
            "memory_usage": {"warning": 80.0, "critical": 95.0},
            "disk_usage": {"warning": 85.0, "critical": 95.0},
            "error_rate": {"warning": 1.0, "critical": 5.0},
            "response_time": {"warning": 500.0, "critical": 2000.0},
            "active_users_drop": {"warning": 50.0, "critical": 80.0}
        }
    
    def add_alert_handler(self, alert_type: str, handler: Callable):
        """Add a handler for specific alert types."""
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)
    
    async def check_thresholds(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check metrics against thresholds and generate alerts."""
        new_alerts = []
        
        try:
            # Check system metrics
            system_metrics = metrics.get("system", {})
            
            # CPU usage
            cpu_usage = system_metrics.get("cpu", {}).get("usage_percent", 0)
            cpu_alert = self._check_threshold("cpu_usage", cpu_usage)
            if cpu_alert:
                new_alerts.append(cpu_alert)
            
            # Memory usage
            memory_usage = system_metrics.get("memory", {}).get("usage_percent", 0)
            memory_alert = self._check_threshold("memory_usage", memory_usage)
            if memory_alert:
                new_alerts.append(memory_alert)
            
            # Disk usage
            disk_usage = system_metrics.get("disk", {}).get("usage_percent", 0)
            disk_alert = self._check_threshold("disk_usage", disk_usage)
            if disk_alert:
                new_alerts.append(disk_alert)
            
            # Check application metrics
            app_metrics = metrics.get("application", {})
            
            # Error rate
            error_rate = app_metrics.get("performance", {}).get("error_rate_percent", 0)
            error_alert = self._check_threshold("error_rate", error_rate)
            if error_alert:
                new_alerts.append(error_alert)
            
            # Response time
            response_time = app_metrics.get("performance", {}).get("avg_response_time_ms", 0)
            response_alert = self._check_threshold("response_time", response_time)
            if response_alert:
                new_alerts.append(response_alert)
            
            # Store new alerts
            for alert in new_alerts:
                self.alerts[alert.id] = alert
                await self._notify_alert(alert)
            
            return new_alerts
            
        except Exception as e:
            logger.error(f"Failed to check thresholds: {e}")
            return []
    
    def _check_threshold(self, metric: str, value: float) -> Optional[Alert]:
        """Check if a metric value breaches thresholds."""
        try:
            thresholds = self.thresholds.get(metric, {})
            alert_id = f"{metric}_{int(time.time())}"
            
            if value >= thresholds.get("critical", float('inf')):
                return Alert(
                    id=alert_id,
                    level=AlertLevel.CRITICAL,
                    title=f"Critical {metric.replace('_', ' ').title()}",
                    message=f"{metric} is at {value:.1f}%, exceeding critical threshold",
                    metric=metric,
                    value=value,
                    threshold=thresholds["critical"],
                    timestamp=datetime.utcnow()
                )
            elif value >= thresholds.get("warning", float('inf')):
                return Alert(
                    id=alert_id,
                    level=AlertLevel.WARNING,
                    title=f"High {metric.replace('_', ' ').title()}",
                    message=f"{metric} is at {value:.1f}%, exceeding warning threshold",
                    metric=metric,
                    value=value,
                    threshold=thresholds["warning"],
                    timestamp=datetime.utcnow()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check threshold for {metric}: {e}")
            return None
    
    async def _notify_alert(self, alert: Alert):
        """Send alert notifications."""
        try:
            logger.warning(f"ALERT [{alert.level.value.upper()}]: {alert.title} - {alert.message}")
            
            # Call registered handlers
            handlers = self.alert_handlers.get(alert.metric, [])
            for handler in handlers:
                try:
                    await handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to notify alert: {e}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self.alerts.values() if not alert.resolved]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        try:
            if alert_id in self.alerts:
                self.alerts[alert_id].resolved = True
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False


class MonitoringSystem:
    """Main monitoring system coordinator."""
    
    def __init__(self):
        self.metric_collector = MetricCollector()
        self.alert_manager = AlertManager()
        self.monitoring_active = False
        self.monitoring_interval = 30  # seconds
        self.metrics_history = []
        self.max_history = 1440  # 24 hours of 1-minute intervals
    
    async def start_monitoring(self, session: AsyncSession):
        """Start the monitoring system."""
        try:
            self.monitoring_active = True
            logger.info("Monitoring system started")
            
            while self.monitoring_active:
                await self._collect_and_process_metrics(session)
                await asyncio.sleep(self.monitoring_interval)
                
        except Exception as e:
            logger.error(f"Monitoring system error: {e}")
        finally:
            logger.info("Monitoring system stopped")
    
    async def stop_monitoring(self):
        """Stop the monitoring system."""
        self.monitoring_active = False
    
    async def _collect_and_process_metrics(self, session: AsyncSession):
        """Collect metrics and process alerts."""
        try:
            # Collect metrics
            system_metrics = await self.metric_collector.collect_system_metrics()
            app_metrics = await self.metric_collector.collect_application_metrics(session)
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "system": system_metrics,
                "application": app_metrics
            }
            
            # Store metrics history
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
            
            # Check for alerts
            await self.alert_manager.check_thresholds(metrics)
            
        except Exception as e:
            logger.error(f"Failed to collect and process metrics: {e}")
    
    async def get_current_status(self) -> Dict[str, Any]:
        """Get current system status."""
        try:
            if not self.metrics_history:
                return {"status": "no_data", "message": "No metrics available"}
            
            latest_metrics = self.metrics_history[-1]
            active_alerts = self.alert_manager.get_active_alerts()
            
            # Determine overall health
            critical_alerts = [a for a in active_alerts if a.level == AlertLevel.CRITICAL]
            warning_alerts = [a for a in active_alerts if a.level == AlertLevel.WARNING]
            
            if critical_alerts:
                overall_status = "critical"
            elif warning_alerts:
                overall_status = "warning"
            else:
                overall_status = "healthy"
            
            return {
                "status": overall_status,
                "timestamp": latest_metrics["timestamp"],
                "metrics": latest_metrics,
                "alerts": {
                    "total": len(active_alerts),
                    "critical": len(critical_alerts),
                    "warning": len(warning_alerts),
                    "active_alerts": [
                        {
                            "id": alert.id,
                            "level": alert.level.value,
                            "title": alert.title,
                            "message": alert.message,
                            "timestamp": alert.timestamp.isoformat()
                        }
                        for alert in active_alerts[:10]  # Latest 10 alerts
                    ]
                },
                "uptime": latest_metrics["system"].get("uptime_seconds", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get current status: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for specified hours."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            filtered_metrics = []
            for metrics in self.metrics_history:
                metrics_time = datetime.fromisoformat(metrics["timestamp"])
                if metrics_time >= cutoff_time:
                    filtered_metrics.append(metrics)
            
            return filtered_metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []
    
    def set_alert_threshold(self, metric: str, warning: float = None, critical: float = None):
        """Update alert thresholds."""
        try:
            if metric not in self.alert_manager.thresholds:
                self.alert_manager.thresholds[metric] = {}
            
            if warning is not None:
                self.alert_manager.thresholds[metric]["warning"] = warning
            if critical is not None:
                self.alert_manager.thresholds[metric]["critical"] = critical
                
            logger.info(f"Updated thresholds for {metric}: warning={warning}, critical={critical}")
            
        except Exception as e:
            logger.error(f"Failed to set alert threshold: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a quick health check."""
        try:
            status = await self.get_current_status()
            
            return {
                "healthy": status["status"] in ["healthy", "warning"],
                "status": status["status"],
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {
                    "monitoring_active": self.monitoring_active,
                    "metrics_available": len(self.metrics_history) > 0,
                    "no_critical_alerts": status["alerts"]["critical"] == 0
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global instance
monitoring_system = MonitoringSystem()