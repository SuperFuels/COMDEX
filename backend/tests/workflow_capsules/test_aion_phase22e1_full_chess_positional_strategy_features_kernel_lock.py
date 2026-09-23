from pathlib import Path

import chess

from backend.modules.aion_games.full_chess_positional_strategy_features_kernel import (
    run_full_chess_positional_strategy_features_kernel,
)


def test_phase22e1_extracts_core_positional_features(tmp_path: Path):
    result = run_full_chess_positional_strategy_features_kernel(
        memory_path=tmp_path / "positional_memory.json",
        fen=chess.STARTING_FEN,
        analysed_side="white",
    )

    assert result.evidence["positional_strategy_features_active"] is True
    assert result.evidence["king_safety_feature_active"] is True
    assert result.evidence["centre_control_feature_active"] is True
    assert result.evidence["development_feature_active"] is True
    assert result.evidence["piece_activity_feature_active"] is True
    assert result.evidence["pawn_structure_feature_active"] is True
    assert result.evidence["rook_activity_feature_active"] is True
    assert result.evidence["queen_safety_feature_active"] is True
    assert result.evidence["passed_pawn_feature_active"] is True
    assert result.evidence["weak_square_feature_active"] is True
    assert isinstance(result.positional_score, int)
    assert result.positional_trace_hash


def test_phase22e1_detects_enemy_invasion_risk(tmp_path: Path):
    fen = "4k3/8/8/8/8/8/5q2/4K3 w - - 0 1"
    result = run_full_chess_positional_strategy_features_kernel(
        memory_path=tmp_path / "positional_memory.json",
        fen=fen,
        analysed_side="white",
    )

    assert result.invasion_risk_penalty < 0
    assert result.king_safety_score < 0
    assert result.evidence["invasion_risk_feature_active"] is True


def test_phase22e1_detects_promotion_danger(tmp_path: Path):
    fen = "4k3/8/8/8/8/8/6p1/4K3 w - - 0 1"
    result = run_full_chess_positional_strategy_features_kernel(
        memory_path=tmp_path / "positional_memory.json",
        fen=fen,
        analysed_side="white",
    )

    assert result.promotion_danger_penalty < 0
    assert result.evidence["promotion_danger_feature_active"] is True


def test_phase22e1_rewards_passed_pawn_for_analysed_side(tmp_path: Path):
    fen = "4k3/8/8/8/4P3/8/8/4K3 w - - 0 1"
    result = run_full_chess_positional_strategy_features_kernel(
        memory_path=tmp_path / "positional_memory.json",
        fen=fen,
        analysed_side="white",
    )

    assert result.passed_pawn_score > 0


def test_phase22e1_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "positional_memory.json"

    first = run_full_chess_positional_strategy_features_kernel(memory_path=memory_path)
    second = run_full_chess_positional_strategy_features_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_positional_policy["kernel_run_count"] == 2
    assert second.final_positional_policy["positional_analysis_count"] == 2


def test_phase22e1_boundary_no_external_engines(tmp_path: Path):
    result = run_full_chess_positional_strategy_features_kernel(memory_path=tmp_path / "positional_memory.json")

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
