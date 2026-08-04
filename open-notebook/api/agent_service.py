"""
Multi-Agent task execution system.

Provides agent creation, task assignment, progress tracking, and
inter-agent communication. Includes a built-in Test Agent that can
run automated tests (pytest) and report results.

Design:
- Agents are defined with capabilities (tags) and a status
- Tasks are submitted with required capabilities
- The scheduler assigns tasks to idle agents with matching capabilities
- Tasks can have dependencies (predecessors must complete first)
- Agents communicate via a message queue
- A specialized TestAgent runs pytest and parses results

All state is held in-memory (process-local). For multi-process
deployments, plug in a Redis-backed state store.
"""

import asyncio
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field


# === Enums ===

class AgentType(str, Enum):
    GENERIC = "generic"
    TEST = "test"
    BUILD = "build"
    RESEARCH = "research"
    CODE = "code"
    REVIEW = "review"


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


# === Models ===

class AgentMessage(BaseModel):
    """Message between agents."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str
    to_agent: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    read: bool = False


class Agent(BaseModel):
    """An agent that can execute tasks."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: AgentType = AgentType.GENERIC
    status: AgentStatus = AgentStatus.IDLE
    capabilities: List[str] = Field(default_factory=list)
    current_task_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """A unit of work to be executed by an agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    required_capabilities: List[str] = Field(default_factory=list)
    assigned_agent_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)  # task IDs
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: int = 0  # 0-100
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class AgentCreateRequest(BaseModel):
    """Request to create a new agent."""
    name: str
    type: AgentType = AgentType.GENERIC
    capabilities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    required_capabilities: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)


# === Task Handlers ===

TaskHandler = Callable[[Task], Dict[str, Any]]


async def _test_agent_handler(task: Task) -> Dict[str, Any]:
    """Built-in Test Agent handler: runs pytest.

    Payload options:
        test_path: str - pytest target (file or directory)
        pytest_args: List[str] - extra pytest arguments
        timeout: int - timeout in seconds (default 300)
    """
    test_path = task.payload.get("test_path", "tests/")
    extra_args = task.payload.get("pytest_args", [])
    timeout = task.payload.get("timeout", 300)

    cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"] + extra_args
    logger.info(f"TestAgent running: {' '.join(cmd)}")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(__import__("pathlib").Path(__file__).parent.parent),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        # Parse pytest summary line
        summary = ""
        for line in stdout_text.splitlines():
            if "passed" in line or "failed" in line or "error" in line:
                summary = line.strip()
                break

        return {
            "exit_code": proc.returncode,
            "passed": proc.returncode == 0,
            "summary": summary,
            "stdout": stdout_text[-4000:],  # Truncate to avoid huge payloads
            "stderr": stderr_text[-2000:],
        }
    except asyncio.TimeoutError:
        return {
            "exit_code": -1,
            "passed": False,
            "summary": f"Test timed out after {timeout}s",
            "stdout": "",
            "stderr": f"Timeout after {timeout} seconds",
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "passed": False,
            "summary": f"Test runner error: {e}",
            "stdout": "",
            "stderr": str(e),
        }


async def _build_agent_handler(task: Task) -> Dict[str, Any]:
    """Built-in Build Agent handler: runs a build command.

    Payload options:
        command: str - shell command to run (default: pyinstaller)
        cwd: str - working directory
        timeout: int - timeout in seconds (default 600)
    """
    command = task.payload.get("command", "python -m PyInstaller --version")
    cwd = task.payload.get("cwd")
    timeout = task.payload.get("timeout", 600)

    logger.info(f"BuildAgent running: {command}")
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "exit_code": proc.returncode,
            "passed": proc.returncode == 0,
            "stdout": stdout.decode("utf-8", errors="replace")[-4000:],
            "stderr": stderr.decode("utf-8", errors="replace")[-2000:],
        }
    except asyncio.TimeoutError:
        return {
            "exit_code": -1,
            "passed": False,
            "stderr": f"Build timed out after {timeout}s",
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "passed": False,
            "stderr": str(e),
        }


# Default handlers per agent type
DEFAULT_HANDLERS: Dict[AgentType, TaskHandler] = {
    AgentType.TEST: _test_agent_handler,
    AgentType.BUILD: _build_agent_handler,
}


# === Agent Manager ===

class AgentManager:
    """In-process agent and task manager.

    Singleton: use AgentManager.get_instance() to access.
    """

    _instance: Optional["AgentManager"] = None

    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}
        self._tasks: Dict[str, Task] = {}
        self._messages: List[AgentMessage] = []
        self._handlers: Dict[AgentType, TaskHandler] = dict(DEFAULT_HANDLERS)
        self._custom_handlers: Dict[str, TaskHandler] = {}  # by agent id
        self._lock = asyncio.Lock()
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls) -> "AgentManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # --- Agent management ---

    def create_agent(self, request: AgentCreateRequest) -> Agent:
        """Create a new agent."""
        agent = Agent(
            name=request.name,
            type=request.type,
            capabilities=request.capabilities,
            metadata=request.metadata,
        )
        self._agents[agent.id] = agent
        logger.info(
            f"Agent created: id={agent.id} name={agent.name} type={agent.type}"
        )
        return agent

    def list_agents(self) -> List[Agent]:
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def delete_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        if agent.status == AgentStatus.BUSY:
            raise ValueError(f"Cannot delete busy agent: {agent.name}")
        del self._agents[agent_id]
        logger.info(f"Agent deleted: {agent_id}")
        return True

    def set_agent_status(self, agent_id: str, status: AgentStatus) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = status
            agent.last_active = datetime.now(timezone.utc).isoformat()

    # --- Task management ---

    async def create_task(self, request: TaskCreateRequest) -> Task:
        """Create a new task and queue it for scheduling."""
        task = Task(
            title=request.title,
            description=request.description,
            priority=request.priority,
            required_capabilities=request.required_capabilities,
            dependencies=request.dependencies,
            payload=request.payload,
        )
        self._tasks[task.id] = task
        logger.info(f"Task created: id={task.id} title={task.title}")
        return task

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        # Sort by priority (desc) then created_at (asc)
        tasks.sort(key=lambda t: (-t.priority, t.created_at))
        return tasks

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> Task:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            raise ValueError(f"Cannot cancel task in status: {task.status}")
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc).isoformat()
        if task.assigned_agent_id:
            self.set_agent_status(task.assigned_agent_id, AgentStatus.IDLE)
        logger.info(f"Task cancelled: {task_id}")
        return task

    # --- Scheduling ---

    def _can_schedule(self, task: Task) -> bool:
        """Check if a task's dependencies are all completed."""
        for dep_id in task.dependencies:
            dep = self._tasks.get(dep_id)
            if not dep or dep.status != TaskStatus.COMPLETED:
                return False
        return True

    def _find_agent_for_task(self, task: Task) -> Optional[Agent]:
        """Find an idle agent with matching capabilities."""
        for agent in self._agents.values():
            if agent.status != AgentStatus.IDLE:
                continue
            if task.required_capabilities and not all(
                cap in agent.capabilities for cap in task.required_capabilities
            ):
                continue
            return agent
        return None

    async def start_scheduler(self) -> None:
        """Start the background scheduler loop."""
        if self._running:
            return
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info(
            f"[AGENT/SCHEDULER] ▶ started "
            f"(loop_interval=1.0s, agents={len(self._agents)}, "
            f"tasks={len(self._tasks)})"
        )

    async def stop_scheduler(self) -> None:
        """Stop the background scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
        logger.info("[AGENT/SCHEDULER] ◼ stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop: assign and execute tasks."""
        loop_iter = 0
        while self._running:
            try:
                assigned = await self._schedule_pending_tasks()
                loop_iter += 1
                if assigned > 0:
                    logger.debug(
                        f"[AGENT/SCHEDULER]   iter={loop_iter} assigned={assigned} "
                        f"pending={sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)}"
                    )
            except Exception as e:
                logger.error(f"[AGENT/SCHEDULER] ✗ loop error: {e}")
            await asyncio.sleep(1.0)

    async def _schedule_pending_tasks(self) -> int:
        """Find pending tasks and assign them to available agents.

        Returns number of tasks assigned in this pass.
        """
        assigned = 0
        async with self._lock:
            for task in list(self._tasks.values()):
                if task.status != TaskStatus.PENDING:
                    continue
                if not self._can_schedule(task):
                    logger.debug(
                        f"[AGENT/SCHEDULER]   task {task.id} ({task.title}) "
                        f"waiting on dependencies: {[d for d in task.dependencies]}"
                    )
                    continue
                agent = self._find_agent_for_task(task)
                if not agent:
                    logger.debug(
                        f"[AGENT/SCHEDULER]   task {task.id} ({task.title}) "
                        f"no available agent with caps={task.required_capabilities}"
                    )
                    continue

                # Assign
                task.assigned_agent_id = agent.id
                task.status = TaskStatus.ASSIGNED
                task.started_at = datetime.now(timezone.utc).isoformat()
                agent.status = AgentStatus.BUSY
                agent.current_task_id = task.id
                assigned += 1
                logger.info(
                    f"[AGENT/SCHEDULER] ▸ ASSIGN task={task.id} ({task.title}) "
                    f"→ agent={agent.name} (id={agent.id}, type={agent.type})"
                )

                # Execute asynchronously
                asyncio.create_task(self._execute_task(task, agent))
        return assigned

    async def _execute_task(self, task: Task, agent: Agent) -> None:
        """Execute a task with the assigned agent's handler."""
        task.status = TaskStatus.RUNNING
        exec_start = time.time()
        logger.info(
            f"[AGENT/EXEC] ▸ task={task.id} title={task.title!r} "
            f"agent={agent.name} (type={agent.type}) payload_keys="
            f"{list(task.payload.keys()) if task.payload else []}"
        )
        try:
            handler = (
                self._custom_handlers.get(agent.id)
                or self._handlers.get(agent.type)
            )
            if not handler:
                raise ValueError(
                    f"No handler for agent type {agent.type} (agent {agent.name})"
                )
            logger.debug(
                f"[AGENT/EXEC]   task={task.id} using handler "
                f"{getattr(handler, '__name__', handler)}"
            )

            result = await handler(task) if asyncio.iscoroutinefunction(handler) else handler(task)
            task.result = result
            task.progress = 100
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            exec_time = time.time() - exec_start
            result_keys = list(result.keys()) if isinstance(result, dict) else type(result).__name__
            logger.info(
                f"[AGENT/EXEC] ◂ OK task={task.id} ({task.title}) "
                f"in {exec_time:.2f}s result_keys={result_keys}"
            )
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            exec_time = time.time() - exec_start
            logger.error(
                f"[AGENT/EXEC] ✗ FAIL task={task.id} ({task.title}) "
                f"in {exec_time:.2f}s: {type(e).__name__}: {e}"
            )
        finally:
            agent.status = AgentStatus.IDLE
            agent.current_task_id = None
            agent.last_active = datetime.now(timezone.utc).isoformat()

    # --- Messaging ---

    def send_message(
        self, from_agent: str, to_agent: str, content: str
    ) -> AgentMessage:
        """Send a message from one agent to another."""
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
        )
        self._messages.append(msg)
        return msg

    def get_messages(
        self,
        agent_id: Optional[str] = None,
        unread_only: bool = False,
    ) -> List[AgentMessage]:
        """Get messages for an agent (or all if agent_id is None)."""
        msgs = self._messages
        if agent_id:
            msgs = [m for m in msgs if m.to_agent == agent_id or m.from_agent == agent_id]
        if unread_only:
            msgs = [m for m in msgs if not m.read and m.to_agent == agent_id]
        return msgs

    def mark_message_read(self, message_id: str) -> bool:
        for msg in self._messages:
            if msg.id == message_id:
                msg.read = True
                return True
        return False

    # --- Statistics ---

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        agents = list(self._agents.values())
        tasks = list(self._tasks.values())
        return {
            "agents": {
                "total": len(agents),
                "idle": sum(1 for a in agents if a.status == AgentStatus.IDLE),
                "busy": sum(1 for a in agents if a.status == AgentStatus.BUSY),
                "offline": sum(1 for a in agents if a.status == AgentStatus.OFFLINE),
                "error": sum(1 for a in agents if a.status == AgentStatus.ERROR),
            },
            "tasks": {
                "total": len(tasks),
                "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
                "running": sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
                "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            },
            "messages": len(self._messages),
        }
