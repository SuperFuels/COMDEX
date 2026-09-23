from pathlib import Path

from backend.modules.aion_games.full_chess_dynamic_intent_switching_plan_strength_kernel import (
    run_full_chess_dynamic_intent_switching_plan_strength_kernel,
)


def test_phase22e46_switches_rapid_development_to_initiative_when_development_complete(tmp_path: Path):
    result = run_full_chess_dynamic_intent_switching_plan_strength_kernel(
        input_fen="r1b1kbnr/pp3ppp/1qnpp3/2p5/3PP3/2N2N2/PPP1BPPP/R1BQK2R w KQkq - 1 6",
        side_to_move="white",
        forced_base_selected_move="c1g5",
        forced_active_intent="rapid_development",
        memory_path=tmp_path / "memory.json",
    )

    assert result.dynamic_intent_checked is True
    assert result.development_complete is True
    assert result.intent_switch_applied is True
    assert result.previous_active_intent == "rapid_development"
    assert result.active_intent == "initiative_pressure"
    assert result.final_selected_move_is_legal is True


def test_phase22e46_switches_material_advantage_to_simplify_when_ahead(tmp_path: Path):
    result = run_full_chess_dynamic_intent_switching_plan_strength_kernel(
        input_fen="rnb1kbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKBQR w KQkq - 0 3",
        side_to_move="white",
        forced_base_selected_move="b1c3",
        forced_active_intent="initiative_pressure",
        memory_path=tmp_path / "memory.json",
    )

    assert result.material_delta_cp >= 500
    assert result.intent_switch_applied is True
    assert result.active_intent == "simplify_when_ahead"
    assert result.final_selected_move_is_legal is True


def test_phase22e46_keeps_current_intent_when_plan_strength_ok(tmp_path: Path):
    result = run_full_chess_dynamic_intent_switching_plan_strength_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        forced_base_selected_move="g1f3",
        forced_active_intent="rapid_development",
        memory_path=tmp_path / "memory.json",
    )

    assert result.development_complete is False
    assert result.intent_switch_applied is False
    assert result.active_intent == "rapid_development"
    assert result.final_selected_move == "g1f3"
    assert result.final_selected_move_is_legal is True


def test_phase22e46_memory_persists(tmp_path: Path):
    memory = tmp_path / "memory.json"

    first = run_full_chess_dynamic_intent_switching_plan_strength_kernel(
        input_fen="r1b1kbnr/pp3ppp/1qnpp3/2p5/3PP3/2N2N2/PPP1BPPP/R1BQK2R w KQkq - 1 6",
        side_to_move="white",
        forced_base_selected_move="c1g5",
        forced_active_intent="rapid_development",
        memory_path=memory,
    )
    second = run_full_chess_dynamic_intent_switching_plan_strength_kernel(
        input_fen="r1b1kbnr/pp3ppp/1qnpp3/2p5/3PP3/2N2N2/PPP1BPPP/R1BQK2R w KQkq - 1 6",
        side_to_move="white",
        forced_base_selected_move="c1g5",
        forced_active_intent="rapid_development",
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e46_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_dynamic_intent_switching_plan_strength_kernel(
        input_fen="r1b1kbnr/pp3ppp/1qnpp3/2p5/3PP3/2N2N2/PPP1BPPP/R1BQK2R w KQkq - 1 6",
        side_to_move="white",
        forced_base_selected_move="c1g5",
        forced_active_intent="rapid_development",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
