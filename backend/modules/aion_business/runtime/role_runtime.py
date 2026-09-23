from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.contracts.containers import ContainerBindingSpec
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.runtime.role_binding_resolver import RoleBindingResolver


class RoleRuntime:
    def __init__(
        self,
        workspace_repo: Optional[WorkspaceRepository] = None,
        binding_resolver: Optional[RoleBindingResolver] = None,
    ):
        self.workspace_repo = workspace_repo or WorkspaceRepository()
        self.binding_resolver = binding_resolver or RoleBindingResolver()

    def load_workspace(self, workspace_id: str) -> WorkspaceSpec:
        return self.workspace_repo.load(workspace_id)

    def _resolve_workspace(
        self,
        workspace: Optional[Union[str, WorkspaceSpec]],
        role: RoleSpec,
    ) -> WorkspaceSpec:
        if isinstance(workspace, WorkspaceSpec):
            return workspace

        if isinstance(workspace, str) and workspace.strip():
            return self.load_workspace(workspace)

        return self.load_workspace(role.workspace_id)

    def build_role_context(
        self,
        workspace: Optional[Union[str, WorkspaceSpec]],
        role: RoleSpec,
    ) -> Dict[str, Any]:
        workspace_spec = self._resolve_workspace(workspace, role)
        bindings = self.binding_resolver.get_role_bindings(workspace_spec.id, role)

        return {
            "workspace_id": workspace_spec.id,
            "workspace_name": workspace_spec.name,
            "business_type": workspace_spec.business_type,
            "role_id": role.id,
            "role_type": role.role_type,
            "objective_set": list(role.objective_set),
            "container_bindings": [b.model_dump(mode="json") for b in bindings],
        }

    def get_bindings(
        self,
        workspace: Optional[Union[str, WorkspaceSpec]],
        role: RoleSpec,
    ) -> List[ContainerBindingSpec]:
        workspace_spec = self._resolve_workspace(workspace, role)
        return self.binding_resolver.get_role_bindings(workspace_spec.id, role)

    def get_bindings_by_category(
        self,
        workspace: Optional[Union[str, WorkspaceSpec]],
        role: RoleSpec,
        category: str,
    ) -> List[ContainerBindingSpec]:
        workspace_spec = self._resolve_workspace(workspace, role)
        return self.binding_resolver.get_role_bindings_by_category(
            workspace_spec.id,
            role,
            category,
        )