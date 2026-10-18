from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.container_binding_repository import (
    ContainerBindingRepository,
)
from backend.modules.aion_business.runtime.memory_scope import (
    MemoryAccessDecision,
    MemoryScope,
)


@dataclass(slots=True)
class ContainerAccessDecision:
    ok: bool
    binding_id: str
    can_read: bool
    can_write: bool
    reason: str


@dataclass(slots=True)
class AgentMemoryAccessResult:
    ok: bool
    scope_decision: MemoryAccessDecision
    container_decisions: List[ContainerAccessDecision] = field(default_factory=list)

    @property
    def readable_binding_ids(self) -> List[str]:
        return [d.binding_id for d in self.container_decisions if d.can_read]

    @property
    def writable_binding_ids(self) -> List[str]:
        return [d.binding_id for d in self.container_decisions if d.can_write]


class MemoryAccess:
    """
    v1 memory access checker.

    This layer combines:
    - agent memory scope
    - role-permitted bindings
    - agent-permitted bindings
    - workspace binding existence

    It does not read containers itself.
    It decides what the runtime should permit.
    """

    def __init__(
        self,
        binding_repository: Optional[ContainerBindingRepository] = None,
    ):
        self.binding_repository = binding_repository or ContainerBindingRepository()

    def evaluate(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        agent: AgentSpec,
        task: Optional[TaskRecord] = None,
    ) -> AgentMemoryAccessResult:
        scope_decision = MemoryScope.evaluate_agent_scope(
            workspace=workspace,
            role=role,
            agent=agent,
            task=task,
        )

        if not scope_decision.ok:
            return AgentMemoryAccessResult(
                ok=False,
                scope_decision=scope_decision,
                container_decisions=[],
            )

        workspace_binding_ids = set(self.binding_repository.list_ids(workspace.id))
        role_binding_ids = set(role.allowed_container_ids)
        agent_binding_ids = set(agent.allowed_containers)

        container_decisions: List[ContainerAccessDecision] = []
        overall_ok = True

        for binding_id in sorted(agent_binding_ids):
            if binding_id not in workspace_binding_ids:
                container_decisions.append(
                    ContainerAccessDecision(
                        ok=False,
                        binding_id=binding_id,
                        can_read=False,
                        can_write=False,
                        reason="binding_not_found_in_workspace",
                    )
                )
                overall_ok = False
                continue

            if binding_id not in role_binding_ids:
                container_decisions.append(
                    ContainerAccessDecision(
                        ok=False,
                        binding_id=binding_id,
                        can_read=False,
                        can_write=False,
                        reason="binding_not_permitted_by_role",
                    )
                )
                overall_ok = False
                continue

            container_decisions.append(
                ContainerAccessDecision(
                    ok=True,
                    binding_id=binding_id,
                    can_read=scope_decision.can_read,
                    can_write=scope_decision.can_write,
                    reason="ok",
                )
            )

        return AgentMemoryAccessResult(
            ok=overall_ok and scope_decision.ok,
            scope_decision=scope_decision,
            container_decisions=container_decisions,
        )

    def can_read_binding(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        agent: AgentSpec,
        binding_id: str,
        task: Optional[TaskRecord] = None,
    ) -> bool:
        result = self.evaluate(
            workspace=workspace,
            role=role,
            agent=agent,
            task=task,
        )
        return any(
            d.binding_id == binding_id and d.can_read
            for d in result.container_decisions
        )

    def can_write_binding(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        agent: AgentSpec,
        binding_id: str,
        task: Optional[TaskRecord] = None,
    ) -> bool:
        result = self.evaluate(
            workspace=workspace,
            role=role,
            agent=agent,
            task=task,
        )
        return any(
            d.binding_id == binding_id and d.can_write
            for d in result.container_decisions
        )