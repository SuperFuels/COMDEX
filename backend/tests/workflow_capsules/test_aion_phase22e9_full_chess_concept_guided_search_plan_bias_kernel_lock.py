from pathlib import Path

from backend.modules.aion_games.full_chess_concept_guided_search_plan_bias_kernel import (
    run_full_chess_concept_guided_search_plan_bias_kernel,
)


def test_phase22e9_applies_concept_guided_bias(tmp_path: Path):
    result = run_full_chess_concept_guided_search_plan_bias_kernel(
        memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.bias_mode == "concept_guided_search_and_plan_bias"
    assert result.applied_concept_count >= 1
    assert result.concept_bias_score_total > 0
    assert result.strongest_applied_concept != "none"
    assert result.evidence["concept_guided_search_bias_active"] is True
    assert result.evidence["concept_guided_plan_bias_active"] is True


def test_phase22e9_consumes_search_plan_and_concepts(tmp_path: Path):
    result = run_full_chess_concept_guided_search_plan_bias_kernel(
        memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.evidence["strategic_search_consumed"] is True
    assert result.evidence["long_term_plan_consumed"] is True
    assert result.evidence["strategic_concept_memory_consumed"] is True
    assert result.strategic_trace_hash
    assert result.long_term_plan_trace_hash
    assert result.concept_memory_trace_hash


def test_phase22e9_applied_concepts_have_bias_scores(tmp_path: Path):
    result = run_full_chess_concept_guided_search_plan_bias_kernel(
        memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    for concept in result.applied_concepts:
        assert concept["bias_score"] > 0
        assert concept["policy_weight"] > 1.0
        assert concept["success_rate"] > 0
        assert concept["bias_trace_hash"]
        assert concept["matched_plan_stage"] or concept["matched_search_goal"]


def test_phase22e9_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "bias_memory.json"

    first = run_full_chess_concept_guided_search_plan_bias_kernel(
        memory_path=memory_path,
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )
    second = run_full_chess_concept_guided_search_plan_bias_kernel(
        memory_path=memory_path,
        concept_memory_path=tmp_path / "concept_memory.json",
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
    assert second.final_concept_guided_bias_policy["kernel_run_count"] == 2
    assert second.final_concept_guided_bias_policy["applied_concept_total"] >= first.applied_concept_count


def test_phase22e9_boundary_no_live_send_or_external_engines(tmp_path: Path):
    result = run_full_chess_concept_guided_search_plan_bias_kernel(
        memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.evidence["live_lichess_send_enabled"] is False
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
