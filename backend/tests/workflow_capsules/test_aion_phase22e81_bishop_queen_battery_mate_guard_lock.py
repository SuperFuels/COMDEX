import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e81_rejects_qh5_allows_qf2_bg2_mate_net_from_live_loss(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    # Live loss: AION played Qd1-h5, Black replied ...Qf2, then ...Bg2#.
    board = chess.Board("r5k1/pb3rpp/5q2/2p1n3/2P5/3pP3/PP4PP/R2Q2K1 w - - 0 18")

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e81_bishop_queen_battery_mate_guard_fast_selector"
    assert selected["selected_move"] != "d1h5"
    assert "d1h5" in selected["phase22e81_forced_rejects"]
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e81_detects_forced_mate_sequence_after_qh5(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r5k1/pb3rpp/5q2/2p1n3/2P5/3pP3/PP4PP/R2Q2K1 w - - 0 18")
    move = chess.Move.from_uci("d1h5")
    assert move in board.legal_moves

    board.push(move)
    forced = kernel._fast_forced_mate_sequence_replies(board)

    assert "f6f2" in forced


def test_phase22e81_opening_book_still_owns_start(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    selected = kernel._select_fast_live_move(chess.Board())

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"


def test_phase22e81_promotion_guard_still_owns_promotion_emergency(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r2qk2r/pp1n1pp1/2p4p/8/3PP3/b1Q2N2/bp3PPP/1R4K1 w kq - 0 19")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e80_passed_pawn_promotion_guard_fast_selector"
    assert selected["selected_move"] == "c3b2"
