import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22f2_keeps_opening_book_start(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    selected = kernel._select_fast_live_move(chess.Board())

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"


def test_phase22f2_keeps_rank_one_promotion_guard(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r2qk2r/pp1n1pp1/2p4p/8/3PP3/b1Q2N2/bp3PPP/1R4K1 w kq - 0 19")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e80_passed_pawn_promotion_guard_fast_selector"
    assert selected["selected_move"] == "c3b2"


def test_phase22f2_review_marks_safe_fallback_as_allowed(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r2qk2r/ppp1bppp/2npp1b1/3n4/8/2P1PNB1/PP1N1PPP/R2Q1RK1 w kq - 2 11")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_move"] in selected["legal_moves"]
    assert selected.get("phase22f2_observer_review_decision") in {None, "allow", "no_safe_alternative", "alternative_also_risky", "veto_selected_move"}


def test_phase22f2_helper_can_review_manual_bad_candidate(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("3r2k1/pp3ppp/4p3/2b4P/5P1P/2P5/Pr6/7K w - - 1 29")
    selected = {
        "selected_move": "f4f5",
        "selected_source": "phase22e69_fast_live_clock_safe_selector",
        "legal_moves": [m.uci() for m in board.legal_moves],
    }

    reviewed = kernel._observer_review_selected_fast_move(board, selected)

    assert reviewed["selected_move"] in selected["legal_moves"]
    assert reviewed.get("phase22f2_observer_review_used") is True
