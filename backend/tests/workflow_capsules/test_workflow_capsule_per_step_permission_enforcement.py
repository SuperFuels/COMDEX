from __future__ import annotations

from backend.modules.workflow_capsules.canvas.canvas_workflow_compiler import (
    CanvasWorkflowCompiler,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_expander import (
    WorkflowCapsuleExpander,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_dry_run import (
    WorkflowCapsuleDryRunExecutor,
)


def _compile_permission_canvas(permission_mode: str = "auto_with_exceptions"):
    canvas = {
        "canonical_key": "workflow:permission.per_step_demo.v1",
        "display_name": "Per-Step Permission Demo",
        "meaning": "Tests per-step permission enforcement before runtime execution.",
        "display_glyph": "PERM-STEP-001",
        "tags": ["permission", "runtime", "per-step"],
        "vault_requirements": ["vault.gmail.credentials"],
        "permission_mode": permission_mode,
        "nodes": [
            {
                "id": "read",
                "type": "read_email",
                "data": {
                    "step_id": "read",
                    "kind": "read_email",
                    "label": "Read email",
                    "connector": "gmail",
                    "requires": ["vault.gmail.credentials"],
                    "permission": {
                        "mode": permission_mode,
                        "risk_tier": "low",
                        "action": "read_email",
                    },
                    "output_ref": "read.output",
                },
            },
            {
                "id": "draft",
                "type": "draft_content",
                "data": {
                    "step_id": "draft",
                    "kind": "draft_content",
                    "label": "Draft reply",
                    "permission": {
                        "mode": permission_mode,
                        "risk_tier": "low",
                        "action": "draft_content",
                    },
                    "output_ref": "draft.output",
                },
            },
            {
                "id": "send",
                "type": "send_email",
                "data": {
                    "step_id": "send",
                    "kind": "send_email",
                    "label": "Send reply",
                    "connector": "gmail",
                    "external_write": True,
                    "requires_approval": True,
                    "permission": {
                        "mode": permission_mode,
                        "risk_tier": "medium",
                        "action": "send_email",
                    },
                    "output_ref": "send.output",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "read", "target": "draft"},
            {"id": "e2", "source": "draft", "target": "send"},
        ],
    }

    compiled = CanvasWorkflowCompiler().compile(canvas)
    assert compiled.ok is True
    assert compiled.capsule is not None
    return compiled.capsule


def _dry_run(permission_mode: str):
    capsule = _compile_permission_canvas(permission_mode)
    expansion = WorkflowCapsuleExpander().expand(capsule)
    assert expansion.ok is True

    return WorkflowCapsuleDryRunExecutor().run(
        capsule,
        expansion,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_per_step_permission_no_learning",
        },
        inputs={"gmail_message_id": "pytest-per-step-msg-001"},
    )


def test_per_step_permission_metadata_is_attached_to_each_dry_run_step() -> None:
    dry = _dry_run("auto_with_exceptions")
    by_id = {step.step_id: step for step in dry.steps}

    assert by_id["read"].preview["permission"]["decision"] == "auto_run"
    assert by_id["draft"].preview["permission"]["decision"] == "auto_run"
    assert by_id["send"].preview["permission"]["decision"] in {
        "auto_run",
        "request_approval",
    }

    assert by_id["send"].preview["permission"]["audit"]["risk_tier"] == "medium"
    assert by_id["send"].preview["permission"]["audit"]["is_external_write"] is True


def test_review_mode_requests_approval_for_external_write_step() -> None:
    dry = _dry_run("review")
    by_id = {step.step_id: step for step in dry.steps}

    assert by_id["draft"].preview["permission"]["decision"] == "draft_only"
    assert by_id["send"].preview["permission"]["decision"] == "request_approval"
    assert by_id["send"].preview["permission"]["requires_approval"] is True
    assert by_id["send"].status == "blocked"


def test_draft_auto_allows_draft_but_not_send() -> None:
    dry = _dry_run("draft_auto")
    by_id = {step.step_id: step for step in dry.steps}

    assert by_id["draft"].preview["permission"]["decision"] == "draft_only"
    assert by_id["send"].preview["permission"]["decision"] == "request_approval"
    assert by_id["send"].status == "blocked"


def test_manual_only_requests_approval_for_all_steps() -> None:
    dry = _dry_run("manual_only")

    for step in dry.steps:
        assert step.preview["permission"]["decision"] == "request_approval"
        assert step.preview["permission"]["requires_approval"] is True


def test_blocked_risk_step_is_blocked_by_permission_layer() -> None:
    capsule = _compile_permission_canvas("auto_with_exceptions")
    capsule.compiled_glyph["steps"][-1]["permission"]["risk_tier"] = "blocked"

    expansion = WorkflowCapsuleExpander().expand(capsule)
    dry = WorkflowCapsuleDryRunExecutor().run(
        capsule,
        expansion,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_per_step_permission_no_learning",
        },
        inputs={"gmail_message_id": "pytest-per-step-msg-001"},
    )

    by_id = {step.step_id: step for step in dry.steps}

    assert by_id["send"].preview["permission"]["decision"] == "block"
    assert by_id["send"].status == "blocked"
    assert "permission_blocked" in by_id["send"].blocked_reasons
