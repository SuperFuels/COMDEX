import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e75_opening_book_starts_with_d4(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")
    board = chess.Board()

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"


def test_phase22e75_against_d5_plays_nf3_not_bg5(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board()
    board.push(chess.Move.from_uci("d2d4"))
    board.push(chess.Move.from_uci("d7d5"))

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] == "g1f3"
    assert selected["selected_move"] != "c1g5"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"


def test_phase22e75_against_nf6_prefers_bf4_not_loose_bg5(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board()
    board.push(chess.Move.from_uci("d2d4"))
    board.push(chess.Move.from_uci("g8f6"))

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] == "c1f4"
    assert selected["selected_move"] != "c1g5"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"


def test_phase22e75_london_shell_castles_when_ready(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board()
    for move_uci in ["d2d4", "d7d5", "g1f3", "g8f6", "c1f4", "e7e6", "e2e3", "f8d6", "f1d3", "e8g8"]:
        move = chess.Move.from_uci(move_uci)
        assert move in board.legal_moves
        board.push(move)

    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] == "e1g1"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"
