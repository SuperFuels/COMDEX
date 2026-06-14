import chess

from backend.modules.aion_games.full_chess_live_one_move_strategic_well_sender_kernel import (
    AionLiveOneMoveStrategicWellSenderKernel,
)


def _get(result, *names):
    for name in names:
        if hasattr(result, name):
            return getattr(result, name)
    raise AttributeError(f"Missing expected result field. Tried: {names}")


def test_phase22e62_live_sender_uses_parallel_opponent_beam_router_with_no_live_post(tmp_path):
    memory_path = tmp_path / "phase22e62_live_sender_memory.json"

    result = AionLiveOneMoveStrategicWellSenderKernel(memory_path=memory_path).run(
        game_id="phase22e62-dry-run-no-live-post",
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        target_level=8,
        explicit_live_send_authorized=False,
        human_operator_confirmed=False,
        live_game_stream_confirmed=False,
        one_move_gate_enabled=False,
        live_sender_enabled=False,
        allow_real_post=False,
        token=None,
        task_name="phase22e62_live_sender_parallel_beam_router_no_live_post",
    )

    selected_move = _get(result, "selected_move", "final_selected_move", "move")
    evidence = _get(result, "evidence")
    selected_source = _get(result, "selected_source", "final_selected_source", "source")

    assert selected_move
    assert selected_source
    assert evidence["phase22e62_parallel_opponent_beam_router_live_sender_integration_used"] is True
    assert evidence["phase22e61_parallel_opponent_beam_router_used"] is True
    assert evidence["phase22e61_selected_move"]
    assert evidence["phase22e61_trace_hash"]
    assert result.selected_move_is_legal is True
    assert result.move_post_attempted is False
    assert result.move_post_succeeded is False
    assert selected_move not in {"b1a3", "g1h3"}

    # Safety boundary: this test must not be able to post a move.
    assert result.live_sender_enabled is False
    assert result.allow_real_post is False
    assert result.all_live_gates_passed is False
