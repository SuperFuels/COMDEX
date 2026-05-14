from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.tasks import TaskRecord
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.container_adapter import BusinessContainerAdapter
from backend.modules.aion_business.runtime.memory_access import MemoryAccess


@dataclass(slots=True)
class GuardedContainerReadResult:
    ok: bool
    binding_id: str
    reason: str
    container: dict | None = None


@dataclass(slots=True)
class GuardedContainerWriteResult:
    ok: bool
    binding_id: str
    reason: str
    container: dict | None = None


class ContainerGuard:
    """
    Guard layer for container reads and writes.

    v1 responsibilities:
    - enforce memory/container access decisions
    - route reads through BusinessContainerAdapter
    - route writes through BusinessContainerAdapter
    - return structured results instead of loose access logic
    """

    def __init__(
        self,
        memory_access: Optional[MemoryAccess] = None,
        container_adapter: Optional[BusinessContainerAdapter] = None,
    ):
        self.memory_access = memory_access or MemoryAccess()
        self.container_adapter = container_adapter or BusinessContainerAdapter()

    def read_container(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        agent: AgentSpec,
        binding_id: str,
        task: Optional[TaskRecord] = None,
    ) -> GuardedContainerReadResult:
        if not self.memory_access.can_read_binding(
            workspace=workspace,
            role=role,
            agent=agent,
            binding_id=binding_id,
            task=task,
        ):
            return GuardedContainerReadResult(
                ok=False,
                binding_id=binding_id,
                reason="read_not_permitted",
                container=None,
            )

        try:
            container = self.container_adapter.get_container(binding_id)
        except Exception as exc:
            return GuardedContainerReadResult(
                ok=False,
                binding_id=binding_id,
                reason=f"container_read_failed:{exc}",
                container=None,
            )

        if not isinstance(container, dict) or not container:
            return GuardedContainerReadResult(
                ok=False,
                binding_id=binding_id,
                reason="container_not_found",
                container=None,
            )

        return GuardedContainerReadResult(
            ok=True,
            binding_id=binding_id,
            reason="ok",
            container=container,
        )

    def write_container(
        self,
        *,
        workspace: WorkspaceSpec,
        role: RoleSpec,
        agent: AgentSpec,
        binding_id: str,
        data: dict,
        task: Optional[TaskRecord] = None,
    ) -> GuardedContainerWriteResult:
        if not self.memory_access.can_write_binding(
            workspace=workspace,
            role=role,
            agent=agent,
            binding_id=binding_id,
            task=task,
        ):
            return GuardedContainerWriteResult(
                ok=False,
                binding_id=binding_id,
                reason="write_not_permitted",
                container=None,
            )

        try:
            binding = self.container_adapter.get_binding(binding_id)
            saved = self.container_adapter.save_container(binding, data)
        except Exception as exc:
            return GuardedContainerWriteResult(
                ok=False,
                binding_id=binding_id,
                reason=f"container_write_failed:{exc}",
                container=None,
            )

        return GuardedContainerWriteResult(
            ok=True,
            binding_id=binding_id,
            reason="ok",
            container=saved,
        )