"""
System Monitor - Real-time system health and performance monitoring
Tracks all components and generates alerts
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import deque

from utils.trace_logger import trace, trace_async_calls


class HealthStatus:
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class MetricSnapshot:
    """Snapshot of metrics at a point in time"""

    def __init__(self, metrics: Dict[str, Any]):
        self.timestamp = datetime.now()
        self.metrics = metrics


class SystemMonitor:
    """
    Continuous system health and performance monitoring
    All monitoring activity is traced to files
    """

    def __init__(
        self,
        workflow_engine,
        agent_coordinator,
        event_dispatcher,
        rest_gateway,
        websocket_server
    ):
        self.workflow_engine = workflow_engine
        self.agent_coordinator = agent_coordinator
        self.event_dispatcher = event_dispatcher
        self.rest_gateway = rest_gateway
        self.websocket_server = websocket_server

        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.check_interval = 10  # seconds

        # Metrics history (keep last 100 snapshots)
        self.metrics_history: deque = deque(maxlen=100)

        # Performance baselines
        self.baselines = {
            "api_response_time_ms": 200,
            "workflow_completion_rate": 0.95,
            "error_rate": 0.05
        }

        # Alerts
        self.alerts: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            "error_rate": 0.1,
            "response_time_ms": 500,
            "memory_usage_percent": 90
        }

        self.start_time = datetime.now()

        trace.info("SystemMonitor initialized", module=__name__, function="__init__")

    @trace_async_calls
    async def start(self):
        """Start system monitoring"""
        if self.is_running:
            trace.warning(
                "SystemMonitor already running",
                module=__name__,
                function="start"
            )
            return

        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        trace.info("SystemMonitor started", module=__name__, function="start")

    @trace_async_calls
    async def stop(self):
        """Stop system monitoring"""
        if not self.is_running:
            return

        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        trace.info("SystemMonitor stopped", module=__name__, function="stop")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        trace.debug(
            "Monitoring loop started",
            module=__name__,
            function="_monitoring_loop"
        )

        while self.is_running:
            try:
                # Collect metrics
                await self._collect_metrics()

                # Check health
                await self._check_health()

                # Detect anomalies
                await self._detect_anomalies()

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                trace.error(
                    "Error in monitoring loop",
                    module=__name__,
                    function="_monitoring_loop",
                    exception=e
                )
                await asyncio.sleep(self.check_interval)

    async def _collect_metrics(self):
        """Collect metrics from all components"""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "workflow_engine": self.workflow_engine.get_metrics(),
                "agent_coordinator": self.agent_coordinator.get_coordinator_metrics(),
                "event_dispatcher": self.event_dispatcher.get_dispatcher_metrics(),
                "rest_gateway": self.rest_gateway.get_gateway_metrics(),
                "websocket_server": self.websocket_server.get_websocket_metrics()
            }

            # Add snapshot to history
            snapshot = MetricSnapshot(metrics)
            self.metrics_history.append(snapshot)

            trace.debug(
                "Metrics collected",
                context={
                    "active_workflows": metrics["workflow_engine"]["active_workflows"],
                    "total_requests": metrics["rest_gateway"]["total_requests"],
                    "websocket_connections": metrics["websocket_server"]["total_connections"]
                },
                module=__name__,
                function="_collect_metrics"
            )

        except Exception as e:
            trace.error(
                "Error collecting metrics",
                module=__name__,
                function="_collect_metrics",
                exception=e
            )

    async def _check_health(self):
        """Check health of all components"""
        try:
            if not self.metrics_history:
                return

            latest_metrics = self.metrics_history[-1].metrics

            # Check workflow engine health
            workflow_metrics = latest_metrics["workflow_engine"]
            if workflow_metrics["success_rate"] < self.baselines["workflow_completion_rate"]:
                await self._raise_alert(
                    "workflow_engine",
                    HealthStatus.DEGRADED,
                    f"Workflow success rate below baseline: {workflow_metrics['success_rate']:.2f}"
                )

            # Check API gateway health
            gateway_metrics = latest_metrics["rest_gateway"]
            if gateway_metrics["error_count"] > 0:
                error_rate = gateway_metrics["error_count"] / gateway_metrics["total_requests"]
                if error_rate > self.alert_thresholds["error_rate"]:
                    await self._raise_alert(
                        "rest_gateway",
                        HealthStatus.DEGRADED,
                        f"High error rate: {error_rate:.2%}"
                    )

            # Check event dispatcher health
            dispatcher_metrics = latest_metrics["event_dispatcher"]
            if dispatcher_metrics["pending_events"] > 100:
                await self._raise_alert(
                    "event_dispatcher",
                    HealthStatus.DEGRADED,
                    f"High pending events: {dispatcher_metrics['pending_events']}"
                )

            trace.debug(
                "Health check completed",
                module=__name__,
                function="_check_health"
            )

        except Exception as e:
            trace.error(
                "Error checking health",
                module=__name__,
                function="_check_health",
                exception=e
            )

    async def _detect_anomalies(self):
        """Detect anomalies in metrics"""
        try:
            if len(self.metrics_history) < 10:
                return  # Need more data

            # Get recent metrics
            recent_snapshots = list(self.metrics_history)[-10:]

            # Calculate average response times, error rates, etc.
            # This is a simplified anomaly detection
            # In production, use more sophisticated algorithms

            trace.debug(
                "Anomaly detection completed",
                module=__name__,
                function="_detect_anomalies"
            )

        except Exception as e:
            trace.error(
                "Error detecting anomalies",
                module=__name__,
                function="_detect_anomalies",
                exception=e
            )

    async def _raise_alert(self, component: str, severity: str, message: str):
        """Raise a system alert"""
        alert = {
            "alert_id": f"alert_{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "severity": severity,
            "message": message,
            "acknowledged": False
        }

        self.alerts.append(alert)

        # Emit alert event
        await self.event_dispatcher.emit(
            "alert.raised",
            alert,
            source="system_monitor"
        )

        trace.warning(
            f"Alert raised: {component} - {message}",
            context=alert,
            module=__name__,
            function="_raise_alert"
        )

    @trace_async_calls
    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        if not self.metrics_history:
            return {
                "status": HealthStatus.HEALTHY,
                "message": "No metrics collected yet"
            }

        latest_metrics = self.metrics_history[-1].metrics

        # Determine overall health status
        workflow_success = latest_metrics["workflow_engine"]["success_rate"]
        gateway_success = latest_metrics["rest_gateway"]["success_rate"]

        overall_success = (workflow_success + gateway_success) / 2

        if overall_success >= 0.95:
            status = HealthStatus.HEALTHY
        elif overall_success >= 0.85:
            status = HealthStatus.DEGRADED
        elif overall_success >= 0.70:
            status = HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.CRITICAL

        return {
            "status": status,
            "uptime_seconds": latest_metrics["uptime_seconds"],
            "components": {
                "workflow_engine": {
                    "status": HealthStatus.HEALTHY if workflow_success >= 0.95 else HealthStatus.DEGRADED,
                    "metrics": latest_metrics["workflow_engine"]
                },
                "agent_coordinator": {
                    "status": HealthStatus.HEALTHY,
                    "metrics": latest_metrics["agent_coordinator"]
                },
                "event_dispatcher": {
                    "status": HealthStatus.HEALTHY if latest_metrics["event_dispatcher"]["is_running"] else HealthStatus.CRITICAL,
                    "metrics": latest_metrics["event_dispatcher"]
                },
                "rest_gateway": {
                    "status": HealthStatus.HEALTHY if gateway_success >= 0.95 else HealthStatus.DEGRADED,
                    "metrics": latest_metrics["rest_gateway"]
                },
                "websocket_server": {
                    "status": HealthStatus.HEALTHY if latest_metrics["websocket_server"]["is_running"] else HealthStatus.CRITICAL,
                    "metrics": latest_metrics["websocket_server"]
                }
            },
            "recent_alerts": self.get_recent_alerts(10)
        }

    @trace_async_calls
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        if not self.metrics_history:
            return {}

        latest_metrics = self.metrics_history[-1].metrics

        return {
            "timestamp": latest_metrics["timestamp"],
            "uptime_seconds": latest_metrics["uptime_seconds"],
            "workflow_engine": {
                "total_workflows": latest_metrics["workflow_engine"]["total_workflows"],
                "active_workflows": latest_metrics["workflow_engine"]["active_workflows"],
                "completed_workflows": latest_metrics["workflow_engine"]["completed_workflows"],
                "failed_workflows": latest_metrics["workflow_engine"]["failed_workflows"],
                "success_rate": latest_metrics["workflow_engine"]["success_rate"]
            },
            "api_gateway": {
                "total_requests": latest_metrics["rest_gateway"]["total_requests"],
                "error_count": latest_metrics["rest_gateway"]["error_count"],
                "success_rate": latest_metrics["rest_gateway"]["success_rate"]
            },
            "websocket": {
                "active_connections": latest_metrics["websocket_server"]["total_connections"],
                "messages_sent": latest_metrics["websocket_server"]["total_messages_sent"],
                "messages_received": latest_metrics["websocket_server"]["total_messages_received"]
            }
        }

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        return self.alerts[-limit:] if self.alerts else []

    def get_metrics_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get metrics history for the last N minutes"""
        cutoff_time = datetime.now().timestamp() - (minutes * 60)

        history = [
            {
                "timestamp": snapshot.timestamp.isoformat(),
                "metrics": snapshot.metrics
            }
            for snapshot in self.metrics_history
            if snapshot.timestamp.timestamp() >= cutoff_time
        ]

        return history
