from __future__ import annotations

from pathlib import Path

from backend.modules.aion_business.api import department_pilot_api as api
from backend.modules.aion_business.contracts.department_pilot import (
    BoardroomAssignmentAction,
)
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.central_pilot_department_router import (
    CentralPilotDepartmentRouter,
)
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    approve_assignment_package,
    create_assignment_package,
    create_provenance,
)
from backend.modules.aion_business.runtime.department_pilot_profiles import (
    get_workspace_department_pilot_profile,
)
from backend.modules.aion_business.runtime.department_pilot_repository import (
    DepartmentPilotRepository,
)
from backend.modules.aion_business.runtime.department_pilot_runtime import (
    DepartmentPilotRuntime,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


class _Containers:
    def load_optional_dict(self, workspace_id: str, kind: str):
        assert workspace_id == "acme"
        assert kind == "department_intelligence"
        return {
            "custom_departments": [{
                "id": "continuity_lab",
                "name": "Continuity Lab",
                "core": False,
            }]
        }


def _repository(tmp_path: Path) -> tuple[DepartmentPilotRepository, VaultDomainStore]:
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id="acme", encryption_key=b"p" * 32
    )
    store = VaultDomainStore(guardian, actor_id="future-department-test")
    return DepartmentPilotRepository(
        base_dir=tmp_path / "legacy-pilot-runtime", domain_store=store
    ), store


def _package():
    provenance = create_provenance(
        created_by="boardroom", created_at="2026-10-18T03:00:00+00:00"
    )
    draft = create_assignment_package(
        package_id="pkg-continuity",
        workspace_id="acme",
        business_id="acme",
        boardroom_session_id="board-1",
        boardroom_decision_id="decision-1",
        title="Continuity evidence",
        objective="Prepare restart evidence without external execution.",
        department_id="continuity_lab",
        actions=[BoardroomAssignmentAction(
            action_id="prepare-evidence",
            title="Prepare evidence",
            objective="Prepare the governed evidence.",
            department_id="continuity_lab",
            capability="department.records",
            acceptance_criteria=["History survives restart"],
        )],
        provenance=provenance,
    )
    return approve_assignment_package(
        draft,
        approval_id="board-approval-1",
        approved_by="founder",
        approved_at="2026-10-18T03:01:00+00:00",
    )


def test_workspace_profile_resolves_founder_installed_department():
    profile = get_workspace_department_pilot_profile(
        "acme", "continuity_lab", container_repository=_Containers()
    )
    assert profile is not None
    assert profile["activation_state"] == "enabled"
    assert profile["custom_department"] is True
    assert profile["tool_permissions"]["approved_live_external"] == []


def test_future_department_routes_to_guardian_without_creating_legacy_path(
    monkeypatch, tmp_path
):
    repository, _store = _repository(tmp_path)
    monkeypatch.setattr(
        "backend.modules.aion_business.runtime.central_pilot_department_router.get_workspace_department_pilot_profile",
        lambda workspace_id, department_id: get_workspace_department_pilot_profile(
            workspace_id, department_id, container_repository=_Containers()
        ),
    )
    routed = CentralPilotDepartmentRouter(repository).route_approved_package(
        _package(), routed_at="2026-10-18T03:02:00+00:00"
    )
    assert routed[0].task.department_id == "continuity_lab"
    assert not (tmp_path / "legacy-pilot-runtime").exists()


def test_future_department_action_approval_is_exact_and_does_not_execute(
    monkeypatch, tmp_path
):
    repository, store = _repository(tmp_path)
    monkeypatch.setattr(api, "get_department_pilot_repository", lambda: repository)
    monkeypatch.setattr(
        api,
        "_profile_or_404",
        lambda department_id, workspace_id=None: get_workspace_department_pilot_profile(
            workspace_id or "acme", department_id, container_repository=_Containers()
        ),
    )
    monkeypatch.setattr(
        "backend.modules.aion_business.runtime.central_pilot_department_router.get_workspace_department_pilot_profile",
        lambda workspace_id, department_id: get_workspace_department_pilot_profile(
            workspace_id, department_id, container_repository=_Containers()
        ),
    )
    envelope = CentralPilotDepartmentRouter(repository).route_approved_package(
        _package(), routed_at="2026-10-18T03:02:00+00:00"
    )[0]
    runtime = DepartmentPilotRuntime(repository)
    for index, status in enumerate(("claimed", "running", "waiting_approval"), start=1):
        envelope = runtime.transition(
            workspace_id="acme", department_id="continuity_lab",
            task_id=envelope.task.task_id, to_status=status,
            occurred_at=f"2026-10-18T03:0{index + 2}:00+00:00",
            actor_id="continuity_lab_pilot", event_id=f"event-{index}",
        )

    decided = api.decide_department_action(
        "acme",
        "continuity_lab",
        envelope.task.task_id,
        api.DepartmentActionApprovalRequest(
            tool_call_id="tool-1",
            approval_id="approval-1",
            tool_name="continuity.publish_test_notice",
            provider="internal-sandbox",
            payload={"notice_id": "notice-1", "mode": "dry_run"},
            rationale="Founder review is required before any publication.",
            requested_by="continuity_lab_pilot",
            decided_by="founder",
            approved=True,
            proposed_at="2026-10-18T03:06:00+00:00",
            decided_at="2026-10-18T03:07:00+00:00",
        ),
    )
    assert decided.approvals[0].status == "approved"
    assert decided.approvals[0].decided_payload_hash == decided.proposed_tool_calls[0].payload_hash
    assert decided.proposed_tool_calls[0].tool_mode == "staged_external"
    assert len(store.list("departments.pilot_audit", workspace_id="acme")) == 6
