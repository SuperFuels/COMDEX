from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.guardian_business_container_repository import (
    GuardianBusinessContainerRepository,
)
from backend.modules.aion_business.runtime.pilot_operating_team_service import (
    PilotOperatingTeamService,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_train_agent_state_audit_and_future_department_are_vault_records(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"t" * 32)
    store = VaultDomainStore(guardian)
    service = PilotOperatingTeamService(
        domain_store=store,
        container_repository=GuardianBusinessContainerRepository(guardian),
        workflow_cabinet_loader=lambda _workspace: {"folders": []},
    )
    result = service.bootstrap_workspace(
        "acme", departments=["finance", "future_department"]
    )
    assert {row["department_id"] for row in result["capsules"]} == {
        "finance", "future_department"
    }
    assert all(row["workspace_path"].startswith("guardian://") for row in result["capsules"])
    service.transfer_control(
        "acme",
        "future_department",
        control_state="human",
        controller_id="person:founder",
        reason="Review future department setup",
    )
    workflow_tabs = {
        "active_id": "future-department-automation",
        "tabs": [{
            "id": "future-department-automation",
            "graph": {"nodes": [{"id": "private-procedure"}], "edges": []},
        }],
    }
    service.save_workspace_state(
        "acme",
        "workflow-tabs",
        payload=workflow_tabs,
        saved_by="person:founder",
    )
    restarted = PilotOperatingTeamService(
        domain_store=store,
        container_repository=GuardianBusinessContainerRepository(guardian),
        workflow_cabinet_loader=lambda _workspace: {"folders": []},
    )
    workspace = restarted.workspace("acme")
    capsule = next(row for row in workspace["capsules"] if row["department_id"] == "future_department")
    assert capsule["control_state"] == "human"
    assert restarted.workspace_state("acme", "workflow-tabs")["payload"] == workflow_tabs
    assert workspace["audit"]["ok"] is True
    assert workspace["audit"]["count"] == 3
    assert b"Review future department setup" not in guardian.database.read_bytes()
    assert b"private-procedure" not in guardian.database.read_bytes()


def test_future_department_can_own_trained_skills_routines_and_action_evidence(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"u" * 32)
    store = VaultDomainStore(guardian)
    service = PilotOperatingTeamService(
        domain_store=store,
        container_repository=GuardianBusinessContainerRepository(guardian),
        workflow_cabinet_loader=lambda _workspace: {"folders": []},
    )
    service.bootstrap_workspace("acme", departments=["procurement"])
    skill = service.create_demonstrated_skill(
        "acme",
        name="Prepare supplier comparison",
        department_id="procurement",
        outcome="A reviewed supplier comparison is placed in the department cabinet.",
        observed_steps=[{"event": "click", "target": {"role": "button", "name": "Compare"}}],
        created_by="person:founder",
    )
    routine = service.create_routine(
        "acme",
        title="Weekly supplier comparison",
        department_id="procurement",
        owner_id="person:founder",
        event_trigger={"event": "supplier_quotes_ready"},
        input_source="procurement supplier records",
        expected_result="Reviewed comparison saved to the File Cabinet",
    )
    decision = service.preflight_action(
        "acme",
        department_id="procurement",
        initiator={"type": "pilot", "id": "procurement-pilot"},
        action_type="publish",
        target={"type": "file_cabinet", "folder": "procurement"},
        payload={"document": "private supplier comparison"},
        registered_capability=True,
    )

    assert skill["department_id"] == routine["department_id"] == "procurement"
    assert decision["department_id"] == "procurement"
    assert decision["approval_required"] is True
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id=f"skills/{skill['skill_id']}",
    )["payload"]["outcome"].startswith("A reviewed supplier")
    assert b"private supplier comparison" not in guardian.database.read_bytes()


def test_train_agent_rejects_department_identity_that_can_escape_its_vault_namespace(tmp_path):
    service = PilotOperatingTeamService(base_dir=tmp_path)
    with pytest.raises(ValueError, match="invalid_department_id"):
        service.bootstrap_workspace("acme", departments=["../another-business"])
