from __future__ import annotations

from backend.modules.workflow_capsules.permissions.permission_modes import (
    PermissionDecision,
    PermissionMode,
    RiskTier,
)
from backend.modules.workflow_capsules.permissions.permission_evaluator import (
    PermissionEvaluator,
)
from backend.modules.workflow_capsules.permissions.permission_policy import (
    AgentPermissionProfile,
    PermissionEvaluationContext,
    WorkflowPermissionPolicy,
)


def _evaluate(
    *,
    mode: PermissionMode = PermissionMode.REVIEW,
    risk_tier: RiskTier = RiskTier.LOW,
    action: str = "draft_content",
    is_external_write: bool = False,
    is_draft_action: bool = False,
    risk_flags: list[str] | None = None,
    execution_mode: str = "connector_ready",
    agent_allowed_actions: list[str] | None = None,
    workflow_allowed_actions: list[str] | None = None,
):
    evaluator = PermissionEvaluator()

    policy = WorkflowPermissionPolicy(
        workflow_id="workflow:electrician.gmail_receptionist.v1",
        mode=mode,
        allowed_actions=workflow_allowed_actions or [],
    )

    agent = AgentPermissionProfile(
        agent_id="receptionist_agent",
        allowed_actions=agent_allowed_actions or [],
        can_self_authorise_external_writes=False,
    )

    context = PermissionEvaluationContext(
        workspace_id="costa-conexion",
        agent_id="receptionist_agent",
        workflow_id="workflow:electrician.gmail_receptionist.v1",
        node_id="node_1",
        action=action,
        connector="gmail",
        risk_tier=risk_tier,
        is_external_write=is_external_write,
        is_draft_action=is_draft_action,
        risk_flags=risk_flags or [],
        execution_mode=execution_mode,
    )

    return evaluator.evaluate(policy=policy, agent=agent, context=context)


def test_review_required_requests_approval_before_guarded_resume() -> None:
    result = _evaluate(
        mode=PermissionMode.REVIEW,
        risk_tier=RiskTier.MEDIUM,
        action="send_email",
        is_external_write=True,
        execution_mode="connector_ready",
    )

    assert result.ok is True
    assert result.decision == PermissionDecision.REQUEST_APPROVAL
    assert result.requires_approval is True
    assert result.reason == "review_mode_requires_approval"
    assert result.audit["execution_mode"] == "connector_ready"


def test_draft_auto_allows_draft_but_blocks_send_behind_approval() -> None:
    draft = _evaluate(
        mode=PermissionMode.DRAFT_AUTO,
        risk_tier=RiskTier.LOW,
        action="draft_content",
        is_draft_action=True,
        is_external_write=False,
    )

    assert draft.ok is True
    assert draft.decision == PermissionDecision.DRAFT_ONLY
    assert draft.requires_approval is False
    assert draft.reason == "draft_auto_mode_allows_draft"

    send = _evaluate(
        mode=PermissionMode.DRAFT_AUTO,
        risk_tier=RiskTier.MEDIUM,
        action="send_email",
        is_external_write=True,
        is_draft_action=False,
    )

    assert send.ok is True
    assert send.decision == PermissionDecision.REQUEST_APPROVAL
    assert send.requires_approval is True
    assert send.reason == "draft_auto_mode_external_write_requires_approval"


def test_auto_with_exceptions_allows_low_risk_but_pauses_exception_risk() -> None:
    low = _evaluate(
        mode=PermissionMode.AUTO_WITH_EXCEPTIONS,
        risk_tier=RiskTier.LOW,
        action="summarise",
        is_external_write=False,
    )

    assert low.ok is True
    assert low.decision == PermissionDecision.AUTO_RUN
    assert low.requires_approval is False
    assert low.reason == "auto_with_exceptions_allows_low_or_medium_risk"

    exception = _evaluate(
        mode=PermissionMode.AUTO_WITH_EXCEPTIONS,
        risk_tier=RiskTier.MEDIUM,
        action="draft_refund_reply",
        is_external_write=False,
        risk_flags=["refund", "complaint"],
    )

    assert exception.ok is True
    assert exception.decision == PermissionDecision.REQUEST_APPROVAL
    assert exception.requires_approval is True
    assert exception.reason == "risk_flags_require_approval"

    high = _evaluate(
        mode=PermissionMode.AUTO_WITH_EXCEPTIONS,
        risk_tier=RiskTier.HIGH,
        action="legal_statement",
        is_external_write=True,
    )

    assert high.ok is True
    assert high.decision == PermissionDecision.REQUEST_APPROVAL
    assert high.requires_approval is True
    assert high.reason == "high_risk_requires_approval"


def test_manual_only_blocks_automatic_execution_by_requiring_approval() -> None:
    result = _evaluate(
        mode=PermissionMode.MANUAL_ONLY,
        risk_tier=RiskTier.LOW,
        action="draft_content",
        is_draft_action=True,
        is_external_write=False,
    )

    assert result.ok is True
    assert result.decision == PermissionDecision.REQUEST_APPROVAL
    assert result.requires_approval is True
    assert result.reason == "manual_only_mode_requires_approval"


def test_blocked_risk_tier_blocks_execution() -> None:
    result = _evaluate(
        mode=PermissionMode.FULL_AUTO,
        risk_tier=RiskTier.BLOCKED,
        action="bank_payment",
        is_external_write=True,
    )

    assert result.ok is False
    assert result.decision == PermissionDecision.BLOCK
    assert result.requires_approval is False
    assert result.reason == "risk_tier_blocked"
    assert "risk_tier_blocked" in result.errors


def test_no_mode_can_self_enable_live_execute() -> None:
    for mode in [
        PermissionMode.REVIEW,
        PermissionMode.DRAFT_AUTO,
        PermissionMode.AUTO_WITH_EXCEPTIONS,
        PermissionMode.TRUSTED_WORKFLOW,
        PermissionMode.FULL_AUTO,
        PermissionMode.MANUAL_ONLY,
    ]:
        result = _evaluate(
            mode=mode,
            risk_tier=RiskTier.MEDIUM,
            action="send_email",
            is_external_write=True,
            execution_mode="live_execute",
        )

        assert result.audit["execution_mode"] == "live_execute"

        # Current lock: permission evaluator records requested mode but does not
        # grant live execution. Live execution remains a separate runner/connector guard.
        assert result.reason != "live_execute_allowed"
        assert result.decision in {
            PermissionDecision.REQUEST_APPROVAL,
            PermissionDecision.AUTO_RUN,
            PermissionDecision.BLOCK,
        }
