from __future__ import annotations

from backend.modules.workflow_capsules.approval.workflow_capsule_approval_store import (
    WorkflowCapsuleApprovalStore,
)


def test_workflow_capsule_approval_payload_contains_boardroom_hydration_fields(tmp_path) -> None:
    store = WorkflowCapsuleApprovalStore(
        approval_dir=tmp_path / "approvals" / "items",
        approval_log=tmp_path / "approvals" / "workflow_approvals.jsonl",
    )

    created = store.create(
        run_id="wf_dry_demo_001",
        canonical_key="workflow:electrician.gmail_receptionist.v1",
        display_name="Electrician Gmail Receptionist",
        reason="External write requires approval.",
        external_write_step_id="send_email",
        approval_ref="approval.result",
        payload={
            "workflow_id": "workflow:electrician.gmail_receptionist.v1",
            "node_id": "send_email",
            "agent_id": "agent.receptionist.v1",
            "permission_decision": "request_approval",
            "risk_tier": "medium",
            "vault_requirements": ["vault.gmail.credentials"],
            "connector_handles": ["connector.gmail.default"],
            "dry_run_preview": {
                "subject": "Re: your enquiry",
                "body": "Draft reply preview would be generated here for human review.",
            },
            "blocked_writes": [
                {
                    "step_id": "send_email",
                    "reason": "dry_run_blocks_external_write",
                }
            ],
        },
        meta={
            "source": "workflow_capsule_runner",
            "boardroom_visible": True,
        },
    )

    assert created["ok"] is True

    item = store.get(created["approval_id"])
    assert item is not None

    assert item["approval_id"] == created["approval_id"]
    assert item["run_id"] == "wf_dry_demo_001"
    assert item["canonical_key"] == "workflow:electrician.gmail_receptionist.v1"
    assert item["display_name"] == "Electrician Gmail Receptionist"
    assert item["status"] == "pending"
    assert item["external_write_step_id"] == "send_email"

    payload = item["payload"]
    assert payload["workflow_id"] == "workflow:electrician.gmail_receptionist.v1"
    assert payload["node_id"] == "send_email"
    assert payload["agent_id"] == "agent.receptionist.v1"
    assert payload["permission_decision"] == "request_approval"
    assert payload["risk_tier"] == "medium"
    assert payload["vault_requirements"] == ["vault.gmail.credentials"]
    assert payload["connector_handles"] == ["connector.gmail.default"]
    assert payload["dry_run_preview"]["subject"] == "Re: your enquiry"
    assert payload["blocked_writes"][0]["reason"] == "dry_run_blocks_external_write"

    assert item["meta"]["boardroom_visible"] is True


def test_workflow_capsule_approval_list_returns_pending_boardroom_items(tmp_path) -> None:
    store = WorkflowCapsuleApprovalStore(
        approval_dir=tmp_path / "approvals" / "items",
        approval_log=tmp_path / "approvals" / "workflow_approvals.jsonl",
    )

    pending = store.create(
        run_id="wf_dry_pending_001",
        canonical_key="workflow:electrician.gmail_receptionist.v1",
        display_name="Electrician Gmail Receptionist",
        reason="External write requires approval.",
        external_write_step_id="send_email",
        payload={
            "permission_decision": "request_approval",
            "risk_tier": "medium",
            "vault_requirements": ["vault.gmail.credentials"],
            "dry_run_preview": {"body": "Pending preview"},
        },
        meta={"boardroom_visible": True},
    )

    rejected = store.create(
        run_id="wf_dry_rejected_001",
        canonical_key="workflow:electrician.gmail_receptionist.v1",
        display_name="Electrician Gmail Receptionist",
        reason="External write requires approval.",
        external_write_step_id="send_email",
        payload={
            "permission_decision": "request_approval",
            "risk_tier": "medium",
            "vault_requirements": ["vault.gmail.credentials"],
            "dry_run_preview": {"body": "Rejected preview"},
        },
        meta={"boardroom_visible": True},
    )

    store.decide(
        rejected["approval_id"],
        decision="rejected",
        decided_by="pytest",
        reason="not suitable",
    )

    items = store.list(status="pending", canonical_key="workflow:electrician.gmail_receptionist.v1")

    assert len(items) == 1
    assert items[0]["approval_id"] == pending["approval_id"]
    assert items[0]["status"] == "pending"
    assert items[0]["payload"]["risk_tier"] == "medium"
    assert items[0]["payload"]["vault_requirements"] == ["vault.gmail.credentials"]


def test_workflow_capsule_approval_payload_never_requires_live_execute_for_boardroom(tmp_path) -> None:
    store = WorkflowCapsuleApprovalStore(
        approval_dir=tmp_path / "approvals" / "items",
        approval_log=tmp_path / "approvals" / "workflow_approvals.jsonl",
    )

    created = store.create(
        run_id="wf_dry_demo_002",
        canonical_key="workflow:electrician.gmail_receptionist.v1",
        display_name="Electrician Gmail Receptionist",
        reason="External write requires approval.",
        external_write_step_id="send_email",
        payload={
            "permission_decision": "request_approval",
            "risk_tier": "medium",
            "resume_mode": "connector_ready",
            "vault_requirements": ["vault.gmail.credentials"],
            "dry_run_preview": {"body": "Preview only"},
        },
        meta={"boardroom_visible": True},
    )

    item = store.get(created["approval_id"])
    text = str(item).lower()

    assert "connector_ready" in text
    assert "live_execute" not in text
    assert "send_message" not in text
    assert "gmail_live_send" not in text
