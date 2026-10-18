from __future__ import annotations

from types import SimpleNamespace

from backend.modules.aion_business.runtime.business_vault import (
    provision_business_vault,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.workflow_capsules.approval.workflow_capsule_approval_store import (
    WorkflowCapsuleApprovalStore,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_trace import (
    WorkflowCapsuleTraceWriter,
)


def test_capsule_approvals_and_execution_traces_are_vault_records(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"r" * 32),
        actor_id="workflow-capsule-runtime-test",
    )
    retained_runtime = tmp_path / "replaceable-runtime"
    approvals = WorkflowCapsuleApprovalStore(
        domain_store=store,
        workspace_id="acme",
    )

    created = approvals.create(
        run_id="run_private_1",
        canonical_key="workflow:private.customer.follow_up.v1",
        display_name="Private customer follow-up",
        reason="Founder must approve the private customer message",
        payload={"customer": "Private Client", "email": "private@example.test"},
    )
    assert created["path"].startswith(
        "vault://train_agent.runs_and_audit/workflow_capsule_approvals/"
    )
    assert approvals.get(created["approval_id"])["status"] == "pending"
    assert [item["approval_id"] for item in approvals.list(status="pending")] == [
        created["approval_id"]
    ]

    decision = approvals.decide(
        created["approval_id"],
        decision="approved",
        decided_by="founder",
        reason="Approved for this customer",
    )
    assert decision["status"] == "approved"

    capsule = SimpleNamespace(
        canonical_key="workflow:private.customer.follow_up.v1",
        display_name="Private customer follow-up",
        meta={"checksum": "capsule-checksum"},
    )
    trace = WorkflowCapsuleTraceWriter(
        domain_store=store,
        workspace_id="acme",
    ).append(
        event_type="workflow_completed",
        capsule=capsule,
        run_result={
            "run_id": "run_private_1",
            "customer": "Private Client",
            "result": "Email prepared",
        },
        cau_state={"allow_learn": True, "adr_active": False},
    )
    assert trace["path"].startswith(
        "vault://train_agent.runs_and_audit/workflow_capsule_traces/"
    )

    restarted = WorkflowCapsuleApprovalStore(
        domain_store=store,
        workspace_id="acme",
    )
    assert restarted.get(created["approval_id"])["decision"] == "approved"
    assert restarted.list(status="approved")[0]["decided_by"] == "founder"
    assert not retained_runtime.exists()

    records = store.list("train_agent.runs_and_audit", workspace_id="acme")
    entity_ids = {str(record["entity_id"]) for record in records}
    assert any("workflow_capsule_approvals/" in item for item in entity_ids)
    assert sum("workflow_capsule_approval_events/" in item for item in entity_ids) == 2
    assert any("workflow_capsule_traces/" in item for item in entity_ids)
    assert store.guardian.verify_audit_chain()["healthy"] is True

    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private Client" not in database_bytes
    assert b"private@example.test" not in database_bytes
    assert b"Approved for this customer" not in database_bytes

