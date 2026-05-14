from __future__ import annotations

from backend.modules.workflow_capsules.permissions.permission_evaluator import (
    PermissionEvaluator,
)
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


def _evaluate(
    *,
    mode: PermissionMode = PermissionMode.AUTO_WITH_EXCEPTIONS,
    action: str = "send_email",
    risk_tier: RiskTier = RiskTier.MEDIUM,
    is_external_write: bool = True,
    is_draft_action: bool = False,
    confidence: float | None = 0.95,
    risk_flags: list[str] | None = None,
    auto_sends_today: int = 0,
    max_auto_sends_per_day: int = 3,
    recipient_scope: str = "original_thread_only",
    allowed_recipient_scope: str = "original_thread_only",
):
    policy = WorkflowPermissionPolicy(
        mode=mode,
        workflow_id="workflow:test.runtime_limits.v1",
        max_auto_sends_per_day=max_auto_sends_per_day,
        min_confidence=0.86,
        allowed_recipient_scope=allowed_recipient_scope,
    )
    agent = AgentPermissionProfile(
        agent_id="agent.runtime_limits",
        allowed_actions=["read_email", "draft_content", "create_draft", "send_email"],
    )
    context = PermissionEvaluationContext(
        workspace_id="workspace.test",
        agent_id=agent.agent_id,
        workflow_id=policy.workflow_id,
        node_id="send",
        action=action,
        connector="gmail",
        risk_tier=risk_tier,
        is_external_write=is_external_write,
        is_draft_action=is_draft_action,
        confidence=confidence,
        risk_flags=risk_flags or [],
        execution_mode="connector_ready",
        metadata={
            "auto_sends_today": auto_sends_today,
            "recipient_scope": recipient_scope,
        },
    )
    return PermissionEvaluator().evaluate(
        policy=policy,
        agent=agent,
        context=context,
    )


def test_auto_send_allowed_within_limits_and_audit_contains_limit_context() -> None:
    result = _evaluate(auto_sends_today=1, max_auto_sends_per_day=3)

    assert result.ok is True
    assert result.decision == PermissionDecision.AUTO_RUN
    assert result.requires_approval is False

    audit = result.audit
    assert audit["mode"] == "auto_with_exceptions"
    assert audit["action"] == "send_email"
    assert audit["risk_tier"] == "medium"
    assert audit["is_external_write"] is True
    assert audit["auto_sends_today"] == 1
    assert audit["max_auto_sends_per_day"] == 3
    assert audit["recipient_scope"] == "original_thread_only"
    assert audit["allowed_recipient_scope"] == "original_thread_only"


def test_auto_send_pauses_when_daily_limit_reached() -> None:
    result = _evaluate(auto_sends_today=3, max_auto_sends_per_day=3)

    assert result.ok is True
    assert result.decision == PermissionDecision.REQUEST_APPROVAL
    assert result.requires_approval is True
    assert result.reason == "auto_send_daily_limit_reached"


def test_auto_send_pauses_when_confidence_below_threshold() -> None:
    result = _evaluate(confidence=0.42)

    assert result.ok is True
    assert result.decision == PermissionDecision.REQUEST_APPROVAL
    assert result.requires_approval is True
    assert result.reason == "confidence_below_policy_threshold"


def test_auto_send_pauses_when_recipient_scope_not_allowed() -> None:
    result = _evaluate(
        recipient_scope="new_external_recipient",
        allowed_recipient_scope="original_thread_only",
    )

    assert result.ok is True
    assert result.decision == PermissionDecision.REQUEST_APPROVAL
    assert result.requires_approval is True
    assert result.reason == "recipient_scope_requires_approval"


def test_auto_send_pauses_on_risk_exception_flags() -> None:
    result = _evaluate(risk_flags=["complaint", "refund_request"])

    assert result.ok is True
    assert result.decision == PermissionDecision.REQUEST_APPROVAL
    assert result.requires_approval is True
    assert result.reason == "risk_flags_require_approval"
    assert result.audit["risk_flags"] == ["complaint", "refund_request"]


def test_draft_action_is_not_counted_as_send_limit() -> None:
    result = _evaluate(
        mode=PermissionMode.DRAFT_AUTO,
        action="create_draft",
        risk_tier=RiskTier.LOW,
        is_external_write=False,
        is_draft_action=True,
        auto_sends_today=999,
        max_auto_sends_per_day=0,
    )

    assert result.ok is True
    assert result.decision == PermissionDecision.DRAFT_ONLY
    assert result.requires_approval is False
    assert result.reason == "draft_auto_mode_allows_draft"
