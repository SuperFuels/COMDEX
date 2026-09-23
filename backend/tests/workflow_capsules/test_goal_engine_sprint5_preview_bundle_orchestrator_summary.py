from backend.modules.aion.goal_engine.orchestrator import (
    AgentAssignmentContract,
    OrchestratorContract,
)
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def test_preview_bundle_exposes_orchestrator_runtime_summary():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_orch_001",
        workflow_id="workflow_orch_001",
        contracts=[
            OrchestratorContract(
                orchestrator_id="orch_001",
                goal_id="goal_001",
                agents=[
                    AgentAssignmentContract(
                        agent_id="agent_research_001",
                        role="research",
                        glyph_code="RS-001",
                        goal_id="goal_001",
                    ),
                    AgentAssignmentContract(
                        agent_id="agent_marketing_001",
                        role="marketing",
                        glyph_code="MK-001",
                        goal_id="goal_001",
                    ),
                ],
                coordination_mode="sequential",
                conflict_policy="human_review",
                max_parallel_agents=1,
                child_timeout_seconds=300,
            )
        ],
    )

    payload = bundle.to_dict()

    assert "orchestrator_runtime_summary" in payload
    summary = payload["orchestrator_runtime_summary"]

    assert summary["trace_type"] == "orchestrator_runtime_summary"
    assert summary["orchestrator_count"] == 1
    assert summary["agent_count"] == 2
    assert summary["bounded_orchestrator_count"] == 1
    assert summary["unbounded_orchestrator_count"] == 0
    assert summary["coordination_modes"] == ["sequential"]
    assert summary["conflict_policies"] == ["human_review"]
    assert summary["dry_run_only"] is True
    assert summary["would_execute"] is False
    assert summary["would_write_external"] is False
    assert summary["would_grant_permission"] is False


def test_preview_bundle_orchestrator_summary_tracks_blocked_orchestration():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_orch_blocked_001",
        workflow_id="workflow_orch_001",
        contracts=[
            OrchestratorContract(
                orchestrator_id="orch_blocked_001",
                goal_id="goal_001",
                agents=[],
                coordination_mode="parallel",
                conflict_policy="highest_confidence",
                max_parallel_agents=0,
                child_timeout_seconds=0,
            )
        ],
    )

    summary = bundle.to_dict()["orchestrator_runtime_summary"]

    assert summary["orchestrator_count"] == 1
    assert summary["agent_count"] == 0
    assert summary["bounded_orchestrator_count"] == 0
    assert summary["unbounded_orchestrator_count"] == 1
    assert "unbounded_orchestration_blocked" in summary["blocked_reasons"]
    assert "agents_required" in summary["blocked_reasons"]
    assert "max_parallel_agents_required" in summary["blocked_reasons"]


def test_preview_bundle_orchestrator_summary_preserves_agent_assignment_previews():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_orch_previews_001",
        workflow_id="workflow_orch_001",
        contracts=[
            OrchestratorContract(
                orchestrator_id="orch_previews_001",
                goal_id="goal_001",
                agents=[
                    AgentAssignmentContract(
                        agent_id="agent_finance_001",
                        role="finance",
                        glyph_code="FN-001",
                        goal_id="goal_001",
                    )
                ],
                coordination_mode="review_gated",
                conflict_policy="safest_option",
                max_parallel_agents=1,
                child_timeout_seconds=300,
                requires_human_approval=True,
            )
        ],
    )

    summary = bundle.to_dict()["orchestrator_runtime_summary"]

    assert "orchestrator_previews" in summary
    assert len(summary["orchestrator_previews"]) == 1

    preview = summary["orchestrator_previews"][0]
    assert preview["orchestrator_id"] == "orch_previews_001"
    assert preview["requires_human_approval"] is True
    assert preview["coordination_mode"] == "review_gated"
    assert preview["agent_assignment_previews"][0]["agent_id"] == "agent_finance_001"
    assert preview["agent_assignment_previews"][0]["glyph_code"] == "FN-001"
