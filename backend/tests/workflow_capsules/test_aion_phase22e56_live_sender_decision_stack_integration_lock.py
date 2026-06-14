import chess

from backend.modules.aion_games.full_chess_live_one_move_strategic_well_sender_kernel import (
    AionLiveOneMoveStrategicWellSenderKernel,
)


LEVEL8_FAILURE_FEN = "r1b1k2r/p4ppp/2p1p3/2P5/2Pq4/5P2/Pb4PP/R3K2R w KQkq - 0 15"


def test_phase22e56_live_sender_uses_opponent_reply_and_monte_carlo_stack(tmp_path):
    sender = AionLiveOneMoveStrategicWellSenderKernel(memory_path=tmp_path / "sender_memory.json")

    result = sender.run(
        game_id="dry_run_level8_stack_test",
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        target_level=8,
        explicit_live_send_authorized=False,
        human_operator_confirmed=False,
        live_game_stream_confirmed=False,
        one_move_gate_enabled=False,
        live_sender_enabled=False,
        allow_real_post=False,
        token="",
        task_name="phase22e56_live_sender_stack_test",
    )

    board = chess.Board(LEVEL8_FAILURE_FEN)

    assert result.evidence["phase22e56_live_sender_decision_stack_used"] is True
    assert result.evidence["phase22e54_opponent_reply_probability_tactical_exposure_guard_used"] is True
    assert result.evidence["phase22e55_monte_carlo_policy_value_seed_used"] is True
    assert result.selected_move_is_legal is True
    assert chess.Move.from_uci(result.selected_move) in board.legal_moves
    assert result.selected_source == "monte_carlo_policy_value_seed"


def test_phase22e56_live_sender_blocks_level8_h2h4_before_posting(tmp_path):
    sender = AionLiveOneMoveStrategicWellSenderKernel(memory_path=tmp_path / "sender_memory.json")

    result = sender.run(
        game_id="dry_run_level8_h2h4_block_test",
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        target_level=8,
        explicit_live_send_authorized=False,
        human_operator_confirmed=False,
        live_game_stream_confirmed=False,
        one_move_gate_enabled=False,
        live_sender_enabled=False,
        allow_real_post=False,
        token="",
        task_name="phase22e56_h2h4_block_test",
    )

    assert result.evidence["phase22e54_opponent_reply_probability_tactical_exposure_guard_used"] is True
    assert result.evidence["phase22e55_monte_carlo_policy_value_seed_used"] is True
    assert result.selected_move != "h2h4"
    assert result.move_post_attempted is False
    assert result.all_live_gates_passed is False


def test_phase22e56_level8_live_post_gate_remains_enabled_in_sender_source():
    from pathlib import Path

    text = Path("backend/modules/aion_games/full_chess_live_one_move_strategic_well_sender_kernel.py").read_text(encoding="utf-8")

    assert "target_level in {2, 3, 8}" in text
    assert "run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel" in text
    assert "run_full_chess_monte_carlo_policy_value_seed_kernel" in text
