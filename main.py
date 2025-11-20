"""
DayPilot Orchestration Hub - Main Application
FastAPI-based system orchestration and integration platform
All operations are traced to files in trace/ folder for debugging
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from utils.trace_logger import trace
from config.settings import settings
from models.schemas import (
    UserDataInput, VitalityStatus, APIResponse,
    SystemHealth, AgentState
)

# Import core components
from orchestrator.workflow.engine import WorkflowEngine
from orchestrator.coordinator.agent_coordinator import AgentCoordinator
from orchestrator.dispatcher.event_dispatcher import EventDispatcher
from api.gateway.rest_gateway import RESTGateway
from api.websocket.websocket_server import WebSocketServer
from api.auth.auth_service import AuthService
from dashboard.monitor.system_monitor import SystemMonitor
from dashboard.visualizer.data_visualizer import DataVisualizer


# Global component instances
workflow_engine: Optional[WorkflowEngine] = None
agent_coordinator: Optional[AgentCoordinator] = None
event_dispatcher: Optional[EventDispatcher] = None
rest_gateway: Optional[RESTGateway] = None
websocket_server: Optional[WebSocketServer] = None
auth_service: Optional[AuthService] = None
system_monitor: Optional[SystemMonitor] = None
data_visualizer: Optional[DataVisualizer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    trace.info(
        "Application startup initiated",
        context={"app_name": settings.APP_NAME, "version": settings.APP_VERSION},
        module=__name__,
        function="lifespan"
    )

    global workflow_engine, agent_coordinator, event_dispatcher
    global rest_gateway, websocket_server, auth_service
    global system_monitor, data_visualizer

    try:
        # Initialize core components
        trace.info("Initializing core components", module=__name__, function="lifespan")

        workflow_engine = WorkflowEngine()
        agent_coordinator = AgentCoordinator()
        event_dispatcher = EventDispatcher()
        auth_service = AuthService()

        # Start event dispatcher
        await event_dispatcher.start()

        # Initialize API layer
        rest_gateway = RESTGateway(workflow_engine, agent_coordinator, event_dispatcher)
        websocket_server = WebSocketServer(event_dispatcher)
        await websocket_server.start()

        # Initialize dashboard layer
        system_monitor = SystemMonitor(
            workflow_engine,
            agent_coordinator,
            event_dispatcher,
            rest_gateway,
            websocket_server
        )
        await system_monitor.start()

        data_visualizer = DataVisualizer(system_monitor)

        # Register some demo agents
        await agent_coordinator.register_agent("perception", ["data_validation", "sensor_processing"])
        await agent_coordinator.register_agent("analysis", ["rhythm_analysis", "ml_inference"])
        await agent_coordinator.register_agent("intervention", ["recommendation_generation", "notification"])

        trace.info(
            "Application startup completed successfully",
            context={
                "components_initialized": 8,
                "agents_registered": 3
            },
            module=__name__,
            function="lifespan"
        )

        yield

    except Exception as e:
        trace.critical(
            "Failed to start application",
            module=__name__,
            function="lifespan",
            exception=e
        )
        raise

    finally:
        # Shutdown
        trace.info("Application shutdown initiated", module=__name__, function="lifespan")

        try:
            if system_monitor:
                await system_monitor.stop()
            if websocket_server:
                await websocket_server.stop()
            if event_dispatcher:
                await event_dispatcher.stop()

            trace.info("Application shutdown completed", module=__name__, function="lifespan")

        except Exception as e:
            trace.error(
                "Error during application shutdown",
                module=__name__,
                function="lifespan",
                exception=e
            )


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="系统编排与集成平台 - System Orchestration and Integration Platform",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency: Verify authentication
async def verify_auth(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> str:
    """Verify user authentication via Bearer token or API key"""

    # Try API key first
    if x_api_key:
        user_id = await auth_service.verify_api_key(x_api_key)
        if user_id:
            return user_id

    # Try Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        user_id = await auth_service.verify_token(token)
        if user_id:
            return user_id

    trace.warning(
        "Unauthorized access attempt",
        module=__name__,
        function="verify_auth"
    )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials"
    )


# ========== API Routes ==========

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/auth/login")
async def login(username: str, password: str):
    """
    User login endpoint
    Returns JWT access token
    """
    trace.trace_api_call(
        endpoint="/api/v1/auth/login",
        method="POST",
        params={"username": username},
        module=__name__
    )

    token = await auth_service.authenticate(username, password)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@app.post("/api/v1/auth/api-key", response_model=dict)
async def create_api_key(user_id: str = Depends(verify_auth)):
    """Create a new API key for authenticated user"""
    api_key = await auth_service.create_api_key(user_id)

    return {
        "api_key": api_key,
        "user_id": user_id,
        "created_at": datetime.now().isoformat()
    }


@app.post("/api/v1/users/{user_id}/data", response_model=APIResponse)
async def upload_user_data(
    user_id: str,
    data: UserDataInput,
    authenticated_user: str = Depends(verify_auth)
):
    """
    Upload user sensor data and trigger workflow processing
    """
    # Verify user can only upload their own data (or is admin)
    # Simplified check - in production, implement proper authorization

    result = await rest_gateway.upload_user_data(user_id, data, authenticated_user)

    return result


@app.get("/api/v1/users/{user_id}/status", response_model=APIResponse)
async def get_user_status(
    user_id: str,
    authenticated_user: str = Depends(verify_auth)
):
    """
    Get current vitality status for user
    """
    result = await rest_gateway.get_user_status(user_id, authenticated_user)

    return result


@app.get("/api/v1/health", response_model=SystemHealth)
async def get_system_health():
    """
    Get system health status (no authentication required)
    """
    health = await rest_gateway.get_system_health()

    return health


@app.get("/api/v1/metrics/performance")
async def get_performance_metrics(user_id: str = Depends(verify_auth)):
    """
    Get detailed performance metrics
    """
    metrics = await system_monitor.get_performance_metrics()

    return metrics


@app.get("/api/v1/dashboard/overview")
async def get_dashboard_overview(user_id: str = Depends(verify_auth)):
    """
    Get complete dashboard overview
    """
    overview = await data_visualizer.get_dashboard_overview()

    return overview


@app.get("/api/v1/dashboard/vitality-trend/{user_id}")
async def get_vitality_trend(
    user_id: str,
    hours: int = 24,
    authenticated_user: str = Depends(verify_auth)
):
    """
    Get vitality trend for user
    """
    trend = await data_visualizer.get_vitality_trend(user_id, hours)

    return trend


@app.get("/api/v1/dashboard/system-performance")
async def get_system_performance_chart(
    minutes: int = 60,
    user_id: str = Depends(verify_auth)
):
    """
    Get system performance chart data
    """
    chart_data = await data_visualizer.get_system_performance_chart(minutes)

    return chart_data


@app.websocket("/api/v1/realtime")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time updates
    """
    await websocket.accept()

    # Authenticate
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        trace.warning(
            "WebSocket connection rejected: no token",
            module=__name__,
            function="websocket_endpoint"
        )
        return

    user_id = await auth_service.verify_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        trace.warning(
            "WebSocket connection rejected: invalid token",
            module=__name__,
            function="websocket_endpoint"
        )
        return

    # Connect to WebSocket server
    connection_id = await websocket_server.connect(user_id, websocket)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            await websocket_server.handle_client_message(connection_id, data)

    except WebSocketDisconnect:
        await websocket_server.disconnect(connection_id)

    except Exception as e:
        trace.error(
            f"WebSocket error for connection {connection_id}",
            module=__name__,
            function="websocket_endpoint",
            exception=e
        )
        await websocket_server.disconnect(connection_id)


@app.get("/api/v1/workflows/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    user_id: str = Depends(verify_auth)
):
    """
    Get workflow execution status
    """
    workflow = await workflow_engine.get_workflow_status(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    return workflow.dict()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with trace logging"""
    trace.error(
        "Unhandled exception",
        context={
            "path": str(request.url),
            "method": request.method
        },
        module=__name__,
        function="global_exception_handler",
        exception=exc
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn

    trace.info(
        "Starting DayPilot Orchestration Hub",
        context={
            "host": settings.HOST,
            "port": settings.PORT,
            "debug": settings.DEBUG
        },
        module=__name__
    )

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
