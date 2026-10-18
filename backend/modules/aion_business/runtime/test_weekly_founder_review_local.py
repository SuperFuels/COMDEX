from __future__ import annotations

from backend.modules.aion_business.runtime.role_repository import RoleRepository
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.workflows.weekly_founder_review import (
    WeeklyFounderReviewWorkflow,
)


def main() -> None:
    workspace_id = "test-workspace"
    role_id = "ceo-core"

    workspace = WorkspaceRepository().load(workspace_id)
    role = RoleRepository().load(workspace_id, role_id)

    workflow = WeeklyFounderReviewWorkflow()
    run_state = workflow.run(
        workspace=workspace,
        role=role,
        days_back=7,
        include_draft=True,
    )

    print("STATUS:", run_state.status)
    print("FAILED STEP:", run_state.failed_step_id)
    print("ERROR:", run_state.outputs.get("error"))
    print()

    draft = run_state.outputs.get("draft_content", {})
    print("DRAFT ROUTE:", draft.get("route"))
    print("DRAFT PROVIDER:", draft.get("provider"))
    print("DRAFT MODEL:", draft.get("model"))
    print("DRAFT TEXT:", draft.get("draft"))
    print()

    assert run_state.status == "completed"
    assert draft.get("route") == "local_llm"
    assert (draft.get("draft") or "").strip()

    print("OK: weekly founder review local routing test passed")


if __name__ == "__main__":
    main()