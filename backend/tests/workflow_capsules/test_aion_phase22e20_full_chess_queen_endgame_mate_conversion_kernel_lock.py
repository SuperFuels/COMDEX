from pathlib import Path

import chess

from backend.modules.aion_games.full_chess_queen_endgame_mate_conversion_kernel import (
    run_full_chess_queen_endgame_mate_conversion_kernel,
)


def test_phase22e20_detects_queen_endgame_from_live_failure_position(tmp_path: Path):
    result = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.queen_endgame_conversion_active is True
    assert result.selected_move
    assert result.selected_move_is_legal is True
    assert result.candidate_count > 0


def test_phase22e20_penalises_repeated_queen_square(tmp_path: Path):
    fen = "8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61"

    no_penalty = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen=fen,
        side_to_move="white",
        memory_path=tmp_path / "memory_a.json",
    )

    with_penalty = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen=fen,
        side_to_move="white",
        repeated_moves=["d6b8"],
        repeated_queen_squares=["b8", "d6"],
        memory_path=tmp_path / "memory_b.json",
    )

    assert with_penalty.repeated_move_penalty_active is True
    assert with_penalty.repeated_queen_square_penalty_active is True
    assert with_penalty.selected_move_is_legal is True
    assert with_penalty.selected_move != "d6b8" or with_penalty.selected_score < no_penalty.selected_score


def test_phase22e20_prioritises_rook_capture_when_winning(tmp_path: Path):
    fen = "r5k1/8/8/8/8/8/6K1/Q7 w - - 0 1"

    result = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen=fen,
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.queen_endgame_conversion_active is True
    assert result.selected_move == "a1a8"
    assert result.top_candidates[0]["captured_piece_type"] == "rook"


def test_phase22e20_clock_pressure_prefers_forcing_moves(tmp_path: Path):
    fen = "8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61"

    result = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen=fen,
        side_to_move="white",
        clock_seconds_remaining=20,
        memory_path=tmp_path / "memory.json",
    )

    assert result.clock_pressure_active is True
    assert result.selected_move_is_legal is True
    assert result.evidence["clock_pressure_override_enabled"] is True


def test_phase22e20_inactive_without_queen_advantage(tmp_path: Path):
    result = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.queen_endgame_conversion_active is False
    assert result.selected_move == ""
    assert result.selected_move_is_legal is False


def test_phase22e20_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"
    fen = "8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61"

    first = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen=fen,
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen=fen,
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_conversion_policy["kernel_run_count"] == 2


def test_phase22e20_boundary_no_live_or_engine_calls(tmp_path: Path):
    result = run_full_chess_queen_endgame_mate_conversion_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "does not call Lichess" in result.boundary_statement
