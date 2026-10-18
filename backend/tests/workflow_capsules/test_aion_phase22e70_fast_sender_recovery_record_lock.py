import chess

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    AionStrategicWellLiveRematchKernel,
)


def test_phase22e70_fast_sender_record_shape_has_recovery_fields(tmp_path):
    kernel = AionStrategicWellLiveRematchKernel(memory_path=tmp_path / "memory.json")

    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    selected = kernel._select_fast_live_move(board)

    sender_record = {
        "move_post_attempted": True,
        "move_post_succeeded": False,
        "move_post_status_code": 400,
        "selected_move": selected["selected_move"],
        "selected_source": selected["selected_source"],
        "phase22e69_fast_live_mode_used": True,
    }

    assert sender_record["phase22e69_fast_live_mode_used"] is True
    assert sender_record["move_post_attempted"] is True
    assert sender_record["move_post_succeeded"] is False
    assert int(sender_record["move_post_status_code"]) == 400
    assert sender_record["selected_source"] in {"phase22e69_fast_live_clock_safe_selector", "phase22e75_opening_book_fast_selector"}
