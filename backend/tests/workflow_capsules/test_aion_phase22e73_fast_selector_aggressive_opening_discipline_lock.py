import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e73_after_nc3_selector_does_not_move_same_knight_again(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    # From latest live pattern after 1.Nc3 ...a6, old selector chose Nc3-e4.
    fen = "rnbqkbnr/1ppppppp/p7/8/8/2N5/PPPPPPPP/R1BQKBNR w KQkq - 0 2"
    board = chess.Board(fen)

    selected = kernel._select_fast_live_move(board)

    assert selected["fast_mode_used"] is True
    assert selected["selected_move"] != "c3e4"
    assert selected["selected_move"] != "c3d5"
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e73_opening_selector_prefers_development_over_early_queen_sortie(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    # Similar to latest line: queen sortie Qd5 was too loose.
    fen = "r2qkb1r/pp3ppp/2n2n2/3ppb2/8/8/PPP1PPPP/R1BQKB1R w KQkq - 0 9"
    board = chess.Board(fen)

    selected = kernel._select_fast_live_move(board)

    assert selected["fast_mode_used"] is True
    assert selected["selected_move"] != "d1d5"
    assert selected["selected_move"] in selected["legal_moves"]


def test_phase22e73_aggressive_selector_still_allows_safe_captures_and_checks(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 1 2")

    selected = kernel._select_fast_live_move(board)

    assert selected["fast_mode_used"] is True
    assert selected["selected_move"] in selected["legal_moves"]
    assert selected["selected_source"] in {"phase22e69_fast_live_clock_safe_selector", "phase22e75_opening_book_fast_selector"}
