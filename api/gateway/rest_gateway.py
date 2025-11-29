"""
REST Gateway - RESTful API unified entry point
Handles request routing, authentication, and rate limiting
"""
import time
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict
import asyncio

from utils.trace_logger import trace, trace_async_calls
from models.schemas import (
    UserDataInput, VitalityStatus, APIResponse,
    SystemHealth, AgentState
)


class RateLimiter:
    """Simple rate limiter for API requests"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed"""
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]

        # Check limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False

        # Add current request
        self.requests[client_id].append(now)
        return True


class RESTGateway:
    """
    REST API Gateway for unified access to system services
    All API calls are traced to files for debugging
    """

    def __init__(self, workflow_engine, agent_coordinator, event_dispatcher):
        self.workflow_engine = workflow_engine
        self.agent_coordinator = agent_coordinator
        self.event_dispatcher = event_dispatcher
        self.rate_limiter = RateLimiter(requests_per_minute=60)
        self.request_count = 0
        self.error_count = 0

        trace.info("RESTGateway initialized", module=__name__, function="__init__")

    @trace_async_calls
    async def upload_user_data(
        self,
        user_id: str,
        data: UserDataInput,
        client_id: str
    ) -> APIResponse:
        """
        POST /api/v1/users/{user_id}/data
        Upload user sensor data and trigger workflow
        """

        request_id = f"req_{int(time.time() * 1000)}"
        start_time = time.time()

        trace.trace_api_call(
            endpoint=f"/api/v1/users/{user_id}/data",
            method="POST",
            params={"user_id": user_id, "timestamp": str(data.timestamp)},
            module=__name__
        )

        try:
            # Rate limiting
            if not self.rate_limiter.is_allowed(client_id):
                trace.warning(
                    f"Rate limit exceeded for client {client_id}",
                    context={"client_id": client_id, "user_id": user_id},
                    module=__name__,
                    function="upload_user_data"
                )

                duration_ms = (time.time() - start_time) * 1000
                trace.trace_api_response(
                    endpoint=f"/api/v1/users/{user_id}/data",
                    status_code=429,
                    response={"error": "Rate limit exceeded"},
                    duration_ms=duration_ms,
                    module=__name__
                )

                return APIResponse(
                    success=False,
                    error="Rate limit exceeded",
                    request_id=request_id
                )

            self.request_count += 1

            # Emit data received event
            await self.event_dispatcher.emit(
                "data.received",
                {
                    "user_id": user_id,
                    "timestamp": data.timestamp.isoformat(),
                    "request_id": request_id
                }
            )

            # Create workflow
            workflow_id = await self.workflow_engine.create_workflow(user_id)

            # Prepare initial state
            initial_state = AgentState(
                user_id=user_id,
                timestamp=data.timestamp,
                sensor_data={
                    "imu": data.sensor_data.imu,
                    "hrv": data.sensor_data.hrv,
                    "environment": data.sensor_data.environment
                }
            )

            # Execute workflow
            result = await self.workflow_engine.execute_workflow(
                workflow_id,
                initial_state
            )

            # Emit data processed event
            await self.event_dispatcher.emit(
                "data.processed",
                {
                    "user_id": user_id,
                    "workflow_id": workflow_id,
                    "request_id": request_id
                }
            )

            duration_ms = (time.time() - start_time) * 1000

            trace.trace_api_response(
                endpoint=f"/api/v1/users/{user_id}/data",
                status_code=200,
                response={"workflow_id": workflow_id},
                duration_ms=duration_ms,
                module=__name__
            )

            return APIResponse(
                success=True,
                data={
                    "workflow_id": workflow_id,
                    "result": result
                },
                request_id=request_id
            )

        except Exception as e:
            self.error_count += 1

            trace.error(
                f"Error processing user data upload for {user_id}",
                context={"user_id": user_id, "request_id": request_id},
                module=__name__,
                function="upload_user_data",
                exception=e
            )

            duration_ms = (time.time() - start_time) * 1000

            trace.trace_api_response(
                endpoint=f"/api/v1/users/{user_id}/data",
                status_code=500,
                response={"error": str(e)},
                duration_ms=duration_ms,
                module=__name__
            )

            return APIResponse(
                success=False,
                error=str(e),
                request_id=request_id
            )

    @trace_async_calls
    async def get_user_status(
        self,
        user_id: str,
        client_id: str
    ) -> APIResponse:
        """
        GET /api/v1/users/{user_id}/status
        Get current user vitality status
        """

        request_id = f"req_{int(time.time() * 1000)}"
        start_time = time.time()

        trace.trace_api_call(
            endpoint=f"/api/v1/users/{user_id}/status",
            method="GET",
            params={"user_id": user_id},
            module=__name__
        )

        try:
            # Rate limiting
            if not self.rate_limiter.is_allowed(client_id):
                duration_ms = (time.time() - start_time) * 1000
                trace.trace_api_response(
                    endpoint=f"/api/v1/users/{user_id}/status",
                    status_code=429,
                    response={"error": "Rate limit exceeded"},
                    duration_ms=duration_ms,
                    module=__name__
                )

                return APIResponse(
                    success=False,
                    error="Rate limit exceeded",
                    request_id=request_id
                )

            self.request_count += 1

            # Simulate retrieving user status
            # In production, this would query a database or cache
            status = VitalityStatus(
                vitality_score=0.72,
                energy_state="moderate",
                risk_level="low",
                next_intervention=datetime.now(),
                recommendations=[
                    "Take a short break",
                    "Stay hydrated",
                    "Practice deep breathing"
                ]
            )

            duration_ms = (time.time() - start_time) * 1000

            trace.trace_api_response(
                endpoint=f"/api/v1/users/{user_id}/status",
                status_code=200,
                response=status.dict(),
                duration_ms=duration_ms,
                module=__name__
            )

            return APIResponse(
                success=True,
                data=status.dict(),
                request_id=request_id
            )

        except Exception as e:
            self.error_count += 1

            trace.error(
                f"Error retrieving user status for {user_id}",
                context={"user_id": user_id, "request_id": request_id},
                module=__name__,
                function="get_user_status",
                exception=e
            )

            duration_ms = (time.time() - start_time) * 1000

            trace.trace_api_response(
                endpoint=f"/api/v1/users/{user_id}/status",
                status_code=500,
                response={"error": str(e)},
                duration_ms=duration_ms,
                module=__name__
            )

            return APIResponse(
                success=False,
                error=str(e),
                request_id=request_id
            )

    @trace_async_calls
    async def get_system_health(self) -> SystemHealth:
        """
        GET /api/v1/health
        Get system health status
        """

        start_time = time.time()

        trace.trace_api_call(
            endpoint="/api/v1/health",
            method="GET",
            params={},
            module=__name__
        )

        try:
            workflow_metrics = self.workflow_engine.get_metrics()
            coordinator_metrics = self.agent_coordinator.get_coordinator_metrics()
            dispatcher_metrics = self.event_dispatcher.get_dispatcher_metrics()

            health = SystemHealth(
                status="healthy",
                uptime_seconds=(time.time() - start_time),
                services={
                    "workflow_engine": True,
                    "agent_coordinator": True,
                    "event_dispatcher": dispatcher_metrics["is_running"],
                    "rest_gateway": True
                },
                metrics={
                    "workflow_engine": workflow_metrics,
                    "agent_coordinator": coordinator_metrics,
                    "event_dispatcher": dispatcher_metrics,
                    "api_gateway": {
                        "total_requests": self.request_count,
                        "error_count": self.error_count,
                        "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0.0
                    }
                }
            )

            duration_ms = (time.time() - start_time) * 1000

            trace.trace_api_response(
                endpoint="/api/v1/health",
                status_code=200,
                response=health.dict(),
                duration_ms=duration_ms,
                module=__name__
            )

            return health

        except Exception as e:
            trace.error(
                "Error retrieving system health",
                module=__name__,
                function="get_system_health",
                exception=e
            )
            raise

    def get_gateway_metrics(self) -> Dict[str, Any]:
        """Get gateway metrics"""
        return {
            "total_requests": self.request_count,
            "error_count": self.error_count,
            "success_rate": (self.request_count - self.error_count) / self.request_count if self.request_count > 0 else 1.0
        }
