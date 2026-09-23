import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e78_triggers_when_black_queen_invades_near_castled_king(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r1b2rk1/pp2bppp/4p3/4n3/2q5/1N6/PPQ3PP/R4R1K w - - 4 17")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] == "phase22e78_queen_invasion_threat_fast_selector"
    assert selected["selected_move"] in selected["legal_moves"]
    assert selected["phase22e78_queen_square"] == "c4"


def test_phase22e78_does_not_trigger_old_e1_queen_corridor_lock(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r1b1kbnr/1p3ppp/p7/4n3/4P3/8/PqP2PPP/R3KB1R w KQkq - 0 12")
    selected = kernel._select_fast_live_move(board)

    assert selected["selected_source"] != "phase22e78_queen_invasion_threat_fast_selector"
    assert "f1a6" in selected["horizon_rejects"]


def test_phase22e78_prefers_addressing_invading_queen_not_rook_raid(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("r1b2rk1/pp2bppp/4p3/4n3/2q5/1N6/PPQ3PP/R4R1K w - - 4 17")
    raid = kernel._queen_invasion_threat_fast_move(board)

    assert raid["selected_move"] != "f1f7"
    assert raid["selected_move"] in [move.uci() for move in board.legal_moves]
    assert any(
        bit in raid["strategy_plan"]
        for bit in {
            "capture_invading_queen",
            "attack_invading_queen",
            "force_check",
            "reject_rook_raid_during_queen_invasion",
        }
    )


def test_phase22e78_opening_book_still_owns_start(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    selected = kernel._select_fast_live_move(chess.Board())

    assert selected["selected_move"] == "d2d4"
    assert selected["selected_source"] == "phase22e75_opening_book_fast_selector"
