"""
Workflow Engine - LangGraph-based workflow management
Coordinates multi-agent workflows with comprehensive trace logging
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum

from utils.trace_logger import trace, trace_async_calls
from models.schemas import AgentState, WorkflowExecution, WorkflowStep


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class WorkflowEngine:
    """
    LangGraph-based workflow engine for orchestrating multi-agent tasks
    All operations are traced to files for debugging
    """

    def __init__(self):
        self.workflows: Dict[str, WorkflowExecution] = {}
        self.active_workflows = 0
        trace.info("WorkflowEngine initialized", module=__name__, function="__init__")

    @trace_async_calls
    async def create_workflow(self, user_id: str, workflow_type: str = "data_processing") -> str:
        """Create a new workflow execution"""
        workflow_id = str(uuid.uuid4())

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            user_id=user_id,
            start_time=datetime.now(),
            status=WorkflowStatus.PENDING,
            steps=[]
        )

        self.workflows[workflow_id] = execution
        trace.trace_workflow_step(
            workflow_id=workflow_id,
            step_name="create",
            status="created",
            data={"user_id": user_id, "type": workflow_type},
            module=__name__
        )

        return workflow_id

    @trace_async_calls
    async def execute_workflow(
        self,
        workflow_id: str,
        initial_state: AgentState
    ) -> Dict[str, Any]:
        """Execute a complete workflow with all steps"""

        trace.trace_workflow_step(
            workflow_id=workflow_id,
            step_name="execute",
            status="started",
            data={"user_id": initial_state.user_id},
            module=__name__
        )

        try:
            self.active_workflows += 1
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")

            workflow.status = WorkflowStatus.RUNNING
            state = initial_state
            state.workflow_id = workflow_id

            # Step 1: Perception (Data validation)
            state = await self._execute_step(workflow_id, "perception", state, self._perception_step)

            # Step 2: Analysis (Rhythm analysis)
            state = await self._execute_step(workflow_id, "analysis", state, self._analysis_step)

            # Step 3: Intervention (Generate intervention plan)
            state = await self._execute_step(workflow_id, "intervention", state, self._intervention_step)

            # Step 4: Feedback (Collect and process feedback)
            if await self._should_get_feedback(state):
                state = await self._execute_step(workflow_id, "feedback", state, self._feedback_step)

            # Complete workflow
            workflow.status = WorkflowStatus.COMPLETED
            workflow.end_time = datetime.now()
            workflow.result = {
                "validated_data": state.validated_data,
                "rhythm_analysis": state.rhythm_analysis,
                "intervention_plan": state.intervention_plan,
                "feedback": state.feedback
            }

            trace.trace_workflow_step(
                workflow_id=workflow_id,
                step_name="execute",
                status="completed",
                data={"steps_count": len(workflow.steps)},
                module=__name__
            )

            return workflow.result

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.end_time = datetime.now()

            trace.error(
                f"Workflow {workflow_id} failed",
                context={
                    "workflow_id": workflow_id,
                    "user_id": initial_state.user_id,
                    "steps_completed": len(workflow.steps)
                },
                module=__name__,
                function="execute_workflow",
                exception=e
            )
            raise

        finally:
            self.active_workflows -= 1

    async def _execute_step(
        self,
        workflow_id: str,
        step_name: str,
        state: AgentState,
        step_func: Callable
    ) -> AgentState:
        """Execute a single workflow step with tracing"""

        step = WorkflowStep(
            step_name=step_name,
            status="running",
            start_time=datetime.now()
        )

        trace.trace_workflow_step(
            workflow_id=workflow_id,
            step_name=step_name,
            status="started",
            module=__name__
        )

        try:
            state.current_step = step_name
            result_state = await step_func(state)

            step.status = "completed"
            step.end_time = datetime.now()
            step.duration_ms = (step.end_time - step.start_time).total_seconds() * 1000

            trace.trace_workflow_step(
                workflow_id=workflow_id,
                step_name=step_name,
                status="completed",
                data={"duration_ms": step.duration_ms},
                module=__name__
            )

            self.workflows[workflow_id].steps.append(step)
            return result_state

        except Exception as e:
            step.status = "failed"
            step.end_time = datetime.now()
            step.errors.append(str(e))

            trace.error(
                f"Workflow step {step_name} failed",
                context={"workflow_id": workflow_id, "step": step_name},
                module=__name__,
                function="_execute_step",
                exception=e
            )

            self.workflows[workflow_id].steps.append(step)
            raise

    async def _perception_step(self, state: AgentState) -> AgentState:
        """Perception step: validate and process sensor data"""
        trace.debug(
            "Executing perception step",
            context={"user_id": state.user_id},
            module=__name__,
            function="_perception_step"
        )

        # Simulate data validation
        await asyncio.sleep(0.05)  # Simulate processing

        state.validated_data = {
            "imu_valid": True,
            "hrv_valid": True,
            "environment_valid": True,
            "quality_score": 0.95,
            "processed_at": datetime.now().isoformat()
        }

        return state

    async def _analysis_step(self, state: AgentState) -> AgentState:
        """Analysis step: perform rhythm analysis"""
        trace.debug(
            "Executing analysis step",
            context={"user_id": state.user_id},
            module=__name__,
            function="_analysis_step"
        )

        # Simulate ML inference
        await asyncio.sleep(0.12)  # Simulate model inference

        state.rhythm_analysis = {
            "vitality_score": 0.72,
            "energy_state": "moderate",
            "risk_level": "low",
            "circadian_phase": "afternoon_peak",
            "prediction_confidence": 0.89,
            "analyzed_at": datetime.now().isoformat()
        }

        return state

    async def _intervention_step(self, state: AgentState) -> AgentState:
        """Intervention step: generate intervention plan"""
        trace.debug(
            "Executing intervention step",
            context={"user_id": state.user_id},
            module=__name__,
            function="_intervention_step"
        )

        # Simulate intervention generation
        await asyncio.sleep(0.08)

        state.intervention_plan = {
            "recommendations": [
                "Take a 10-minute break",
                "Practice deep breathing",
                "Hydrate"
            ],
            "next_intervention": datetime.now().isoformat(),
            "intervention_type": "preventive",
            "priority": "medium",
            "generated_at": datetime.now().isoformat()
        }

        return state

    async def _feedback_step(self, state: AgentState) -> AgentState:
        """Feedback step: collect user feedback"""
        trace.debug(
            "Executing feedback step",
            context={"user_id": state.user_id},
            module=__name__,
            function="_feedback_step"
        )

        await asyncio.sleep(0.03)

        state.feedback = {
            "feedback_requested": True,
            "feedback_channels": ["app", "notification"],
            "requested_at": datetime.now().isoformat()
        }

        return state

    async def _should_get_feedback(self, state: AgentState) -> bool:
        """Determine if feedback should be collected"""
        # Get feedback if intervention priority is medium or high
        if state.intervention_plan:
            priority = state.intervention_plan.get("priority", "low")
            return priority in ["medium", "high"]
        return False

    @trace_async_calls
    async def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution status"""
        return self.workflows.get(workflow_id)

    def get_active_workflows_count(self) -> int:
        """Get count of active workflows"""
        return self.active_workflows

    def get_metrics(self) -> Dict[str, Any]:
        """Get workflow engine metrics"""
        completed = sum(1 for w in self.workflows.values() if w.status == WorkflowStatus.COMPLETED)
        failed = sum(1 for w in self.workflows.values() if w.status == WorkflowStatus.FAILED)

        return {
            "total_workflows": len(self.workflows),
            "active_workflows": self.active_workflows,
            "completed_workflows": completed,
            "failed_workflows": failed,
            "success_rate": completed / len(self.workflows) if self.workflows else 0.0
        }
