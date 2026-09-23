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


def _compile_capsule(
    *,
    permission_mode: str = "auto_with_exceptions",
    recipient_scope: str = "original_thread_only",
    auto_sends_today: int = 0,
    max_auto_sends_per_day: int = 3,
    confidence: float = 0.95,
    risk_flags: list[str] | None = None,
):
    canvas = {
        "canonical_key": "workflow:runner.runtime_limits.v1",
        "display_name": "Runner Runtime Limits",
        "meaning": "Tests runner-level propagation of permission runtime limits.",
        "display_glyph": "RUNTIME-LIMITS-001",
        "tags": ["permission", "runtime", "limits"],
        "vault_requirements": ["vault.gmail.credentials"],
        "permission_mode": permission_mode,
        "nodes": [
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
                        "confidence": confidence,
                        "risk_flags": risk_flags or [],
                        "metadata": {
                            "recipient_scope": recipient_scope,
                            "auto_sends_today": auto_sends_today,
                        },
                    },
                    "limits": {
                        "max_auto_sends_per_day": max_auto_sends_per_day,
                        "allowed_recipient_scope": "original_thread_only",
                    },
                    "output_ref": "send.output",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "draft", "target": "send"},
        ],
    }

    compiled = CanvasWorkflowCompiler().compile(canvas)
    assert compiled.ok is True
    assert compiled.capsule is not None
    return compiled.capsule


def _dry(capsule):
    expansion = WorkflowCapsuleExpander().expand(capsule)
    assert expansion.ok is True

    return WorkflowCapsuleDryRunExecutor().run(
        capsule,
        expansion,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_runner_runtime_limits_no_learning",
        },
        inputs={"gmail_message_id": "pytest-runtime-limits-msg"},
    )


def test_runner_step_permission_audit_receives_limit_metadata() -> None:
    dry = _dry(
        _compile_capsule(
            auto_sends_today=1,
            max_auto_sends_per_day=3,
            recipient_scope="original_thread_only",
        )
    )

    send = {step.step_id: step for step in dry.steps}["send"]
    permission = send.preview["permission"]
    audit = permission["audit"]

    assert permission["decision"] == "auto_run"
    assert audit["auto_sends_today"] == 1
    assert audit["max_auto_sends_per_day"] == 3
    assert audit["recipient_scope"] == "original_thread_only"
    assert audit["allowed_recipient_scope"] == "original_thread_only"


def test_runner_step_permission_pauses_when_auto_send_limit_reached() -> None:
    dry = _dry(
        _compile_capsule(
            auto_sends_today=3,
            max_auto_sends_per_day=3,
        )
    )

    send = {step.step_id: step for step in dry.steps}["send"]
    permission = send.preview["permission"]

    assert permission["decision"] == "request_approval"
    assert permission["requires_approval"] is True
    assert permission["reason"] == "auto_send_daily_limit_reached"
    assert dry.approval_required is True


def test_runner_step_permission_pauses_when_recipient_scope_changes() -> None:
    dry = _dry(
        _compile_capsule(
            recipient_scope="new_external_recipient",
        )
    )

    send = {step.step_id: step for step in dry.steps}["send"]
    permission = send.preview["permission"]

    assert permission["decision"] == "request_approval"
    assert permission["requires_approval"] is True
    assert permission["reason"] == "recipient_scope_requires_approval"
    assert dry.approval_required is True


def test_runner_step_permission_pauses_when_step_confidence_low() -> None:
    dry = _dry(
        _compile_capsule(
            confidence=0.42,
        )
    )

    send = {step.step_id: step for step in dry.steps}["send"]
    permission = send.preview["permission"]

    assert permission["decision"] == "request_approval"
    assert permission["requires_approval"] is True
    assert permission["reason"] == "confidence_below_policy_threshold"
    assert dry.approval_required is True


def test_runner_step_permission_pauses_on_risk_flags() -> None:
    dry = _dry(
        _compile_capsule(
            risk_flags=["complaint", "refund_request"],
        )
    )

    send = {step.step_id: step for step in dry.steps}["send"]
    permission = send.preview["permission"]

    assert permission["decision"] == "request_approval"
    assert permission["requires_approval"] is True
    assert permission["reason"] == "risk_flags_require_approval"
    assert permission["audit"]["risk_flags"] == ["complaint", "refund_request"]
    assert dry.approval_required is True
