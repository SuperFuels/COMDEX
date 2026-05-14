from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.workflow_capsules.permissions.permission_modes import RiskTier
from backend.modules.workflow_capsules.permissions.permission_policy import (
    PermissionEvaluationContext,
)


def infer_action_from_step(step: Dict[str, Any]) -> str:
    kind = str(step.get("kind") or "").strip()
    connector = str(step.get("connector") or "").strip()

    explicit = str(step.get("action") or "").strip()
    if explicit:
        return explicit

    if connector == "gmail" and kind in {"read_email", "read_message"}:
        return "gmail.read"

    if connector == "gmail" and kind in {"create_draft", "draft_email"}:
        return "gmail.create_draft"

    if connector == "gmail" and kind in {"send_email", "send_message"}:
        return "gmail.send"

    if kind in {"draft_content", "draft_reply"}:
        return "content.draft"

    if kind == "approval_checkpoint":
        return "approval.checkpoint"

    return kind or "unknown.action"


def infer_risk_tier_from_step(step: Dict[str, Any]) -> RiskTier:
    raw = step.get("risk_tier") or (step.get("permission") or {}).get("risk_tier")
    if raw:
        try:
            return RiskTier(str(raw))
        except Exception:
            return RiskTier.HIGH

    kind = str(step.get("kind") or "").strip()

    if kind in {"read_email", "read_message", "classify", "summarize", "draft_content", "draft_reply"}:
        return RiskTier.LOW

    if kind in {"create_draft", "approval_checkpoint"}:
        return RiskTier.LOW

    if kind in {"send_email", "send_message", "post_social", "update_crm", "schedule_appointment"}:
        return RiskTier.MEDIUM

    if kind in {"refund", "discount", "contract_change", "price_change", "legal_statement", "financial_statement"}:
        return RiskTier.HIGH

    if kind in {"payment", "bank_write", "xero_write", "delete_data", "credential_change"}:
        return RiskTier.BLOCKED

    return RiskTier.LOW


def permission_context_from_step(
    step: Dict[str, Any],
    *,
    workspace_id: str = "",
    agent_id: str = "",
    workflow_id: str = "",
    execution_mode: str = "dry_run",
) -> PermissionEvaluationContext:
    permission = step.get("permission") if isinstance(step.get("permission"), dict) else {}

    is_external_write = bool(
        step.get("external_write")
        or permission.get("is_external_write")
        or str(step.get("kind") or "") in {"send_email", "send_message", "post_social", "update_crm"}
    )

    is_draft_action = bool(
        permission.get("is_draft_action")
        or str(step.get("kind") or "") in {"draft_content", "draft_reply", "create_draft", "draft_email"}
    )

    return PermissionEvaluationContext(
        workspace_id=workspace_id,
        agent_id=agent_id or str(step.get("agent_id") or ""),
        workflow_id=workflow_id,
        node_id=str(step.get("id") or step.get("step_id") or ""),
        action=infer_action_from_step(step),
        connector=step.get("connector"),
        risk_tier=infer_risk_tier_from_step(step),
        is_external_write=is_external_write,
        is_draft_action=is_draft_action,
        requires_approval=bool(step.get("requires_approval") or permission.get("requires_approval")),
        confidence=step.get("confidence"),
        risk_flags=list(step.get("risk_flags") or permission.get("risk_flags") or []),
        execution_mode=execution_mode,
        metadata={
            "step_kind": step.get("kind"),
            "permission_mode": step.get("permission_mode") or permission.get("node_mode"),
        },
    )
