from __future__ import annotations

from backend.modules.workflow_capsules.permissions import (
    AgentPermissionProfile,
    PermissionDecision,
    PermissionEvaluationContext,
    PermissionEvaluator,
    PermissionMode,
    RiskTier,
    WorkflowPermissionPolicy,
)


def test_review_mode_requests_approval_for_external_write() -> None:
    result = PermissionEvaluator().evaluate(
        policy=WorkflowPermissionPolicy(
            mode=PermissionMode.REVIEW,
            workflow_id="workflow:electrician.gmail_receptionist.v1",
            allowed_actions=["gmail.send"],
        ),
        agent=AgentPermissionProfile(
            agent_id="agent.receptionist.v1",
            allowed_actions=["gmail.send"],
        ),
        context=PermissionEvaluationContext(
            workspace_id="costa-conexion",
            agent_id="agent.receptionist.v1",
            workflow_id="workflow:electrician.gmail_receptionist.v1",
            node_id="send",
            action="gmail.send",
            connector="gmail",
            risk_tier=RiskTier.MEDIUM,
            is_external_write=True,
        ),
    )

    assert result.ok is True
    assert result.decision == PermissionDecision.REQUEST_APPROVAL
    assert result.requires_approval is True
    assert result.reason == "review_mode_requires_approval"


def test_draft_auto_allows_create_draft_but_not_send() -> None:
    evaluator = PermissionEvaluator()
    policy = WorkflowPermissionPolicy(
        mode=PermissionMode.DRAFT_AUTO,
        allowed_actions=["gmail.create_draft", "gmail.send"],
    )
    agent = AgentPermissionProfile(
        agent_id="agent.receptionist.v1",
        allowed_actions=["gmail.create_draft", "gmail.send"],
    )

    draft = evaluator.evaluate(
        policy=policy,
        agent=agent,
        context=PermissionEvaluationContext(
            action="gmail.create_draft",
            risk_tier=RiskTier.LOW,
            is_draft_action=True,
        ),
    )

    send = evaluator.evaluate(
        policy=policy,
        agent=agent,
        context=PermissionEvaluationContext(
            action="gmail.send",
            risk_tier=RiskTier.MEDIUM,
            is_external_write=True,
        ),
    )

    assert draft.decision == PermissionDecision.DRAFT_ONLY
    assert draft.requires_approval is False

    assert send.decision == PermissionDecision.REQUEST_APPROVAL
    assert send.requires_approval is True


def test_auto_with_exceptions_runs_low_risk_but_pauses_on_risk_flags() -> None:
    evaluator = PermissionEvaluator()
    policy = WorkflowPermissionPolicy(
        mode=PermissionMode.AUTO_WITH_EXCEPTIONS,
        allowed_actions=["gmail.send"],
    )
    agent = AgentPermissionProfile(
        agent_id="agent.receptionist.v1",
        allowed_actions=["gmail.send"],
    )

    normal = evaluator.evaluate(
        policy=policy,
        agent=agent,
        context=PermissionEvaluationContext(
            action="gmail.send",
            risk_tier=RiskTier.MEDIUM,
            is_external_write=True,
            confidence=0.95,
        ),
    )

    flagged = evaluator.evaluate(
        policy=policy,
        agent=agent,
        context=PermissionEvaluationContext(
            action="gmail.send",
            risk_tier=RiskTier.MEDIUM,
            is_external_write=True,
            confidence=0.95,
            risk_flags=["complaint"],
        ),
    )

    assert normal.decision == PermissionDecision.AUTO_RUN
    assert flagged.decision == PermissionDecision.REQUEST_APPROVAL
    assert flagged.requires_approval is True
    assert flagged.reason == "risk_flags_require_approval"


def test_blocked_risk_tier_always_blocks() -> None:
    result = PermissionEvaluator().evaluate(
        policy=WorkflowPermissionPolicy(
            mode=PermissionMode.FULL_AUTO,
            allowed_actions=["xero.payment"],
        ),
        agent=AgentPermissionProfile(
            agent_id="agent.finance.v1",
            allowed_actions=["xero.payment"],
        ),
        context=PermissionEvaluationContext(
            action="xero.payment",
            risk_tier=RiskTier.BLOCKED,
            is_external_write=True,
        ),
    )

    assert result.ok is False
    assert result.decision == PermissionDecision.BLOCK
    assert "risk_tier_blocked" in result.errors


def test_agent_cannot_self_authorise_external_writes() -> None:
    result = PermissionEvaluator().evaluate(
        policy=WorkflowPermissionPolicy(
            mode=PermissionMode.FULL_AUTO,
            allowed_actions=["gmail.send"],
        ),
        agent=AgentPermissionProfile(
            agent_id="agent.receptionist.v1",
            allowed_actions=["gmail.send"],
            can_self_authorise_external_writes=True,
        ),
        context=PermissionEvaluationContext(
            action="gmail.send",
            risk_tier=RiskTier.MEDIUM,
            is_external_write=True,
        ),
    )

    assert result.ok is False
    assert result.decision == PermissionDecision.BLOCK
    assert "agent_self_authorisation_forbidden" in result.errors


def test_manual_only_always_requests_approval() -> None:
    result = PermissionEvaluator().evaluate(
        policy=WorkflowPermissionPolicy(
            mode=PermissionMode.MANUAL_ONLY,
            allowed_actions=["gmail.read"],
        ),
        agent=AgentPermissionProfile(
            agent_id="agent.receptionist.v1",
            allowed_actions=["gmail.read"],
        ),
        context=PermissionEvaluationContext(
            action="gmail.read",
            risk_tier=RiskTier.LOW,
        ),
    )

    assert result.ok is True
    assert result.decision == PermissionDecision.REQUEST_APPROVAL
    assert result.requires_approval is True
