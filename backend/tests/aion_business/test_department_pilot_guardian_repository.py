from __future__ import annotations

from backend.modules.aion_business.contracts.department_pilot import BoardroomAssignmentAction
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    approve_assignment_package,
    create_assignment_package,
    create_provenance,
    create_task_from_package,
    create_work_envelope,
)
from backend.modules.aion_business.runtime.department_pilot_repository import (
    DepartmentPilotRepository,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _envelope():
    provenance = create_provenance(
        created_by="boardroom", created_at="2026-10-17T00:00:00+00:00"
    )
    package = create_assignment_package(
        package_id="pkg-1",
        workspace_id="acme",
        business_id="acme",
        boardroom_session_id="session-1",
        boardroom_decision_id="decision-1",
        title="New department task",
        objective="Retain this task across every update.",
        department_id="future_department",
        actions=[
            BoardroomAssignmentAction(
                action_id="action-1",
                title="Prepare record",
                objective="Prepare the governed record.",
                department_id="future_department",
                capability="records.prepare",
                acceptance_criteria=["Record remains in Business Vault"],
            )
        ],
        provenance=provenance,
    )
    package = approve_assignment_package(
        package,
        approval_id="approval-1",
        approved_by="founder",
        approved_at="2026-10-17T00:01:00+00:00",
    )
    task = create_task_from_package(
        package,
        action_id="action-1",
        task_id="task-1",
        pilot_id="future-department-pilot",
        assigned_at="2026-10-17T00:02:00+00:00",
        provenance=provenance,
    )
    return create_work_envelope(package=package, task=task)


def test_department_pilot_uses_guardian_for_current_or_future_department(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"d" * 32)
    store = VaultDomainStore(guardian)
    repository = DepartmentPilotRepository(domain_store=store)
    envelope = _envelope()
    uri = repository.create(envelope)
    assert uri.startswith("guardian://department_pilot_tasks/")
    assert repository.load("acme", "future_department", "task-1").envelope_hash == envelope.envelope_hash
    assert len(repository.list_for_department("acme", "future_department")) == 1
    assert len(store.list("departments.pilot_audit", workspace_id="acme")) == 1
    assert b"Retain this task across every update" not in guardian.database.read_bytes()
