from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec


MemoryScopeType = Literal["none", "task", "workflow", "role", "workspace"]


@dataclass(slots=True)
class MemoryAccessDecision:
    ok: bool
    scope: MemoryScopeType
    reason: str
    can_read: bool
    can_write: bool


class MemoryScope:
    """
    v1 memory-scope policy helper.

    This does not yet perform real container-level enforcement.
    It answers:
    - what scope an agent is operating under
    - whether that scope should permit reads
    - whether that scope should permit writes
    - what higher-level runtime should do next
    """

    @staticmethod
    def normalize(scope: Optional[str]) -> MemoryScopeType:
        if scope in {"none", "task", "workflow", "role", "workspace"}:
            return scope
        return "none"

    @classmethod
    def for_agent(cls, agent: AgentSpec) -> MemoryScopeType:
        return cls.normalize(agent.memory_scope)

    @classmethod
    def can_read(cls, scope: MemoryScopeType) -> bool:
        return scope in {"task", "workflow", "role", "workspace"}

    @classmethod
    def can_write(cls, scope: MemoryScopeType, *, writable: bool = False) -> bool:
        if scope == "none":
            return False
        if scope == "task":
            return bool(writable)
        if scope in {"workflow", "role", "workspace"}:
            return bool(writable)
        return False

    @classmethod
    def evaluate_agent_scope(
        cls,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        agent: AgentSpec,
        task: Optional[TaskRecord] = None,
    ) -> MemoryAccessDecision:
        scope = cls.for_agent(agent)

        if agent.workspace_id != workspace.id:
            return MemoryAccessDecision(
                ok=False,
                scope=scope,
                reason="agent_workspace_mismatch",
                can_read=False,
                can_write=False,
            )

        if agent.parent_role_id != role.id:
            return MemoryAccessDecision(
                ok=False,
                scope=scope,
                reason="agent_role_mismatch",
                can_read=False,
                can_write=False,
            )

        if scope == "task" and task is None:
            return MemoryAccessDecision(
                ok=False,
                scope=scope,
                reason="task_scope_requires_task",
                can_read=False,
                can_write=False,
            )

        if task is not None and task.workspace_id != workspace.id:
            return MemoryAccessDecision(
                ok=False,
                scope=scope,
                reason="task_workspace_mismatch",
                can_read=False,
                can_write=False,
            )

        return MemoryAccessDecision(
            ok=True,
            scope=scope,
            reason="ok",
            can_read=cls.can_read(scope),
            can_write=cls.can_write(scope, writable=agent.writable),
        )