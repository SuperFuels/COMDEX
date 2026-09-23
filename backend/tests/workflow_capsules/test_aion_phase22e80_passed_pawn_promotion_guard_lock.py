import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e80_does_not_abandon_b1_block_square_from_live_loss(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r2qk2r/pp1n1pp1/2p4p/8/3PP3/b1Q2N2/bp3PPP/1R4K1 w kq - 0 19")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e80_passed_pawn_promotion_guard_fast_selector"
    assert selected["selected_move"] != "b1d1"
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e80_prefers_capturing_black_pawn_on_b2_when_available(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r2qk2r/pp1n1pp1/2p4p/8/3PP3/b1Q2N2/bp3PPP/1R4K1 w kq - 0 19")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] == "c3b2"
    assert "capture_promotion_pawn" in selected["phase22e80_promotion_guard_plan"]


def test_phase22e80_blocks_a_pawn_promotion_when_possible(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("4k3/8/8/8/8/Q7/p7/6K1 w - - 0 1")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e80_passed_pawn_promotion_guard_fast_selector"
    assert selected["selected_move"] in {"a3a2", "a3a1"}
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e80_opening_book_still_owns_start(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    selected = kernel._select_fast_live_move(chess.Board())

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"
