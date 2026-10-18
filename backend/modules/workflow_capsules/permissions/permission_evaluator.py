from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.modules.workflow_capsules.permissions.permission_modes import (
    PermissionDecision,
    PermissionMode,
    RiskTier,
)
from backend.modules.workflow_capsules.permissions.permission_policy import (
    AgentPermissionProfile,
    PermissionEvaluationContext,
    WorkflowPermissionPolicy,
)


@dataclass
class PermissionEvaluationResult:
    ok: bool
    decision: PermissionDecision
    reason: str
    requires_approval: bool = False
    audit: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "decision": self.decision.value if isinstance(self.decision, PermissionDecision) else self.decision,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
            "audit": self.audit,
            "errors": list(self.errors),
        }


class PermissionEvaluator:
    """
    Guardrail evaluator for AION workflow autonomy.

    Core rule:
      agents may request or run allowed actions, but they never self-authorise
      external writes. External writes require policy, connector/vault/runtime
      guards, and either approval or an explicit bounded auto mode.
    """

    def evaluate(
        self,
        *,
        policy: WorkflowPermissionPolicy,
        agent: AgentPermissionProfile,
        context: PermissionEvaluationContext,
    ) -> PermissionEvaluationResult:
        action = str(context.action or "").strip()
        risk = context.risk_tier
        mode = policy.mode

        metadata = context.metadata if isinstance(context.metadata, dict) else {}

        auto_sends_today = int(metadata.get("auto_sends_today") or 0)
        max_auto_sends_per_day = int(policy.max_auto_sends_per_day or 0)

        recipient_scope = str(
            metadata.get("recipient_scope") or policy.allowed_recipient_scope or ""
        ).strip()
        allowed_recipient_scope = str(policy.allowed_recipient_scope or "").strip()

        audit = {
            "workspace_id": context.workspace_id,
            "agent_id": context.agent_id or agent.agent_id,
            "workflow_id": context.workflow_id or policy.workflow_id,
            "node_id": context.node_id,
            "action": action,
            "connector": context.connector,
            "risk_tier": risk.value if isinstance(risk, RiskTier) else risk,
            "mode": mode.value if isinstance(mode, PermissionMode) else mode,
            "execution_mode": context.execution_mode,
            "is_external_write": bool(context.is_external_write),
            "is_draft_action": bool(context.is_draft_action),
            "risk_flags": list(context.risk_flags or []),
            "auto_sends_today": auto_sends_today,
            "max_auto_sends_per_day": max_auto_sends_per_day,
            "recipient_scope": recipient_scope,
            "allowed_recipient_scope": allowed_recipient_scope,
        }

        if mode == PermissionMode.MANUAL_ONLY:
            return PermissionEvaluationResult(
                ok=True,
                decision=PermissionDecision.REQUEST_APPROVAL,
                reason="manual_only_mode_requires_approval",
                requires_approval=True,
                audit=audit,
            )

        if risk == RiskTier.BLOCKED:
            return PermissionEvaluationResult(
                ok=False,
                decision=PermissionDecision.BLOCK,
                reason="risk_tier_blocked",
                audit=audit,
                errors=["risk_tier_blocked"],
            )

        if action in set(policy.blocked_actions or []) or action in set(agent.blocked_actions or []):
            return PermissionEvaluationResult(
                ok=False,
                decision=PermissionDecision.BLOCK,
                reason="action_blocked_by_policy_or_agent",
                audit=audit,
                errors=["action_blocked"],
            )

        if agent.allowed_actions and action not in set(agent.allowed_actions):
            return PermissionEvaluationResult(
                ok=False,
                decision=PermissionDecision.BLOCK,
                reason="action_not_allowed_for_agent",
                audit=audit,
                errors=["agent_action_not_allowed"],
            )

        if policy.allowed_actions and action not in set(policy.allowed_actions):
            return PermissionEvaluationResult(
                ok=False,
                decision=PermissionDecision.BLOCK,
                reason="action_not_allowed_for_workflow",
                audit=audit,
                errors=["workflow_action_not_allowed"],
            )

        if context.confidence is not None and context.confidence < policy.min_confidence:
            return PermissionEvaluationResult(
                ok=True,
                decision=PermissionDecision.REQUEST_APPROVAL,
                reason="confidence_below_policy_threshold",
                requires_approval=True,
                audit=audit,
            )

        if context.risk_flags:
            return PermissionEvaluationResult(
                ok=True,
                decision=PermissionDecision.REQUEST_APPROVAL,
                reason="risk_flags_require_approval",
                requires_approval=True,
                audit=audit,
            )

        if (
            context.is_external_write
            and not context.is_draft_action
            and max_auto_sends_per_day > 0
            and auto_sends_today >= max_auto_sends_per_day
        ):
            return PermissionEvaluationResult(
                ok=True,
                decision=PermissionDecision.REQUEST_APPROVAL,
                reason="auto_send_daily_limit_reached",
                requires_approval=True,
                audit=audit,
            )

        if (
            context.is_external_write
            and not context.is_draft_action
            and allowed_recipient_scope
            and recipient_scope
            and recipient_scope != allowed_recipient_scope
        ):
            return PermissionEvaluationResult(
                ok=True,
                decision=PermissionDecision.REQUEST_APPROVAL,
                reason="recipient_scope_requires_approval",
                requires_approval=True,
                audit=audit,
            )

        if risk == RiskTier.HIGH:
            return PermissionEvaluationResult(
                ok=True,
                decision=PermissionDecision.REQUEST_APPROVAL,
                reason="high_risk_requires_approval",
                requires_approval=True,
                audit=audit,
            )

        if context.is_external_write and agent.can_self_authorise_external_writes:
            return PermissionEvaluationResult(
                ok=False,
                decision=PermissionDecision.BLOCK,
                reason="agent_self_authorisation_for_external_write_forbidden",
                audit=audit,
                errors=["agent_self_authorisation_forbidden"],
            )

        if mode == PermissionMode.REVIEW:
            if context.is_draft_action:
                return PermissionEvaluationResult(
                    ok=True,
                    decision=PermissionDecision.DRAFT_ONLY,
                    reason="review_mode_allows_draft_only",
                    audit=audit,
                )

            return PermissionEvaluationResult(
                ok=True,
                decision=PermissionDecision.REQUEST_APPROVAL,
                reason="review_mode_requires_approval",
                requires_approval=True,
                audit=audit,
            )

        if mode == PermissionMode.DRAFT_AUTO:
            if context.is_draft_action:
                return PermissionEvaluationResult(
                    ok=True,
                    decision=PermissionDecision.DRAFT_ONLY,
                    reason="draft_auto_mode_allows_draft",
                    audit=audit,
                )

            if context.is_external_write:
                return PermissionEvaluationResult(
                    ok=True,
                    decision=PermissionDecision.REQUEST_APPROVAL,
                    reason="draft_auto_mode_external_write_requires_approval",
                    requires_approval=True,
                    audit=audit,
                )

            return PermissionEvaluationResult(
                ok=True,
                decision=PermissionDecision.AUTO_RUN,
                reason="draft_auto_mode_allows_non_write_action",
                audit=audit,
            )

        if mode == PermissionMode.AUTO_WITH_EXCEPTIONS:
            if risk in {RiskTier.LOW, RiskTier.MEDIUM}:
                return PermissionEvaluationResult(
                    ok=True,
                    decision=PermissionDecision.AUTO_RUN,
                    reason="auto_with_exceptions_allows_low_or_medium_risk",
                    audit=audit,
                )

        if mode == PermissionMode.TRUSTED_WORKFLOW:
            if risk == RiskTier.LOW:
                return PermissionEvaluationResult(
                    ok=True,
                    decision=PermissionDecision.AUTO_RUN,
                    reason="trusted_workflow_allows_low_risk",
                    audit=audit,
                )
            return PermissionEvaluationResult(
                ok=True,
                decision=PermissionDecision.REQUEST_APPROVAL,
                reason="trusted_workflow_medium_or_high_risk_requires_approval",
                requires_approval=True,
                audit=audit,
            )

        if mode == PermissionMode.FULL_AUTO:
            if risk in {RiskTier.LOW, RiskTier.MEDIUM}:
                return PermissionEvaluationResult(
                    ok=True,
                    decision=PermissionDecision.AUTO_RUN,
                    reason="full_auto_allows_low_or_medium_risk",
                    audit=audit,
                )

        return PermissionEvaluationResult(
            ok=True,
            decision=PermissionDecision.REQUEST_APPROVAL,
            reason="default_safe_approval_required",
            requires_approval=True,
            audit=audit,
        )
