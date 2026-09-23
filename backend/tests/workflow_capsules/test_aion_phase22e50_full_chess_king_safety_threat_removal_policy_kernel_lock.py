from pathlib import Path

from backend.modules.aion_games.full_chess_king_safety_threat_removal_policy_kernel import (
    run_full_chess_king_safety_threat_removal_policy_kernel,
)


def test_phase22e50_replaces_passive_king_walk_with_threat_capture(tmp_path: Path):
    result = run_full_chess_king_safety_threat_removal_policy_kernel(
        input_fen="4k2r/8/8/8/8/8/8/4K2R w K - 0 1",
        side_to_move="white",
        forced_base_selected_move="e1f1",
        forced_active_intent="king_safety",
        memory_path=tmp_path / "memory.json",
    )

    assert result.king_safety_threat_removal_checked is True
    assert result.passive_king_walk_detected is True
    assert result.threat_removal_override_applied is True
    assert result.threat_removal_alternative_found is True
    assert result.final_selected_move == "h1h8"
    assert result.final_selected_move_is_legal is True


def test_phase22e50_keeps_non_passive_king_capture(tmp_path: Path):
    result = run_full_chess_king_safety_threat_removal_policy_kernel(
        input_fen="4k3/8/8/8/8/8/5q2/4K3 w - - 0 1",
        side_to_move="white",
        forced_base_selected_move="e1f2",
        forced_active_intent="king_safety",
        memory_path=tmp_path / "memory.json",
    )

    assert result.king_safety_threat_removal_checked is True
    assert result.passive_king_walk_detected is False
    assert result.threat_removal_override_applied is False
    assert result.final_selected_move == "e1f2"
    assert result.final_selected_move_is_legal is True


def test_phase22e50_non_king_safety_passthrough(tmp_path: Path):
    result = run_full_chess_king_safety_threat_removal_policy_kernel(
        input_fen="4k2r/8/8/8/8/8/8/4K2R w K - 0 1",
        side_to_move="white",
        forced_base_selected_move="e1f1",
        forced_active_intent="initiative_pressure",
        memory_path=tmp_path / "memory.json",
    )

    assert result.king_safety_threat_removal_checked is False
    assert result.threat_removal_override_applied is False
    assert result.final_selected_move_is_legal is True


def test_phase22e50_memory_persists(tmp_path: Path):
    memory = tmp_path / "memory.json"

    first = run_full_chess_king_safety_threat_removal_policy_kernel(
        input_fen="4k2r/8/8/8/8/8/8/4K2R w K - 0 1",
        side_to_move="white",
        forced_base_selected_move="e1f1",
        forced_active_intent="king_safety",
        memory_path=memory,
    )
    second = run_full_chess_king_safety_threat_removal_policy_kernel(
        input_fen="4k2r/8/8/8/8/8/8/4K2R w K - 0 1",
        side_to_move="white",
        forced_base_selected_move="e1f1",
        forced_active_intent="king_safety",
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e50_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_king_safety_threat_removal_policy_kernel(
        input_fen="4k2r/8/8/8/8/8/8/4K2R w K - 0 1",
        side_to_move="white",
        forced_base_selected_move="e1f1",
        forced_active_intent="king_safety",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
