import chess

from backend.modules.aion_games.full_chess_live_one_move_strategic_well_sender_kernel import (
    run_full_chess_live_one_move_strategic_well_sender_kernel,
)


def test_phase22e65_live_sender_blocks_qd5_qe4_qe2_corridor_before_post():
    fen = "r3k2r/p4ppp/2p5/3qp3/1b1n4/1P6/P4PbP/R1BQK2R w KQkq - 2 15"

    result = run_full_chess_live_one_move_strategic_well_sender_kernel(
        input_fen=fen,
        side_to_move="white",
        target_level=8,
        game_id="phase22e65-dry-run-no-post",
        explicit_live_send_authorized=False,
        human_operator_confirmed=False,
        live_game_stream_confirmed=False,
        one_move_gate_enabled=True,
        live_sender_enabled=False,
        allow_real_post=False,
        token="",
        task_name="phase22e65_live_sender_queen_intrusion_final_guard_lock",
    )

    ev = result.evidence

    assert result.selected_move_is_legal is True
    assert result.move_post_attempted is False

    assert ev["phase22e65_queen_intrusion_final_guard_used"] is True
    assert ev["phase22e65_queen_intrusion_override_applied"] is True
    assert ev["phase22e65_queen_intrusion_square"] == "d5"

    assert result.selected_source == "phase22e65_queen_intrusion_final_guard"
    assert result.selected_move != "c1d2"

    board = chess.Board(fen)
    move = chess.Move.from_uci(result.selected_move)
    assert move in board.legal_moves

    # Selected guard move must not permit an immediate one-ply mate reply.
    board.push(move)
    for reply in board.legal_moves:
        probe = board.copy(stack=False)
        probe.push(reply)
        assert not probe.is_checkmate()
