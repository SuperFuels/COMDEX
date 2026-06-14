import chess

from backend.modules.aion_games.full_chess_live_one_move_strategic_well_sender_kernel import (
    AionLiveOneMoveStrategicWellSenderKernel,
)


def test_phase22e59_starting_position_prefers_professional_plan_move_before_monte_carlo(tmp_path):
    sender = AionLiveOneMoveStrategicWellSenderKernel(memory_path=tmp_path / "sender_memory.json")

    result = sender.run(
        game_id="dry_run_phase22e59_opening_plan",
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        target_level=8,
        explicit_live_send_authorized=False,
        human_operator_confirmed=False,
        live_game_stream_confirmed=False,
        one_move_gate_enabled=False,
        live_sender_enabled=False,
        allow_real_post=False,
        token="",
        task_name="phase22e59_opening_plan_test",
    )

    assert result.evidence["phase22e59_rolling_plan_live_sender_integration_used"] is True
    assert result.evidence["phase22e58_rolling_strategic_plan_used"] is True
    assert result.evidence["phase22e58_primary_plan"] == "rapid_development"
    assert result.evidence["phase22e58_selected_plan_move"] == "g1f3"
    assert result.evidence["phase22e59_plan_filtered_move"] == "g1f3"
    assert result.selected_move == "g1f3"
    assert result.selected_source in {"monte_carlo_policy_value_seed", "rolling_plan_monte_carlo_edge_knight_guard"}
    assert result.move_post_attempted is False


def test_phase22e59_blocks_edge_knight_opening_drift_in_live_sender_path(tmp_path):
    sender = AionLiveOneMoveStrategicWellSenderKernel(memory_path=tmp_path / "sender_memory.json")

    result = sender.run(
        game_id="dry_run_phase22e59_edge_knight_block",
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        target_level=8,
        explicit_live_send_authorized=False,
        human_operator_confirmed=False,
        live_game_stream_confirmed=False,
        one_move_gate_enabled=False,
        live_sender_enabled=False,
        allow_real_post=False,
        token="",
        task_name="phase22e59_edge_knight_block_test",
    )

    assert result.selected_move not in {"b1a3", "g1h3"}
    assert (
        result.evidence["phase22e59_rolling_plan_override_applied"] is True
        or result.evidence["phase22e59_monte_carlo_plan_guard_applied"] is True
    )
    assert result.selected_move_is_legal is True


def test_phase22e59_live_sender_source_contains_rolling_plan_before_monte_carlo():
    from pathlib import Path

    text = Path("backend/modules/aion_games/full_chess_live_one_move_strategic_well_sender_kernel.py").read_text(encoding="utf-8")

    plan_index = text.index("run_full_chess_rolling_strategic_plan_kernel(")
    mc_index = text.index("run_full_chess_monte_carlo_policy_value_seed_kernel(")

    assert plan_index < mc_index
    assert "phase22e59_rolling_plan_live_sender_integration_used" in text
    assert "phase22e58_selected_plan_move" in text
