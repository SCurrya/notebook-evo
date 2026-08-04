"""
Multi-Agent task management router.

Provides endpoints for agent CRUD, task CRUD, scheduling, messaging,
and statistics. Includes a built-in Test Agent and Build Agent.

IMPORTANT: Specific routes (e.g., /agents/stats, /agents/tasks) MUST be
defined before parameterized routes (e.g., /agents/{agent_id}) to avoid
route shadowing.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.agent_service import (
    Agent,
    AgentCreateRequest,
    AgentManager,
    AgentMessage,
    AgentStatus,
    AgentType,
    Task,
    TaskCreateRequest,
    TaskStatus,
)

router = APIRouter()


def _get_manager() -> AgentManager:
    return AgentManager.get_instance()


# === Specific routes (MUST come before /agents/{agent_id}) ===

@router.get("/agents/stats")
async def get_stats():
    """Get summary statistics for agents, tasks, and messages."""
    return _get_manager().get_stats()


@router.post("/agents/setup-defaults")
async def setup_default_agents():
    """Create a set of default agents for common workflows.

    Creates:
    - Test Runner (type=test, capabilities=[testing, pytest])
    - Build Runner (type=build, capabilities=[build, pyinstaller])
    - Code Reviewer (type=review, capabilities=[review, code])
    - Researcher (type=research, capabilities=[research, analysis])
    """
    manager = _get_manager()
    created = []
    defaults = [
        AgentCreateRequest(
            name="Test Runner",
            type=AgentType.TEST,
            capabilities=["testing", "pytest"],
        ),
        AgentCreateRequest(
            name="Build Runner",
            type=AgentType.BUILD,
            capabilities=["build", "pyinstaller"],
        ),
        AgentCreateRequest(
            name="Code Reviewer",
            type=AgentType.REVIEW,
            capabilities=["review", "code"],
        ),
        AgentCreateRequest(
            name="Researcher",
            type=AgentType.RESEARCH,
            capabilities=["research", "analysis"],
        ),
    ]
    for req in defaults:
        # Avoid duplicates by name
        existing = [a for a in manager.list_agents() if a.name == req.name]
        if not existing:
            agent = manager.create_agent(req)
            created.append(agent.id)
    # Auto-start scheduler
    await manager.start_scheduler()
    return {
        "created_agent_ids": created,
        "scheduler_running": True,
        "total_agents": len(manager.list_agents()),
    }


# === Tasks (specific routes before parameterized) ===

@router.get("/agents/tasks", response_model=List[Task])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None),
):
    """List all tasks, optionally filtered by status."""
    return _get_manager().list_tasks(status=status)


@router.post("/agents/tasks", response_model=Task)
async def create_task(request: TaskCreateRequest):
    """Create a new task.

    The scheduler will automatically assign it to an idle agent with
    matching capabilities once dependencies are satisfied.
    """
    return await _get_manager().create_task(request)


# === Messages ===

@router.get("/agents/messages", response_model=List[AgentMessage])
async def get_messages(
    agent_id: Optional[str] = Query(None),
    unread_only: bool = Query(False),
):
    """Get messages for an agent (or all messages)."""
    return _get_manager().get_messages(agent_id=agent_id, unread_only=unread_only)


@router.post("/agents/messages", response_model=AgentMessage)
async def send_message(
    from_agent: str = Query(...),
    to_agent: str = Query(...),
    content: str = Query(...),
):
    """Send a message from one agent to another."""
    return _get_manager().send_message(from_agent, to_agent, content)


# === Scheduler control ===

@router.post("/agents/scheduler/start")
async def start_scheduler():
    """Start the background task scheduler."""
    await _get_manager().start_scheduler()
    return {"running": True}


@router.post("/agents/scheduler/stop")
async def stop_scheduler():
    """Stop the background task scheduler."""
    await _get_manager().stop_scheduler()
    return {"running": False}


# === Agent CRUD (parameterized routes come last) ===

@router.get("/agents", response_model=List[Agent])
async def list_agents(
    status: Optional[AgentStatus] = Query(None),
):
    """List all agents, optionally filtered by status."""
    manager = _get_manager()
    agents = manager.list_agents()
    if status:
        agents = [a for a in agents if a.status == status]
    return agents


@router.post("/agents", response_model=Agent)
async def create_agent(request: AgentCreateRequest):
    """Create a new agent.

    Built-in agent types with default handlers:
    - test: Runs pytest commands
    - build: Runs build commands
    - generic/research/code/review: No default handler (use custom)
    """
    return _get_manager().create_agent(request)


@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    agent = _get_manager().get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return agent


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    try:
        if not _get_manager().delete_agent(agent_id):
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        return {"deleted": True, "agent_id": agent_id}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


# === Task parameterized routes ===

@router.get("/agents/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    task = _get_manager().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task


@router.post("/agents/tasks/{task_id}/cancel", response_model=Task)
async def cancel_task(task_id: str):
    try:
        return await _get_manager().cancel_task(task_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


# === Message parameterized routes ===

@router.post("/agents/messages/{message_id}/read")
async def mark_message_read(message_id: str):
    if not _get_manager().mark_message_read(message_id):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"read": True}
