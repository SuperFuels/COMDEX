from pathlib import Path

from backend.modules.aion_games.full_chess_promotion_choice_queen_first_guard_kernel import (
    run_full_chess_promotion_choice_queen_first_guard_kernel,
)


def test_phase22e41_rewrites_underpromotion_to_queen_when_legal(tmp_path: Path):
    result = run_full_chess_promotion_choice_queen_first_guard_kernel(
        input_fen="r1bk1b1r/ppqPn1pp/3p4/4p1p1/1P2P2P/2N2N2/P1P1BPP1/R2QK2R w KQ - 1 12",
        side_to_move="white",
        forced_base_selected_move="d7c8r",
        memory_path=tmp_path / "memory.json",
    )

    assert result.underpromotion_detected is True
    assert result.queen_promotion_available is True
    assert result.queen_override_applied is True
    assert result.base_selected_move == "d7c8r"
    assert result.final_selected_move == "d7c8q"
    assert result.final_selected_move_is_legal is True


def test_phase22e41_keeps_non_promotion_opening_move(tmp_path: Path):
    result = run_full_chess_promotion_choice_queen_first_guard_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        repeated_moves=["d2d4", "d7d5"],
        repeated_squares=["d4", "d5"],
        memory_path=tmp_path / "memory.json",
    )

    assert result.final_selected_move == "g1f3"
    assert result.queen_override_applied is False
    assert result.final_selected_move_is_legal is True


def test_phase22e41_memory_persists(tmp_path: Path):
    memory = tmp_path / "memory.json"

    first = run_full_chess_promotion_choice_queen_first_guard_kernel(
        input_fen="r1bk1b1r/ppqPn1pp/3p4/4p1p1/1P2P2P/2N2N2/P1P1BPP1/R2QK2R w KQ - 1 12",
        side_to_move="white",
        memory_path=memory,
    )
    second = run_full_chess_promotion_choice_queen_first_guard_kernel(
        input_fen="r1bk1b1r/ppqPn1pp/3p4/4p1p1/1P2P2P/2N2N2/P1P1BPP1/R2QK2R w KQ - 1 12",
        side_to_move="white",
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e41_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_promotion_choice_queen_first_guard_kernel(
        input_fen="r1bk1b1r/ppqPn1pp/3p4/4p1p1/1P2P2P/2N2N2/P1P1BPP1/R2QK2R w KQ - 1 12",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "queen-first promotion" in result.boundary_statement
