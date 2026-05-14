from __future__ import annotations

from backend.modules.workflow_capsules.permissions.permission_modes import RiskTier
from backend.modules.workflow_capsules.permissions.workflow_step_permission import (
    infer_action_from_step,
    infer_risk_tier_from_step,
    permission_context_from_step,
)


def test_infers_gmail_read_action_from_step() -> None:
    step = {
        "id": "read",
        "kind": "read_email",
        "connector": "gmail",
    }

    assert infer_action_from_step(step) == "gmail.read"
    assert infer_risk_tier_from_step(step) == RiskTier.LOW


def test_infers_gmail_send_as_medium_external_write() -> None:
    step = {
        "id": "send",
        "kind": "send_email",
        "connector": "gmail",
        "requires_approval": True,
        "external_write": True,
    }

    ctx = permission_context_from_step(
        step,
        workspace_id="costa-conexion",
        agent_id="agent.receptionist.v1",
        workflow_id="workflow:electrician.gmail_receptionist.v1",
        execution_mode="connector_ready",
    )

    assert ctx.workspace_id == "costa-conexion"
    assert ctx.agent_id == "agent.receptionist.v1"
    assert ctx.workflow_id == "workflow:electrician.gmail_receptionist.v1"
    assert ctx.node_id == "send"
    assert ctx.action == "gmail.send"
    assert ctx.risk_tier == RiskTier.MEDIUM
    assert ctx.is_external_write is True
    assert ctx.requires_approval is True
    assert ctx.execution_mode == "connector_ready"


def test_explicit_step_permission_metadata_overrides_inference() -> None:
    step = {
        "id": "send",
        "kind": "send_email",
        "connector": "gmail",
        "action": "gmail.send_low_risk_reply",
        "permission_mode": "auto_with_exceptions",
        "risk_tier": "low",
        "permission": {
            "node_mode": "auto_with_exceptions",
            "is_external_write": True,
            "requires_approval": False,
        },
        "confidence": 0.94,
        "risk_flags": [],
    }

    ctx = permission_context_from_step(step)

    assert ctx.action == "gmail.send_low_risk_reply"
    assert ctx.risk_tier == RiskTier.LOW
    assert ctx.is_external_write is True
    assert ctx.requires_approval is False
    assert ctx.confidence == 0.94
    assert ctx.metadata["permission_mode"] == "auto_with_exceptions"


def test_blocked_action_maps_to_blocked_risk() -> None:
    step = {
        "id": "payment",
        "kind": "payment",
    }

    ctx = permission_context_from_step(step)

    assert ctx.action == "payment"
    assert ctx.risk_tier == RiskTier.BLOCKED
