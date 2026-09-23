from pathlib import Path

from backend.modules.aion_games.full_chess_consequence_simulation_risk_forecasting_kernel import (
    run_full_chess_consequence_simulation_risk_forecasting_kernel,
)


def test_phase22e7_forecasts_risk_for_each_long_term_plan_stage(tmp_path: Path):
    result = run_full_chess_consequence_simulation_risk_forecasting_kernel(
        memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.forecast_mode == "consequence_simulation_and_risk_forecasting"
    assert result.forecast_count == result.plan_stage_count
    assert result.forecast_count >= 3
    assert result.evidence["consequence_simulation_active"] is True
    assert result.evidence["risk_forecasting_active"] is True
    assert result.evidence["long_term_plan_consumed"] is True


def test_phase22e7_risk_fields_are_computed(tmp_path: Path):
    result = run_full_chess_consequence_simulation_risk_forecasting_kernel(
        memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    first = result.risk_forecasts[0]
    assert "risk_before" in first
    assert "risk_after_expected" in first
    assert "risk_delta" in first
    assert "failure_probability" in first
    assert "fallback_required" in first
    assert "forecast_trace_hash" in first
    assert result.average_risk_after_expected <= result.average_risk_before


def test_phase22e7_high_risk_position_requires_fallback(tmp_path: Path):
    result = run_full_chess_consequence_simulation_risk_forecasting_kernel(
        memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        fen="4k3/8/8/8/8/8/6q1/4K3 w - - 0 1",
    )

    assert result.maximum_failure_probability >= 0
    assert result.fallback_required_count >= 1
    assert result.highest_risk_stage_goal


def test_phase22e7_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "forecast_memory.json"

    first = run_full_chess_consequence_simulation_risk_forecasting_kernel(
        memory_path=memory_path,
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )
    second = run_full_chess_consequence_simulation_risk_forecasting_kernel(
        memory_path=memory_path,
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_forecast_policy["kernel_run_count"] == 2
    assert second.final_forecast_policy["forecast_run_count"] == 2


def test_phase22e7_boundary_no_external_engines(tmp_path: Path):
    result = run_full_chess_consequence_simulation_risk_forecasting_kernel(
        memory_path=tmp_path / "forecast_memory.json",
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
