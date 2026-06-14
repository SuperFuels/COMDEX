import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e83_traps_qa1_with_knight_pressure_from_live_loss(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("rnb1kb1r/pp1p1ppp/4pn2/2p5/3P1B2/3BPN2/P1P2PPP/qN1Q1R1K w kq - 0 7")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e83_queen_corner_intrusion_trap_guard_fast_selector"
    assert selected["selected_move"] in {"b1c3", "b1d2", "b1a3"}
    assert selected["phase22e83_queen_corner_square"] == "a1"


def test_phase22e83_traps_qa2_before_escape(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r1b1kb1r/pp1p1ppp/2n1pn2/8/5B2/3BPN2/q1P3PP/1N1Q1R1K w kq - 0 11")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e83_queen_corner_intrusion_trap_guard_fast_selector"
    assert selected["selected_move"] in {"d3c4", "b1c3"}
    assert selected["phase22e83_queen_corner_square"] == "a2"


def test_phase22e83_traps_qa4_before_qc2_escape(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r1b2rk1/pp1pbppp/2n1pn2/8/q4B2/3BPN2/2PN2PP/3Q1R1K w - - 6 14")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e83_queen_corner_intrusion_trap_guard_fast_selector"
    assert selected["selected_move"] in {"d3b5", "d1a1", "c2c3", "c2c4"}
    assert selected["phase22e83_queen_corner_square"] == "a4"


def test_phase22e83_opening_book_still_owns_start(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    selected = kernel._select_fast_live_move(chess.Board())

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"


def test_phase22e83_promotion_guard_still_owns_rank_one_emergency(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r2qk2r/pp1n1pp1/2p4p/8/3PP3/b1Q2N2/bp3PPP/1R4K1 w kq - 0 19")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e80_passed_pawn_promotion_guard_fast_selector"
    assert selected["selected_move"] == "c3b2"
