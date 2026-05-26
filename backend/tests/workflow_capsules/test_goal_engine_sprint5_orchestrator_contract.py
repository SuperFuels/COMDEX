from backend.modules.aion.goal_engine.orchestrator import (
    ORCHESTRATOR_SCHEMA_VERSION,
    AGENT_ASSIGNMENT_SCHEMA_VERSION,
    AgentAssignmentContract,
    OrchestratorContract,
    build_agent_assignment_preview,
    build_orchestrator_preview,
)


def test_orchestrator_schema_versions_are_locked():
    assert AGENT_ASSIGNMENT_SCHEMA_VERSION == "aion.goal_engine.agent_assignment.v1"
    assert ORCHESTRATOR_SCHEMA_VERSION == "aion.goal_engine.orchestrator.v1"


def test_agent_assignment_preview_exposes_role_and_glyph_code():
    agent = AgentAssignmentContract(
        agent_id="agent_marketing_001",
        role="marketing",
        glyph_code="MK-001",
        goal_id="goal_leads_001",
        capabilities=["draft_content", "analyze_channel"],
    )

    preview = build_agent_assignment_preview(agent)

    assert preview["schema_version"] == AGENT_ASSIGNMENT_SCHEMA_VERSION
    assert preview["trace_type"] == "agent_assignment_preview"
    assert preview["agent_id"] == "agent_marketing_001"
    assert preview["role"] == "marketing"
    assert preview["glyph_code"] == "MK-001"
    assert preview["goal_id"] == "goal_leads_001"
    assert preview["valid"] is True
    assert preview["blocked_reasons"] == []
    assert preview["dry_run_only"] is True
    assert preview["would_execute"] is False
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False


def test_agent_assignment_blocks_missing_role_or_glyph_code():
    agent = AgentAssignmentContract(
        agent_id="agent_incomplete_001",
        role="",
        glyph_code="",
        goal_id="goal_leads_001",
    )

    preview = build_agent_assignment_preview(agent)

    assert preview["valid"] is False
    assert "role_required" in preview["blocked_reasons"]
    assert "glyph_code_required" in preview["blocked_reasons"]


def test_orchestrator_preview_supports_sequential_coordination():
    orchestrator = OrchestratorContract(
        orchestrator_id="orch_leads_001",
        goal_id="goal_leads_001",
        agents=[
            AgentAssignmentContract(
                agent_id="agent_research_001",
                role="research",
                glyph_code="RS-001",
                goal_id="goal_leads_001",
            ),
            AgentAssignmentContract(
                agent_id="agent_marketing_001",
                role="marketing",
                glyph_code="MK-001",
                goal_id="goal_leads_001",
            ),
        ],
        coordination_mode="sequential",
        conflict_policy="human_review",
        max_parallel_agents=1,
        child_timeout_seconds=300,
    )

    preview = build_orchestrator_preview(orchestrator)

    assert preview["schema_version"] == ORCHESTRATOR_SCHEMA_VERSION
    assert preview["trace_type"] == "orchestrator_preview"
    assert preview["orchestrator_id"] == "orch_leads_001"
    assert preview["goal_id"] == "goal_leads_001"
    assert preview["agent_count"] == 2
    assert preview["coordination_mode"] == "sequential"
    assert preview["conflict_policy"] == "human_review"
    assert preview["max_parallel_agents"] == 1
    assert preview["bounded"] is True
    assert preview["valid"] is True
    assert preview["dry_run_only"] is True
    assert preview["would_execute"] is False
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False


def test_orchestrator_preview_supports_review_gated_coordination():
    orchestrator = OrchestratorContract(
        orchestrator_id="orch_review_001",
        goal_id="goal_leads_001",
        agents=[
            AgentAssignmentContract(
                agent_id="agent_critic_001",
                role="critic",
                glyph_code="CR-001",
                goal_id="goal_leads_001",
            ),
            AgentAssignmentContract(
                agent_id="agent_reviewer_001",
                role="reviewer",
                glyph_code="RV-001",
                goal_id="goal_leads_001",
            ),
        ],
        coordination_mode="review_gated",
        conflict_policy="safest_option",
        max_parallel_agents=2,
        child_timeout_seconds=600,
        requires_human_approval=True,
    )

    preview = build_orchestrator_preview(orchestrator)

    assert preview["coordination_mode"] == "review_gated"
    assert preview["conflict_policy"] == "safest_option"
    assert preview["requires_human_approval"] is True
    assert preview["bounded"] is True
    assert preview["valid"] is True


def test_orchestrator_blocks_unsafe_parallel_agent_count():
    orchestrator = OrchestratorContract(
        orchestrator_id="orch_unbounded_parallel_001",
        goal_id="goal_leads_001",
        agents=[
            AgentAssignmentContract(
                agent_id="agent_001",
                role="marketing",
                glyph_code="MK-001",
                goal_id="goal_leads_001",
            ),
            AgentAssignmentContract(
                agent_id="agent_002",
                role="sales",
                glyph_code="SL-001",
                goal_id="goal_leads_001",
            ),
        ],
        coordination_mode="parallel",
        conflict_policy="highest_confidence",
        max_parallel_agents=0,
        child_timeout_seconds=300,
    )

    preview = build_orchestrator_preview(orchestrator)

    assert preview["bounded"] is False
    assert preview["valid"] is False
    assert "max_parallel_agents_required" in preview["blocked_reasons"]
    assert "unbounded_orchestration_blocked" in preview["blocked_reasons"]


def test_orchestrator_blocks_invalid_coordination_and_conflict_policy():
    orchestrator = OrchestratorContract(
        orchestrator_id="orch_invalid_policy_001",
        goal_id="goal_leads_001",
        agents=[
            AgentAssignmentContract(
                agent_id="agent_001",
                role="marketing",
                glyph_code="MK-001",
                goal_id="goal_leads_001",
            )
        ],
        coordination_mode="unsafe_free_for_all",
        conflict_policy="auto_takeover",
        max_parallel_agents=1,
        child_timeout_seconds=300,
    )

    preview = build_orchestrator_preview(orchestrator)

    assert preview["valid"] is False
    assert "unsupported_coordination_mode" in preview["blocked_reasons"]
    assert "unsupported_conflict_policy" in preview["blocked_reasons"]


def test_orchestrator_blocks_missing_agents():
    orchestrator = OrchestratorContract(
        orchestrator_id="orch_no_agents_001",
        goal_id="goal_leads_001",
        agents=[],
        coordination_mode="sequential",
        conflict_policy="human_review",
        max_parallel_agents=1,
        child_timeout_seconds=300,
    )

    preview = build_orchestrator_preview(orchestrator)

    assert preview["valid"] is False
    assert preview["agent_count"] == 0
    assert "agents_required" in preview["blocked_reasons"]


def test_orchestrator_preserves_agent_assignment_previews():
    orchestrator = OrchestratorContract(
        orchestrator_id="orch_agent_previews_001",
        goal_id="goal_leads_001",
        agents=[
            AgentAssignmentContract(
                agent_id="agent_finance_001",
                role="finance",
                glyph_code="FN-001",
                goal_id="goal_leads_001",
            )
        ],
        coordination_mode="sequential",
        conflict_policy="human_review",
        max_parallel_agents=1,
        child_timeout_seconds=300,
    )

    preview = build_orchestrator_preview(orchestrator)

    assert "agent_assignment_previews" in preview
    assert len(preview["agent_assignment_previews"]) == 1
    assert preview["agent_assignment_previews"][0]["agent_id"] == "agent_finance_001"
    assert preview["agent_assignment_previews"][0]["glyph_code"] == "FN-001"
