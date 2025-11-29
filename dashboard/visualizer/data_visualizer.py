"""
Data Visualizer - Prepare data for visualization
Generates chart data and statistics for dashboard
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict

from utils.trace_logger import trace, trace_async_calls


class DataVisualizer:
    """
    Prepares data for visualization in dashboard
    All data processing is traced to files
    """

    def __init__(self, system_monitor):
        self.system_monitor = system_monitor

        trace.info("DataVisualizer initialized", module=__name__, function="__init__")

    @trace_async_calls
    async def get_vitality_trend(
        self,
        user_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get vitality score trend over time"""

        trace.debug(
            f"Generating vitality trend for user {user_id}",
            context={"user_id": user_id, "hours": hours},
            module=__name__,
            function="get_vitality_trend"
        )

        # Simulate trend data
        # In production, query from database
        now = datetime.now()
        data_points = []

        for i in range(hours):
            timestamp = now - timedelta(hours=hours - i)
            # Simulate vitality score with some variation
            base_score = 0.7
            variation = 0.1 * (i % 3 - 1)  # Simple oscillation
            score = max(0.0, min(1.0, base_score + variation))

            data_points.append({
                "timestamp": timestamp.isoformat(),
                "vitality_score": round(score, 3),
                "energy_state": "moderate" if score > 0.6 else "low"
            })

        return {
            "user_id": user_id,
            "period_hours": hours,
            "data_points": data_points,
            "statistics": {
                "average": round(sum(p["vitality_score"] for p in data_points) / len(data_points), 3),
                "min": round(min(p["vitality_score"] for p in data_points), 3),
                "max": round(max(p["vitality_score"] for p in data_points), 3)
            }
        }

    @trace_async_calls
    async def get_system_performance_chart(
        self,
        minutes: int = 60
    ) -> Dict[str, Any]:
        """Get system performance metrics for charting"""

        trace.debug(
            "Generating system performance chart",
            context={"minutes": minutes},
            module=__name__,
            function="get_system_performance_chart"
        )

        # Get metrics history from system monitor
        history = self.system_monitor.get_metrics_history(minutes)

        if not history:
            return {
                "period_minutes": minutes,
                "data_points": [],
                "message": "No data available"
            }

        data_points = []
        for snapshot in history:
            timestamp = snapshot["timestamp"]
            metrics = snapshot["metrics"]

            data_points.append({
                "timestamp": timestamp,
                "workflow_success_rate": metrics["workflow_engine"]["success_rate"],
                "api_success_rate": metrics["rest_gateway"]["success_rate"],
                "active_workflows": metrics["workflow_engine"]["active_workflows"],
                "api_requests": metrics["rest_gateway"]["total_requests"],
                "websocket_connections": metrics["websocket_server"]["total_connections"]
            })

        return {
            "period_minutes": minutes,
            "data_points": data_points,
            "summary": {
                "average_workflow_success": round(
                    sum(p["workflow_success_rate"] for p in data_points) / len(data_points), 3
                ),
                "average_api_success": round(
                    sum(p["api_success_rate"] for p in data_points) / len(data_points), 3
                ),
                "peak_workflows": max(p["active_workflows"] for p in data_points),
                "peak_connections": max(p["websocket_connections"] for p in data_points)
            }
        }

    @trace_async_calls
    async def get_workflow_distribution(self) -> Dict[str, Any]:
        """Get workflow status distribution"""

        trace.debug(
            "Generating workflow distribution",
            module=__name__,
            function="get_workflow_distribution"
        )

        metrics = self.system_monitor.workflow_engine.get_metrics()

        total = metrics["total_workflows"]
        completed = metrics["completed_workflows"]
        failed = metrics["failed_workflows"]
        active = metrics["active_workflows"]
        pending = total - completed - failed - active

        return {
            "total": total,
            "distribution": {
                "completed": completed,
                "failed": failed,
                "active": active,
                "pending": pending
            },
            "percentages": {
                "completed": round(completed / total * 100, 1) if total > 0 else 0,
                "failed": round(failed / total * 100, 1) if total > 0 else 0,
                "active": round(active / total * 100, 1) if total > 0 else 0,
                "pending": round(pending / total * 100, 1) if total > 0 else 0
            }
        }

    @trace_async_calls
    async def get_event_distribution(self) -> Dict[str, Any]:
        """Get event type distribution"""

        trace.debug(
            "Generating event distribution",
            module=__name__,
            function="get_event_distribution"
        )

        metrics = self.system_monitor.event_dispatcher.get_dispatcher_metrics()

        distribution = metrics.get("event_type_distribution", {})

        return {
            "total_events": metrics["total_events"],
            "distribution": distribution,
            "top_events": sorted(
                distribution.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]  # Top 10 event types
        }

    @trace_async_calls
    async def get_agent_performance(self) -> Dict[str, Any]:
        """Get agent performance statistics"""

        trace.debug(
            "Generating agent performance statistics",
            module=__name__,
            function="get_agent_performance"
        )

        metrics = self.system_monitor.agent_coordinator.get_coordinator_metrics()

        return {
            "total_agents": metrics["total_agents"],
            "busy_agents": metrics["busy_agents"],
            "idle_agents": metrics["idle_agents"],
            "utilization": round(
                metrics["busy_agents"] / metrics["total_agents"] * 100, 1
            ) if metrics["total_agents"] > 0 else 0,
            "tasks": {
                "completed": metrics["completed_tasks"],
                "failed": metrics["failed_tasks"],
                "queued": metrics["queued_tasks"],
                "success_rate": round(metrics["success_rate"] * 100, 1)
            }
        }

    @trace_async_calls
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get complete dashboard overview"""

        trace.debug(
            "Generating dashboard overview",
            module=__name__,
            function="get_dashboard_overview"
        )

        health = await self.system_monitor.get_system_health()
        performance = await self.system_monitor.get_performance_metrics()
        workflow_dist = await self.get_workflow_distribution()
        agent_perf = await self.get_agent_performance()

        return {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "performance": performance,
            "workflow_distribution": workflow_dist,
            "agent_performance": agent_perf,
            "recent_alerts": self.system_monitor.get_recent_alerts(5)
        }
