from __future__ import annotations

from typing import List, Optional

from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.containers import ContainerBindingSpec
from backend.modules.aion_business.runtime.container_binding_repository import ContainerBindingRepository
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository


class RoleBindingResolver:
    def __init__(
        self,
        workspace_repo: Optional[WorkspaceRepository] = None,
        binding_repo: Optional[ContainerBindingRepository] = None,
    ):
        self.workspace_repo = workspace_repo or WorkspaceRepository()
        self.binding_repo = binding_repo or ContainerBindingRepository()

    def get_role_bindings(self, workspace_id: str, role: RoleSpec) -> List[ContainerBindingSpec]:
        ws = self.workspace_repo.load(workspace_id)
        bindings: List[ContainerBindingSpec] = []

        for binding_id in ws.container_binding_ids:
            binding = self.binding_repo.load(workspace_id, binding_id)

            if role.allowed_container_ids and binding.id not in role.allowed_container_ids:
                continue

            bindings.append(binding)

        return bindings

    def get_role_bindings_by_category(
        self,
        workspace_id: str,
        role: RoleSpec,
        category: str,
    ) -> List[ContainerBindingSpec]:
        return [
            binding
            for binding in self.get_role_bindings(workspace_id, role)
            if binding.category == category
        ]