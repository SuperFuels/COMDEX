import chess

from backend.modules.aion_games.full_chess_live_one_move_strategic_well_sender_kernel import (
    run_full_chess_live_one_move_strategic_well_sender_kernel,
)


def _allows_immediate_mate_reply(fen: str, move_uci: str) -> bool:
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)
    assert move in board.legal_moves
    board.push(move)

    for reply in board.legal_moves:
        probe = board.copy(stack=False)
        probe.push(reply)
        if probe.is_checkmate():
            return True
    return False


def _safe_evasions(fen: str) -> list[str]:
    board = chess.Board(fen)
    safe = []
    for move in board.legal_moves:
        probe = board.copy(stack=False)
        probe.push(move)
        allows_mate = False
        for reply in probe.legal_moves:
            reply_probe = probe.copy(stack=False)
            reply_probe.push(reply)
            if reply_probe.is_checkmate():
                allows_mate = True
                break
        if not allows_mate:
            safe.append(move.uci())
    return safe


def test_phase22e66_move16_position_is_already_forced_mate_corridor():
    fen = "r3k2r/p4ppp/2p5/4p3/1b1nq3/1P6/P2B1PbP/R2QK2R w KQkq - 4 16"

    assert _allows_immediate_mate_reply(fen, "d1e2") is True
    assert _safe_evasions(fen) == []

    result = run_full_chess_live_one_move_strategic_well_sender_kernel(
        input_fen=fen,
        side_to_move="white",
        target_level=8,
        game_id="phase22e66-dry-run-no-post",
        explicit_live_send_authorized=False,
        human_operator_confirmed=False,
        live_game_stream_confirmed=False,
        one_move_gate_enabled=True,
        live_sender_enabled=False,
        allow_real_post=False,
        token="",
        task_name="phase22e66_live_sender_immediate_mate_reply_guard_lock",
    )

    ev = result.evidence

    assert result.move_post_attempted is False
    assert result.selected_move_is_legal is True

    assert ev["phase22e66_immediate_mate_reply_guard_used"] is True
    assert ev["phase22e66_immediate_mate_reply_detected"] is True
    assert ev["phase22e66_immediate_mate_reply_move"] == "e4e2"

    # No safe legal alternative exists here; 22E.65 must prevent this position earlier.
    assert ev["phase22e66_guard_override_applied"] is False
    assert ev["phase22e66_guard_selected_move"] == ""


def test_phase22e65_prevents_reaching_move16_corridor_at_move15():
    fen = "r3k2r/p4ppp/2p5/3qp3/1b1n4/1P6/P4PbP/R1BQK2R w KQkq - 2 15"

    result = run_full_chess_live_one_move_strategic_well_sender_kernel(
        input_fen=fen,
        side_to_move="white",
        target_level=8,
        game_id="phase22e66-dry-run-no-post-move15",
        explicit_live_send_authorized=False,
        human_operator_confirmed=False,
        live_game_stream_confirmed=False,
        one_move_gate_enabled=True,
        live_sender_enabled=False,
        allow_real_post=False,
        token="",
        task_name="phase22e66_live_sender_prevents_move16_corridor_lock",
    )

    ev = result.evidence

    assert result.move_post_attempted is False
    assert result.selected_source == "phase22e65_queen_intrusion_final_guard"
    assert result.selected_move == "d1d2"
    assert ev["phase22e65_queen_intrusion_final_guard_used"] is True
    assert ev["phase22e65_queen_intrusion_override_applied"] is True
    assert ev["phase22e65_queen_intrusion_square"] == "d5"
