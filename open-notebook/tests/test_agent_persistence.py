# -*- coding: utf-8 -*-
"""Unit tests for agent persistence (survives restarts)."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestStateStore:
    def test_save_and_load_roundtrip(self, tmp_path):
        from api.agent_persistence import AgentStateStore

        store = AgentStateStore(tmp_path / "agent_state.json")
        store.save(
            agents=[{"id": "a1", "name": "Agent A", "type": "generic"}],
            tasks=[{"id": "t1", "title": "Task 1"}],
            messages=[{"id": "m1", "from_agent": "a1", "to_agent": "a1", "content": "hi"}],
        )
        data = store.load()
        assert data["agents"][0]["id"] == "a1"
        assert data["tasks"][0]["title"] == "Task 1"
        assert data["messages"][0]["content"] == "hi"

    def test_load_missing_file(self, tmp_path):
        from api.agent_persistence import AgentStateStore

        store = AgentStateStore(tmp_path / "nonexistent.json")
        assert store.load() == {"agents": [], "tasks": [], "messages": []}

    def test_load_corrupt_file(self, tmp_path):
        from api.agent_persistence import AgentStateStore

        path = tmp_path / "agent_state.json"
        path.write_text("{not valid json", encoding="utf-8")
        store = AgentStateStore(path)
        assert store.load() == {"agents": [], "tasks": [], "messages": []}


class TestAgentManagerPersistence:
    @pytest.mark.asyncio
    async def test_restore_after_restart(self, tmp_path):
        from api.agent_service import (
            AgentCreateRequest,
            AgentManager,
            AgentType,
            TaskCreateRequest,
            TaskPriority,
        )

        state_file = tmp_path / "agent_state.json"

        # First "process"
        m1 = AgentManager(str(state_file))
        a = m1.create_agent(
            AgentCreateRequest(name="研究员", type=AgentType.RESEARCH, capabilities=["research"])
        )
        t = await m1.create_task(
            TaskCreateRequest(
                title="调研任务",
                description="收集资料",
                priority=TaskPriority.HIGH,
                required_capabilities=["research"],
            )
        )

        # Second "process" (simulating restart) loads from same file
        m2 = AgentManager(str(state_file))
        agents = m2.list_agents()
        tasks = m2.list_tasks()

        assert len(agents) == 1
        assert agents[0].id == a.id
        assert agents[0].name == "研究员"
        assert agents[0].type == AgentType.RESEARCH

        assert len(tasks) == 1
        assert tasks[0].id == t.id
        assert tasks[0].title == "调研任务"
        assert tasks[0].priority == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_busy_agent_reset_to_idle_on_restore(self, tmp_path):
        from api.agent_service import Agent, AgentManager, AgentStatus, AgentType

        state_file = tmp_path / "agent_state.json"
        m1 = AgentManager(str(state_file))
        agent = m1.create_agent(
            __import__("api.agent_service", fromlist=["AgentCreateRequest"]).AgentCreateRequest(
                name="Busy", capabilities=[]
            )
        )
        # Manually set BUSY then persist
        m1.set_agent_status(agent.id, AgentStatus.BUSY)
        m1._persist()

        m2 = AgentManager(str(state_file))
        restored = m2.get_agent(agent.id)
        assert restored is not None
        assert restored.status == AgentStatus.IDLE
        assert restored.current_task_id is None
