from pathlib import Path

import chess

from backend.modules.aion_games.full_chess_goal_biased_strategic_search_kernel import (
    run_full_chess_goal_biased_strategic_search_kernel,
)


def test_phase22e2_selects_legal_goal_biased_move(tmp_path: Path):
    result = run_full_chess_goal_biased_strategic_search_kernel(
        memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        fen=chess.STARTING_FEN,
        side_to_evaluate="white",
        depth_limit=2,
    )

    assert result.search_mode == "goal_biased_multi_ply_strategic_search"
    assert result.selected_move
    assert result.evidence["selected_move_is_legal"] is True
    assert result.evidence["goal_biased_strategic_search_active"] is True
    assert result.evidence["multi_ply_search_active"] is True
    assert result.evidence["positional_features_consumed"] is True
    assert result.top_candidate_lines


def test_phase22e2_emits_goal_bias_fields(tmp_path: Path):
    result = run_full_chess_goal_biased_strategic_search_kernel(
        memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        depth_limit=2,
    )

    top = result.top_candidate_lines[0]
    assert "goal_bias_score" in top
    assert "positional_delta" in top
    assert "feature_summary_after_move" in top
    assert result.evidence["king_safety_goal_active"] is True
    assert result.evidence["promotion_defence_goal_active"] is True
    assert result.evidence["invasion_reduction_goal_active"] is True


def test_phase22e2_detects_promotion_defence_goal_available(tmp_path: Path):
    fen = "4k3/8/8/8/8/8/6p1/4K3 w - - 0 1"
    result = run_full_chess_goal_biased_strategic_search_kernel(
        memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        fen=fen,
        side_to_evaluate="white",
        depth_limit=2,
    )

    assert result.evidence["promotion_defence_goal_active"] is True
    assert result.selected_reason == "goal_biased_multi_ply_strategic_selection"
    assert result.candidate_count > 0


def test_phase22e2_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "strategic_memory.json"

    first = run_full_chess_goal_biased_strategic_search_kernel(
        memory_path=memory_path,
        feature_memory_path=tmp_path / "feature_memory.json",
        depth_limit=2,
    )
    second = run_full_chess_goal_biased_strategic_search_kernel(
        memory_path=memory_path,
        feature_memory_path=tmp_path / "feature_memory.json",
        depth_limit=2,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_strategic_policy["kernel_run_count"] == 2
    assert second.final_strategic_policy["strategic_search_count"] == 2


def test_phase22e2_boundary_no_external_engines(tmp_path: Path):
    result = run_full_chess_goal_biased_strategic_search_kernel(
        memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        depth_limit=2,
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
