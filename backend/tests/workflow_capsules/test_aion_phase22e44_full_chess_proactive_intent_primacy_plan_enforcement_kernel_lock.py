from pathlib import Path

from backend.modules.aion_games.full_chess_proactive_intent_primacy_plan_enforcement_kernel import (
    run_full_chess_proactive_intent_primacy_plan_enforcement_kernel,
)


def test_phase22e44_replaces_passive_rook_drift_with_plan_move(tmp_path: Path):
    result = run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        forced_base_selected_move="d1d2",
        memory_path=tmp_path / "memory.json",
    )

    assert result.proactive_intent_checked is True
    assert result.passive_drift_detected is True
    assert result.proactive_plan_available is True
    assert result.proactive_override_applied is True
    assert result.final_selected_move != "d1d2"
    assert result.final_selected_move_is_legal is True


def test_phase22e44_keeps_good_development_move(tmp_path: Path):
    result = run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        forced_base_selected_move="g1f3",
        memory_path=tmp_path / "memory.json",
    )

    assert result.proactive_intent_checked is True
    assert result.passive_drift_detected is False
    assert result.proactive_override_applied is False
    assert result.final_selected_move == "g1f3"
    assert result.final_selected_move_is_legal is True


def test_phase22e44_keeps_tactical_capture(tmp_path: Path):
    result = run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
        input_fen="rnbqkbnr/ppp2ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 3",
        side_to_move="white",
        forced_base_selected_move="d4e5",
        memory_path=tmp_path / "memory.json",
    )

    assert result.final_selected_move == "d4e5"
    assert result.proactive_override_applied is False
    assert result.final_selected_move_is_legal is True


def test_phase22e44_memory_persists(tmp_path: Path):
    memory = tmp_path / "memory.json"

    first = run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        forced_base_selected_move="d1d2",
        memory_path=memory,
    )
    second = run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        forced_base_selected_move="d1d2",
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e44_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_proactive_intent_primacy_plan_enforcement_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        forced_base_selected_move="d1d2",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
