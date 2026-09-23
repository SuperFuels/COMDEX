from pathlib import Path

import chess

from backend.modules.aion_games.full_chess_intent_driven_strategic_regression_well_kernel import (
    run_full_chess_intent_driven_strategic_regression_well_kernel,
)


def test_phase22e37_consumes_intent_driver_and_base_well(tmp_path: Path):
    result = run_full_chess_intent_driven_strategic_regression_well_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.intent_driven_regression_well_active is True
    assert result.evidence["intent_driver_consumed"] is True
    assert result.evidence["strategic_regression_well_consumed"] is True
    assert result.final_selected_move_is_legal is True


def test_phase22e37_corrects_opening_wing_pawn_drift(tmp_path: Path):
    result = run_full_chess_intent_driven_strategic_regression_well_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        repeated_moves=["d2d4", "d7d5"],
        repeated_squares=["d4", "d5"],
        memory_path=tmp_path / "memory.json",
    )

    assert result.active_intent in {"rapid_development", "center_control", "king_safety"}
    assert result.final_selected_move_is_legal is True
    assert result.final_selected_move not in {"h2h4", "g1h3", "b1a3"}
    assert result.final_selected_move in {"g1f3", "b1c3", "c1f4", "c1g5", "e2e4", "e2e3", "c2c4"}
    assert result.intent_override_applied is True


def test_phase22e37_preserves_passed_pawn_conversion(tmp_path: Path):
    result = run_full_chess_intent_driven_strategic_regression_well_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.active_intent == "convert_passed_pawn"
    assert result.final_selected_move == "a7a8q"
    assert result.final_selected_move_is_legal is True


def test_phase22e37_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_intent_driven_strategic_regression_well_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_intent_driven_strategic_regression_well_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e37_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_intent_driven_strategic_regression_well_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "does not send moves" in result.boundary_statement
