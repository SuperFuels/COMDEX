import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e76_live_loss_point_captures_e3_pawn_instead_of_c3(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    fen = "r1bqkb1r/pp3ppp/2n1pn2/3p4/5B2/3BpN2/PPPN1PPP/R2Q1RK1 w kq - 0 8"
    board = chess.Board(fen)

    selected = kernel._select_fast_live_move(board)

    assert "f2e3" in selected["legal_moves"]
    assert selected["selected_move"] == "f2e3"
    assert selected["selected_source"] == "phase22e76_advanced_pawn_invasion_fast_selector"


def test_phase22e76_captures_d2_pawn_if_invasion_reaches_back_rank(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    fen = "r1bqkb1r/pp3ppp/2n1pn2/3p4/5B2/3B1N2/PPpN1PPP/R2Q1RK1 w kq - 0 9"
    board = chess.Board(fen)

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] in selected["legal_moves"]
    assert selected["selected_source"] == "phase22e76_advanced_pawn_invasion_fast_selector"


def test_phase22e76_opening_book_still_controls_normal_start(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board()
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"
