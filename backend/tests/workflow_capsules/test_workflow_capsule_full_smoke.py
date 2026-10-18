from __future__ import annotations

from pathlib import Path

from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    WorkflowCapsuleRunner,
)
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    WorkflowGlyphRegistry,
)


def test_workflow_capsule_full_gmail_smoke_path() -> None:
    reg = WorkflowGlyphRegistry()
    reg.rebuild_and_save()

    capsule = reg.require("WG-001")

    assert capsule.canonical_key == "workflow:gmail.enquiry_reply.v1"
    assert capsule.display_name == "Handle Gmail Enquiry"
    assert capsule.display_glyph == "WG-001"
    assert capsule.vault_requirements == ["vault.gmail.credentials"]

    runner = WorkflowCapsuleRunner()

    before_checksum = capsule.meta["checksum"]

    dry = runner.run_dry(
        "WG-001",
        inputs={"gmail_message_id": "demo-message-001"},
        available_vault_requirements=[],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_full_smoke_no_learning",
        },
        extra={"pytest": True, "stage": "full_smoke"},
    )

    assert dry.ok is True
    assert dry.canonical_key == "workflow:gmail.enquiry_reply.v1"
    assert dry.run_id
    assert dry.errors == []

    # Expansion locked: compiled workflow glyph resolves to exactly 5 executable steps.
    assert dry.expansion["ok"] is True
    assert len(dry.expansion["steps"]) == 5
    assert dry.expansion["warnings"] == []

    step_ids = [s["step_id"] for s in dry.expansion["steps"]]
    assert step_ids == [
        "read_email",
        "extract_enquiry_intent",
        "draft_reply",
        "approval_checkpoint",
        "send_email_after_approval",
    ]

    # Dry-run/policy locked: external write exists but is blocked until approval + vault.
    assert dry.run["approval_required"] is True
    assert dry.run["external_writes_blocked"] is True
    assert dry.policy["external_writes_present"] is True
    assert dry.policy["external_writes_allowed_now"] is False
    assert "vault.gmail.credentials" in dry.policy["missing_vault_requirements"]

    blocked_step_ids = {s["step_id"] for s in dry.policy["blocked_steps"]}
    assert "read_email" in blocked_step_ids
    assert "send_email_after_approval" in blocked_step_ids

    # Approval request is created during dry-run.
    assert dry.approval["ok"] is True
    assert dry.approval["status"] == "pending"
    assert dry.approval["canonical_key"] == "workflow:gmail.enquiry_reply.v1"
    approval_id = dry.approval["approval_id"]

    approved = runner.approve(
        approval_id,
        decided_by="pytest",
        reason="Full smoke approval for connector-ready resume.",
    )

    assert approved["ok"] is True
    assert approved["status"] == "approved"
    assert approved["decision"] == "approved"

    ready = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_full_smoke_no_learning",
        },
    )

    assert ready["ok"] is True
    assert ready["phase"] == "resume_after_approval"
    assert ready["canonical_key"] == "workflow:gmail.enquiry_reply.v1"
    assert ready["executed_external_step"] == "send_email_after_approval"
    assert ready["status"] == "simulated_external_write_ready"

    connector = ready["connector_result"]
    assert connector["ok"] is True
    assert connector["connector"] == "gmail"
    assert connector["action"] == "external_write_ready"
    assert connector["status"] == "simulated_external_write_ready"
    assert connector["payload"]["ready"] is True
    assert "Real Gmail send is intentionally not wired" in connector["payload"]["message"]

    # Trace is written to runtime, not capsule source directory.
    assert dry.trace["ok"] is True
    trace_path = Path(dry.trace["path"])
    assert trace_path.exists()
    assert str(trace_path).startswith(".runtime/workflow_capsules/runs/")
    assert dry.trace["event_type"] == "workflow_runner_dry_run_completed"
    assert dry.trace["canonical_key"] == "workflow:gmail.enquiry_reply.v1"
    assert dry.trace["run_id"] == dry.run_id
    assert dry.trace["trace_hash"]

    # Feedback is written, but CAU deny prevents capsule mutation/reinforcement.
    assert dry.feedback["ok"] is True
    feedback_path = Path(dry.feedback["path"])
    assert feedback_path.exists()
    assert str(feedback_path).startswith(".runtime/workflow_capsules/feedback/")
    assert dry.feedback["mutation_allowed"] is False
    assert dry.feedback["mutation_applied"] is False
    assert dry.feedback["quality"] >= 0.0
    assert dry.feedback["feedback_hash"]

    reloaded = reg.require("WG-001")
    assert reloaded.meta["checksum"] == before_checksum
    assert reloaded.meta.get("sqi_score", 0.0) == 0.0
