import chess

from backend.modules.aion_games.full_chess_live_one_move_strategic_well_sender_kernel import (
    AionLiveOneMoveStrategicWellSenderKernel,
)


def test_phase22e63_router_override_survives_monte_carlo(tmp_path):
    result = AionLiveOneMoveStrategicWellSenderKernel(
        memory_path=tmp_path / "phase22e63_memory.json"
    ).run(
        game_id="phase22e63-router-survives-monte-carlo",
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        target_level=8,
        explicit_live_send_authorized=False,
        human_operator_confirmed=False,
        live_game_stream_confirmed=False,
        one_move_gate_enabled=False,
        live_sender_enabled=False,
        allow_real_post=False,
        token=None,
        task_name="phase22e63_router_survives_monte_carlo",
    )

    evidence = result.evidence

    assert evidence["phase22e61_parallel_opponent_beam_router_used"] is True
    assert evidence["phase22e62_parallel_opponent_beam_router_live_sender_integration_used"] is True
    assert evidence["phase22e62_router_override_applied"] is True
    assert evidence["phase22e63_router_survived_monte_carlo"] is True

    assert result.selected_move == evidence["phase22e61_selected_move"]
    assert result.selected_source == "phase22e61_parallel_opponent_beam_router_sqi_collapse"
    assert chess.Move.from_uci(result.selected_move) in chess.Board(result.input_fen).legal_moves

    assert result.move_post_attempted is False
    assert result.move_post_succeeded is False
    assert result.all_live_gates_passed is False
