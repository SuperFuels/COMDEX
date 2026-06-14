import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e79_rejects_false_queen_attack_nd2c4_from_live_loss(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    # Live loss position before AION played Nd2-c4 while black queen was on e3.
    board = chess.Board("r1b1k2r/pp1pbppp/2n5/3p4/6P1/4qN2/PP1N1R1P/R2Q2K1 w kq - 0 14")

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] != "d2c4"
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e79_rejects_false_queen_attack_qd1d4_from_live_loss(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    # After ...dxc4, AION played Qd4 and black captured it.
    board = chess.Board("r1b1k2r/pp1pbppp/2n5/8/2p3P1/4qN2/PP3R1P/R2Q2K1 w kq - 0 15")

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] != "d1d4"
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e79_still_triggers_queen_invasion_guard(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r1b2rk1/pp2bppp/4p3/4n3/2q5/1N6/PPQ3PP/R4R1K w - - 4 17")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e78_queen_invasion_threat_fast_selector"
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e79_opening_book_still_owns_start(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    selected = kernel._select_fast_live_move(chess.Board())

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"
