"""
Agent Coordinator - Multi-agent coordination and communication
Manages task distribution and load balancing across agents
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
import uuid

from utils.trace_logger import trace, trace_async_calls


class AgentInfo:
    """Information about a registered agent"""

    def __init__(self, agent_id: str, agent_type: str, capabilities: List[str]):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.status = "idle"
        self.current_task = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.registered_at = datetime.now()
        self.last_heartbeat = datetime.now()


class AgentCoordinator:
    """
    Coordinates multiple agents with task distribution and load balancing
    All coordination activities are traced for debugging
    """

    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.task_results: Dict[str, Any] = {}
        self.agent_load: Dict[str, int] = defaultdict(int)

        trace.info("AgentCoordinator initialized", module=__name__, function="__init__")

    @trace_async_calls
    async def register_agent(
        self,
        agent_type: str,
        capabilities: List[str]
    ) -> str:
        """Register a new agent with the coordinator"""

        agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"
        agent_info = AgentInfo(agent_id, agent_type, capabilities)
        self.agents[agent_id] = agent_info
        self.agent_load[agent_id] = 0

        trace.info(
            f"Agent registered: {agent_id}",
            context={
                "agent_id": agent_id,
                "type": agent_type,
                "capabilities": capabilities
            },
            module=__name__,
            function="register_agent"
        )

        return agent_id

    @trace_async_calls
    async def unregister_agent(self, agent_id: str):
        """Unregister an agent"""

        if agent_id in self.agents:
            agent = self.agents[agent_id]
            del self.agents[agent_id]
            del self.agent_load[agent_id]

            trace.info(
                f"Agent unregistered: {agent_id}",
                context={
                    "agent_id": agent_id,
                    "tasks_completed": agent.tasks_completed,
                    "tasks_failed": agent.tasks_failed
                },
                module=__name__,
                function="unregister_agent"
            )

    @trace_async_calls
    async def assign_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """Assign a task to the most suitable agent"""

        task_id = str(uuid.uuid4())

        trace.debug(
            f"Assigning task {task_id}",
            context={
                "task_id": task_id,
                "task_type": task_type,
                "priority": priority
            },
            module=__name__,
            function="assign_task"
        )

        # Find suitable agents based on capabilities
        suitable_agents = [
            agent for agent in self.agents.values()
            if task_type in agent.capabilities and agent.status == "idle"
        ]

        if not suitable_agents:
            trace.warning(
                f"No suitable agents for task {task_id}",
                context={"task_type": task_type, "available_agents": len(self.agents)},
                module=__name__,
                function="assign_task"
            )
            # Queue the task
            await self.task_queue.put({
                "task_id": task_id,
                "task_type": task_type,
                "task_data": task_data,
                "priority": priority,
                "queued_at": datetime.now()
            })
            return task_id

        # Select agent with lowest load
        selected_agent = min(suitable_agents, key=lambda a: self.agent_load[a.agent_id])

        # Assign task to agent
        selected_agent.status = "busy"
        selected_agent.current_task = task_id
        self.agent_load[selected_agent.agent_id] += 1

        trace.info(
            f"Task {task_id} assigned to {selected_agent.agent_id}",
            context={
                "task_id": task_id,
                "agent_id": selected_agent.agent_id,
                "agent_load": self.agent_load[selected_agent.agent_id]
            },
            module=__name__,
            function="assign_task"
        )

        # Simulate task execution
        asyncio.create_task(
            self._execute_agent_task(selected_agent.agent_id, task_id, task_data)
        )

        return task_id

    async def _execute_agent_task(
        self,
        agent_id: str,
        task_id: str,
        task_data: Dict[str, Any]
    ):
        """Execute a task on an agent"""

        trace.debug(
            f"Executing task {task_id} on agent {agent_id}",
            context={"task_id": task_id, "agent_id": agent_id},
            module=__name__,
            function="_execute_agent_task"
        )

        try:
            # Simulate task execution
            await asyncio.sleep(0.1)

            # Mark task as completed
            agent = self.agents[agent_id]
            agent.status = "idle"
            agent.current_task = None
            agent.tasks_completed += 1
            self.agent_load[agent_id] -= 1

            # Store result
            self.task_results[task_id] = {
                "status": "completed",
                "result": {"success": True, "data": task_data},
                "completed_at": datetime.now(),
                "agent_id": agent_id
            }

            trace.info(
                f"Task {task_id} completed by {agent_id}",
                context={"task_id": task_id, "agent_id": agent_id},
                module=__name__,
                function="_execute_agent_task"
            )

            # Process next queued task if any
            if not self.task_queue.empty():
                next_task = await self.task_queue.get()
                await self.assign_task(
                    next_task["task_type"],
                    next_task["task_data"],
                    next_task["priority"]
                )

        except Exception as e:
            agent = self.agents[agent_id]
            agent.status = "idle"
            agent.current_task = None
            agent.tasks_failed += 1
            self.agent_load[agent_id] -= 1

            self.task_results[task_id] = {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now(),
                "agent_id": agent_id
            }

            trace.error(
                f"Task {task_id} failed on agent {agent_id}",
                context={"task_id": task_id, "agent_id": agent_id},
                module=__name__,
                function="_execute_agent_task",
                exception=e
            )

    @trace_async_calls
    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a task"""
        return self.task_results.get(task_id)

    @trace_async_calls
    async def heartbeat(self, agent_id: str):
        """Update agent heartbeat"""
        if agent_id in self.agents:
            self.agents[agent_id].last_heartbeat = datetime.now()

    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent status information"""
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        return {
            "agent_id": agent.agent_id,
            "type": agent.agent_type,
            "status": agent.status,
            "current_task": agent.current_task,
            "tasks_completed": agent.tasks_completed,
            "tasks_failed": agent.tasks_failed,
            "load": self.agent_load[agent_id],
            "uptime_seconds": (datetime.now() - agent.registered_at).total_seconds()
        }

    def get_coordinator_metrics(self) -> Dict[str, Any]:
        """Get coordinator metrics"""
        total_agents = len(self.agents)
        busy_agents = sum(1 for a in self.agents.values() if a.status == "busy")
        total_completed = sum(a.tasks_completed for a in self.agents.values())
        total_failed = sum(a.tasks_failed for a in self.agents.values())

        return {
            "total_agents": total_agents,
            "busy_agents": busy_agents,
            "idle_agents": total_agents - busy_agents,
            "queued_tasks": self.task_queue.qsize(),
            "completed_tasks": total_completed,
            "failed_tasks": total_failed,
            "success_rate": total_completed / (total_completed + total_failed) if (total_completed + total_failed) > 0 else 1.0
        }
