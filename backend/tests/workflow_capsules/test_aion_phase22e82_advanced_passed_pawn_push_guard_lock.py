import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e82_triggers_before_f_pawn_promotes_from_live_loss(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    # Live loss: AION played a2-a4 while black had e3/f4 advanced passers.
    # Then black pushed f4-f3 and the f-pawn promotion chain began.
    board = chess.Board("r7/pp3rk1/2n3p1/2R4b/5p2/4p3/P7/6K1 w - - 0 30")

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e82_advanced_passed_pawn_push_guard_fast_selector"
    assert selected["selected_move"] != "a2a4"
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e82_triggers_when_f_pawn_reaches_f3(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r7/pp3rk1/2n3p1/2R4b/P7/4pp2/8/6K1 w - - 0 31")

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e82_advanced_passed_pawn_push_guard_fast_selector"
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e82_opening_book_still_owns_start(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    selected = kernel._select_fast_live_move(chess.Board())

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"


def test_phase22e82_promotion_guard_still_owns_rank_one_emergency(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r2qk2r/pp1n1pp1/2p4p/8/3PP3/b1Q2N2/bp3PPP/1R4K1 w kq - 0 19")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e80_passed_pawn_promotion_guard_fast_selector"
    assert selected["selected_move"] == "c3b2"
