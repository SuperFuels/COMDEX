import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22f1_observer_helper_reads_rook_back_rank_pressure(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("5rk1/pp3ppp/4p3/2b4b/5PP1/2P5/Pr6/7K w - - 3 27")
    observed = kernel._observer_strategy_loop_fast_move(board)

    assert observed.get("selected_move") in {m.uci() for m in board.legal_moves}
    assert observed.get("observer_mode") in {"survive", "defend", "balanced", "counterattack", "convert", "attack"}
    assert observed.get("observer_evidence")


def test_phase22f1_observer_helper_reads_level6_mate_net_position(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("2b2bk1/p1pp2q1/2n1pp2/2p3Nr/2N4P/8/P3nP1K/R4R2 w - - 0 28")
    observed = kernel._observer_strategy_loop_fast_move(board)

    assert observed.get("selected_move") in {m.uci() for m in board.legal_moves}
    assert observed.get("observer_evidence")


def test_phase22f1_does_not_override_opening_book_start(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    selected = kernel._select_fast_live_move(chess.Board())

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"


def test_phase22f1_promotion_guard_still_owns_rank_one_emergency(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r2qk2r/pp1n1pp1/2p4p/8/3PP3/b1Q2N2/bp3PPP/1R4K1 w kq - 0 19")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e80_passed_pawn_promotion_guard_fast_selector"
    assert selected["selected_move"] == "c3b2"
