from pathlib import Path

from backend.modules.aion_games.full_chess_long_term_plan_generation_kernel import (
    run_full_chess_long_term_plan_generation_kernel,
)


def test_phase22e6_generates_multi_stage_long_term_plan(tmp_path: Path):
    result = run_full_chess_long_term_plan_generation_kernel(
        memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.plan_mode == "long_term_multi_stage_plan_generation"
    assert result.plan_stage_count >= 3
    assert result.evidence["long_term_plan_generation_active"] is True
    assert result.evidence["multi_stage_plan_active"] is True
    assert result.evidence["positional_features_consumed"] is True
    assert result.evidence["simple_plan_consumed"] is True
    assert result.evidence["curriculum_policy_consumed"] is True


def test_phase22e6_contains_expected_starting_position_stages(tmp_path: Path):
    result = run_full_chess_long_term_plan_generation_kernel(
        memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    goals = [stage["stage_goal"] for stage in result.long_term_plan]

    assert "stabilise_king" in goals
    assert "develop_inactive_pieces" in goals
    assert "improve_centre_control" in goals
    assert "improve_piece_activity" in goals
    assert result.terminal_plan_goal == "convert_to_safer_endgame"


def test_phase22e6_detects_promotion_plan_stage(tmp_path: Path):
    result = run_full_chess_long_term_plan_generation_kernel(
        memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        fen="4k3/8/8/8/8/8/6p1/4K3 w - - 0 1",
    )

    goals = [stage["stage_goal"] for stage in result.long_term_plan]
    assert "stop_immediate_promotion" in goals


def test_phase22e6_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "long_term_plan_memory.json"

    first = run_full_chess_long_term_plan_generation_kernel(
        memory_path=memory_path,
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )
    second = run_full_chess_long_term_plan_generation_kernel(
        memory_path=memory_path,
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_long_term_plan_policy["kernel_run_count"] == 2
    assert second.final_long_term_plan_policy["long_term_plan_generation_count"] == 2


def test_phase22e6_boundary_no_external_engines(tmp_path: Path):
    result = run_full_chess_long_term_plan_generation_kernel(
        memory_path=tmp_path / "long_term_plan_memory.json",
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
