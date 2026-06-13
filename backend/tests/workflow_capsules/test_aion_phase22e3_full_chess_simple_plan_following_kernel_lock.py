from pathlib import Path

import chess

from backend.modules.aion_games.full_chess_simple_plan_following_kernel import (
    run_full_chess_simple_plan_following_kernel,
)


def test_phase22e3_forms_plan_and_selects_legal_move(tmp_path: Path):
    result = run_full_chess_simple_plan_following_kernel(
        memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        fen=chess.STARTING_FEN,
        side_to_evaluate="white",
        depth_limit=2,
    )

    assert result.planning_mode == "simple_plan_formation_and_following"
    assert result.active_plan
    assert result.selected_move
    assert result.selected_move_is_legal is True
    assert result.evidence["simple_plan_formation_active"] is True
    assert result.evidence["plan_following_check_active"] is True
    assert result.evidence["strategic_search_consumed"] is True
    assert result.evidence["positional_features_consumed"] is True


def test_phase22e3_start_position_plan_prefers_development_or_centre(tmp_path: Path):
    result = run_full_chess_simple_plan_following_kernel(
        memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        fen=chess.STARTING_FEN,
        side_to_evaluate="white",
        depth_limit=2,
    )

    assert any(goal in result.active_plan for goal in ["develop_pieces", "improve_centre", "improve_piece_activity"])
    assert isinstance(result.plan_followed, bool)
    assert result.plan_alignment_reasons


def test_phase22e3_emergency_promotion_plan_detected(tmp_path: Path):
    fen = "4k3/8/8/8/8/8/6p1/4K3 w - - 0 1"
    result = run_full_chess_simple_plan_following_kernel(
        memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        fen=fen,
        side_to_evaluate="white",
        depth_limit=2,
    )

    assert "stop_promotion" in result.active_plan
    assert "promotion" in result.plan_reason
    assert result.evidence["plan_following_check_active"] is True


def test_phase22e3_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "plan_memory.json"

    first = run_full_chess_simple_plan_following_kernel(
        memory_path=memory_path,
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        depth_limit=2,
    )
    second = run_full_chess_simple_plan_following_kernel(
        memory_path=memory_path,
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        depth_limit=2,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_plan_policy["kernel_run_count"] == 2
    assert second.final_plan_policy["plan_generation_count"] == 2


def test_phase22e3_boundary_no_external_engines(tmp_path: Path):
    result = run_full_chess_simple_plan_following_kernel(
        memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        depth_limit=2,
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
