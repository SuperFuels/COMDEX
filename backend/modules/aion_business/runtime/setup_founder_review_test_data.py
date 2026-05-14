from __future__ import annotations

from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.runtime.role_repository import RoleRepository
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository


def main() -> None:
    workspace = WorkspaceSpec(
        id="test-workspace",
        name="Test Workspace",
        business_type="service_business",
        owner="Kevin Robinson",
    )

    role = RoleSpec(
        id="ceo-core",
        workspace_id=workspace.id,
        role_type="CEO",
        business_type=workspace.business_type,
        model_policy_ref="default",
    )

    WorkspaceRepository().save(workspace)
    RoleRepository().save(role)

    print("Created workspace:", workspace.id)
    print("Created role:", role.id)


if __name__ == "__main__":
    main()