from pathlib import Path

from backend.modules.aion_games.full_chess_strategic_concept_memory_kernel import (
    run_full_chess_strategic_concept_memory_kernel,
)


def test_phase22e8_generates_named_strategic_concepts(tmp_path: Path):
    result = run_full_chess_strategic_concept_memory_kernel(
        memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.concept_memory_mode == "strategic_concept_memory"
    assert result.concept_count >= 3
    assert "king_safety_recovery" in result.concept_names
    assert result.evidence["applied_concepts_this_run"] >= 1
    assert result.evidence["plan_alignment_with_concepts"] > 0
    assert "development_before_attack" in result.concept_names
    assert "centre_control_before_conversion" in result.concept_names
    assert "safe_endgame_conversion" in result.concept_names


def test_phase22e8_reinforcement_scores_are_computed(tmp_path: Path):
    result = run_full_chess_strategic_concept_memory_kernel(
        memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.strongest_concept != "none"
    assert result.strongest_reinforcement_score > 0
    for concept in result.active_concepts:
        assert concept["reinforcement_score"] > 0
        assert concept["observed_count"] >= 1
        assert concept["usage_count"] >= 1
        assert concept["success_rate"] > 0
        assert concept["policy_weight"] > 1.0
        assert concept["average_risk_reduction"] >= 0
        assert concept["trigger_features"]
        assert concept["preferred_actions"]
        assert concept["fallback_concepts"]
        assert concept["concept_trace_hash"]


def test_phase22e8_promotion_position_adds_promotion_defence_protocol(tmp_path: Path):
    result = run_full_chess_strategic_concept_memory_kernel(
        memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        fen="4k3/8/8/8/8/8/6p1/4K3 w - - 0 1",
    )

    assert "promotion_defence_protocol" in result.concept_names


def test_phase22e8_memory_reinforces_concepts_across_runs(tmp_path: Path):
    memory_path = tmp_path / "concept_memory.json"

    first = run_full_chess_strategic_concept_memory_kernel(
        memory_path=memory_path,
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )
    second = run_full_chess_strategic_concept_memory_kernel(
        memory_path=memory_path,
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.reinforced_concept_count >= 1
    assert second.final_concept_memory_policy["kernel_run_count"] == 2
    assert second.final_concept_memory_policy["applied_concepts_total"] >= 2
    assert second.final_concept_memory_policy["last_plan_alignment_with_concepts"] > 0


def test_phase22e8_boundary_no_external_engines(tmp_path: Path):
    result = run_full_chess_strategic_concept_memory_kernel(
        memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
