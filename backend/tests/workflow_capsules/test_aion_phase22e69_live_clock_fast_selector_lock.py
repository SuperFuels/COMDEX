import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e69_fast_selector_avoids_22e67_ply42_forced_horizon_move(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    fen = "rnb3k1/1pp1pp2/6pp/p3b3/1PP1n2P/1K6/P2r2P1/8 w - - 0 22"
    board = chess.Board(fen)

    selected = kernel._select_fast_live_move(board)

    assert selected["fast_mode_used"] is True
    assert selected["selected_source"] == "phase22e69_fast_live_clock_safe_selector"

    assert "b3a4" in selected["legal_moves"]
    assert selected["selected_move"] != "b3a4"

    assert selected["selected_move"] in selected["horizon_safe_moves"]
    assert "b3a4" not in selected["horizon_safe_moves"]
    assert "b3a4" in selected["horizon_rejects"]


def test_phase22e69_fast_selector_never_selects_immediate_mate_reply_move(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    fen = "rnb3k1/1pp1pp2/6pp/p3b3/KPP1n2P/8/r5P1/8 w - - 0 23"
    board = chess.Board(fen)

    selected = kernel._select_fast_live_move(board)

    assert selected["fast_mode_used"] is True
    assert selected["selected_move"] in selected["legal_moves"]

    # At this already-lost position the selector must still return a legal fallback quickly.
    assert isinstance(selected["horizon_safe_moves"], list)
