from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.runtime.agent_spawn_engine import AgentSpawnEngine
from backend.modules.aion_business.runtime.task_record_repository import TaskRecordRepository
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository


class TaskSpawnService:
    def __init__(
        self,
        repository: Optional[TaskRecordRepository] = None,
        agent_spawn_engine: Optional[AgentSpawnEngine] = None,
        workspace_repository: Optional[WorkspaceRepository] = None,
    ):
        self.repository = repository or TaskRecordRepository()
        self.agent_spawn_engine = agent_spawn_engine or AgentSpawnEngine()
        self.workspace_repository = workspace_repository or WorkspaceRepository()

    def spawn_from_plan(
        self,
        *,
        workspace_id: str,
        role: RoleSpec,
        plan: Dict[str, Any],
    ) -> TaskRecord:
        task = TaskRecord(
            id=f"task-{secrets.token_hex(6)}",
            workspace_id=workspace_id,
            created_by=role.id,
            owned_by_role=role.id,
            assigned_agent_id=None,
            objective=plan["objective"],
            status="queued",
            priority=plan.get("priority", "medium"),
            inputs={
                "task_type": plan.get("task_type"),
                "plan_context": plan.get("context", {}),
                "requested_skills": plan.get("requested_skills", []),
                "allowed_tools": plan.get("allowed_tools", []),
                "output_contract": plan.get("output_contract", "task_output_v1"),
                "ttl_seconds": int(plan.get("ttl_seconds", 3600)),
                "writable": bool(plan.get("writable", False)),
            },
            linked_containers=list(plan.get("linked_containers", [])),
        )

        self.repository.save(task)

        agent = self._spawn_agent_for_task(
            workspace_id=workspace_id,
            role=role,
            task=task,
            plan=plan,
        )

        task.assigned_agent_id = agent.id
        task.updated_at = self._utc_now_iso()
        self.repository.save(task)
        return task

    def _spawn_agent_for_task(
        self,
        *,
        workspace_id: str,
        role: RoleSpec,
        task: TaskRecord,
        plan: Dict[str, Any],
    ) -> AgentSpec:
        workspace = self.workspace_repository.load(workspace_id)

        return self.agent_spawn_engine.spawn_task_agent(
            workspace=workspace,
            role=role,
            task=task,
            output_contract=plan.get("output_contract", "task_output_v1"),
            ttl_seconds=int(plan.get("ttl_seconds", 3600)),
            writable=bool(plan.get("writable", False)),
        )

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()