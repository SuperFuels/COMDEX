from backend.modules.aion.goal_engine.decomposition import (
    GoalDecompositionContract,
    SubGoalContract,
)
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def test_preview_bundle_exposes_goal_decomposition_runtime_summary():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_sprint6_decomposition_test",
        workflow_id="workflow_sprint6_decomposition_test",
        contracts=[
            GoalDecompositionContract(
                decomposition_id="decomp_campaign_001",
                parent_goal_id="goal_campaign_001",
                parent_goal_title="Launch campaign",
                decomposition_strategy="sequential",
                max_depth=3,
                max_sub_goals=4,
                current_depth=1,
                sub_goals=[
                    SubGoalContract(
                        sub_goal_id="sub_goal_research_001",
                        parent_goal_id="goal_campaign_001",
                        title="Research audience",
                        objective="Find buyer segments.",
                        confidence=0.8,
                        glyph_code="RS-001",
                    ),
                    SubGoalContract(
                        sub_goal_id="sub_goal_marketing_001",
                        parent_goal_id="goal_campaign_001",
                        title="Draft campaign",
                        objective="Draft campaign assets.",
                        confidence=0.75,
                        glyph_code="MK-001",
                    ),
                ],
            )
        ]
    )

    payload = bundle.to_dict()

    assert "goal_decomposition_runtime_summary" in payload
    summary = payload["goal_decomposition_runtime_summary"]

    assert summary["trace_type"] == "goal_decomposition_runtime_summary"
    assert summary["decomposition_count"] == 1
    assert summary["sub_goal_count"] == 2
    assert summary["bounded_decomposition_count"] == 1
    assert summary["unbounded_decomposition_count"] == 0
    assert summary["human_review_required_count"] == 0
    assert summary["dry_run_only"] is True
    assert summary["would_execute"] is False


def test_preview_bundle_decomposition_summary_tracks_unbounded_reasons():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_sprint6_decomposition_test",
        workflow_id="workflow_sprint6_decomposition_test",
        contracts=[
            GoalDecompositionContract(
                decomposition_id="decomp_bad_001",
                parent_goal_id="goal_bad_001",
                parent_goal_title="Bad expansion",
                decomposition_strategy="autonomous_free_for_all",
                max_depth=1,
                max_sub_goals=1,
                current_depth=3,
                sub_goals=[
                    SubGoalContract(
                        sub_goal_id="sub_goal_001",
                        parent_goal_id="goal_bad_001",
                        title="One",
                        objective="One.",
                    ),
                    SubGoalContract(
                        sub_goal_id="sub_goal_002",
                        parent_goal_id="goal_bad_001",
                        title="Two",
                        objective="Two.",
                    ),
                ],
            )
        ]
    )

    summary = bundle.to_dict()["goal_decomposition_runtime_summary"]

    assert summary["bounded_decomposition_count"] == 0
    assert summary["unbounded_decomposition_count"] == 1
    assert "unsupported_decomposition_strategy" in summary["blocked_reasons"]
    assert "max_depth_exceeded" in summary["blocked_reasons"]
    assert "max_sub_goals_exceeded" in summary["blocked_reasons"]
    assert "unbounded_decomposition_blocked" in summary["blocked_reasons"]


def test_preview_bundle_decomposition_summary_preserves_previews():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_sprint6_decomposition_test",
        workflow_id="workflow_sprint6_decomposition_test",
        contracts=[
            GoalDecompositionContract(
                decomposition_id="decomp_ops_001",
                parent_goal_id="goal_ops_001",
                parent_goal_title="Improve ops",
                decomposition_strategy="review_gated",
                max_depth=2,
                max_sub_goals=3,
                current_depth=1,
                risk_tier="high",
                approval_required_before_expansion=True,
                sub_goals=[
                    SubGoalContract(
                        sub_goal_id="sub_goal_ops_001",
                        parent_goal_id="goal_ops_001",
                        title="Map process",
                        objective="Map process safely.",
                        confidence=0.9,
                        glyph_code="OP-001",
                        needs_human_review=True,
                    )
                ],
            )
        ]
    )

    summary = bundle.to_dict()["goal_decomposition_runtime_summary"]

    assert "decomposition_previews" in summary
    assert len(summary["decomposition_previews"]) == 1
    preview = summary["decomposition_previews"][0]
    assert preview["decomposition_id"] == "decomp_ops_001"
    assert preview["sub_goal_previews"][0]["glyph_code"] == "OP-001"
    assert summary["human_review_required_count"] == 1
