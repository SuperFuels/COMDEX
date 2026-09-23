from pathlib import Path

import chess

from backend.modules.aion_games.full_chess_proactive_plan_primacy_intent_driver_kernel import (
    run_full_chess_proactive_plan_primacy_intent_driver_kernel,
)


def test_phase22e36_selects_proactive_opening_intent(tmp_path: Path):
    result = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.proactive_intent_driver_active is True
    assert result.active_intent in {"rapid_development", "center_control"}
    assert result.emergency_override_active is False
    assert result.recommended_intent_move_bias
    assert result.evidence["plan_primacy_enabled"] is True


def test_phase22e36_detects_passed_pawn_conversion_intent(tmp_path: Path):
    result = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.active_intent == "convert_passed_pawn"
    assert "promote" in result.recommended_intent_move_bias
    assert result.opponent_forced_to_react is True


def test_phase22e36_emergency_override_takes_priority(tmp_path: Path):
    result = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
        input_fen="4k3/8/8/8/8/8/4r3/4K3 w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.active_intent == "neutralise_critical_threat"
    assert result.emergency_override_active is True
    assert "escape_check" in result.recommended_intent_move_bias


def test_phase22e36_memory_tracks_intent_continuity(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.previous_intent == first.active_intent
    assert second.intent_changed is False
    assert second.final_intent_policy["kernel_run_count"] == 2


def test_phase22e36_records_intent_change_when_position_changes(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.active_intent != second.active_intent
    assert second.intent_changed is True
    assert second.final_intent_policy["intent_change_count"] >= 1


def test_phase22e36_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_proactive_plan_primacy_intent_driver_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
    assert "proactive plan primacy" in result.boundary_statement
