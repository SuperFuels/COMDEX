from pathlib import Path

from backend.modules.aion_games.full_chess_local_concept_guided_game_loop_kernel import (
    run_full_chess_local_concept_guided_game_loop_kernel,
)


def test_phase22e11_runs_local_concept_guided_game_loop(tmp_path: Path):
    result = run_full_chess_local_concept_guided_game_loop_kernel(
        memory_path=tmp_path / "loop_memory.json",
        rerank_memory_path=tmp_path / "rerank_memory.json",
        bias_memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        plies=4,
    )

    assert result.game_loop_mode == "local_concept_guided_preview"
    assert result.plies_completed == 4
    assert result.legal_move_rate == 1.0
    assert result.concept_memory_active is True
    assert result.concepts_applied_total > 0
    assert result.evidence["local_concept_guided_game_loop_active"] is True


def test_phase22e11_records_trace_per_ply(tmp_path: Path):
    result = run_full_chess_local_concept_guided_game_loop_kernel(
        memory_path=tmp_path / "loop_memory.json",
        rerank_memory_path=tmp_path / "rerank_memory.json",
        bias_memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        plies=3,
    )

    assert len(result.ply_summaries) == 3
    for ply in result.ply_summaries:
        assert ply["move_is_legal"] is True
        assert ply["selected_move"]
        assert ply["concept_guided_trace_hash"]
        assert ply["ply_trace_hash"]


def test_phase22e11_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "loop_memory.json"

    first = run_full_chess_local_concept_guided_game_loop_kernel(
        memory_path=memory_path,
        rerank_memory_path=tmp_path / "rerank_memory.json",
        bias_memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        plies=2,
    )
    second = run_full_chess_local_concept_guided_game_loop_kernel(
        memory_path=memory_path,
        rerank_memory_path=tmp_path / "rerank_memory.json",
        bias_memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        plies=2,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_game_loop_policy["kernel_run_count"] == 2
    assert second.final_game_loop_policy["plies_completed_total"] == 4


def test_phase22e11_boundary_no_live_send_or_external_engines(tmp_path: Path):
    result = run_full_chess_local_concept_guided_game_loop_kernel(
        memory_path=tmp_path / "loop_memory.json",
        rerank_memory_path=tmp_path / "rerank_memory.json",
        bias_memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        plies=3,
    )

    assert result.evidence["live_lichess_send_enabled"] is False
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True


def test_phase22e11_completes_short_terminal_safe_preview(tmp_path: Path):
    result = run_full_chess_local_concept_guided_game_loop_kernel(
        memory_path=tmp_path / "loop_memory.json",
        rerank_memory_path=tmp_path / "rerank_memory.json",
        bias_memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        initial_fen="7k/5K2/6Q1/8/8/8/8/8 b - - 0 1",
        plies=4,
    )

    assert result.plies_completed <= 4
    assert result.legal_move_rate == 1.0
    assert result.terminal_status in {
        "active",
        "checkmate",
        "stalemate",
        "insufficient_material",
        "game_over",
    }
