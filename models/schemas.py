"""
Data models and schemas for the DayPilot Orchestration Hub
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class EnergyState(str, Enum):
    """Energy state levels"""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentState(BaseModel):
    """State model for LangGraph agents"""
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    sensor_data: Dict[str, Any] = Field(default_factory=dict)
    validated_data: Optional[Dict[str, Any]] = None
    rhythm_analysis: Optional[Dict[str, Any]] = None
    intervention_plan: Optional[Dict[str, Any]] = None
    feedback: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    workflow_id: str = ""
    current_step: str = ""


class SensorData(BaseModel):
    """Sensor data input model"""
    timestamp: datetime
    imu: Dict[str, Any] = Field(default_factory=dict)
    hrv: Dict[str, Any] = Field(default_factory=dict)
    environment: Dict[str, Any] = Field(default_factory=dict)


class UserDataInput(BaseModel):
    """User data upload request"""
    timestamp: datetime
    sensor_data: SensorData


class VitalityStatus(BaseModel):
    """User vitality status response"""
    vitality_score: float = Field(ge=0.0, le=1.0)
    energy_state: EnergyState
    risk_level: RiskLevel
    next_intervention: Optional[datetime] = None
    recommendations: List[str] = Field(default_factory=list)


class SystemHealth(BaseModel):
    """System health status"""
    status: str
    uptime_seconds: float
    services: Dict[str, bool]
    metrics: Dict[str, Any]


class PerformanceMetrics(BaseModel):
    """Performance metrics for system components"""
    perception_core: Dict[str, Any]
    rhythm_intelligence: Dict[str, Any]
    intervention_platform: Dict[str, Any]


class WorkflowStep(BaseModel):
    """Workflow execution step"""
    step_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class WorkflowExecution(BaseModel):
    """Complete workflow execution record"""
    workflow_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    steps: List[WorkflowStep] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None


class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: str = ""


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
