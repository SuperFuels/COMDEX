from pathlib import Path

from backend.modules.aion_games.full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel import (
    run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel,
)


def test_phase22e52_blocks_h2h4_under_neutralise_critical_threat(tmp_path: Path):
    result = run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
        input_fen="r1b2rk1/p1Pn1p1p/1p2p1p1/8/3P4/2P2P2/P1P4P/R2QKBq1 w Q - 0 15",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="neutralise_critical_threat",
        memory_path=tmp_path / "memory.json",
    )

    assert result.critical_threat_hygiene_checked is True
    assert result.wing_pawn_lunge_detected is True
    assert result.threat_hygiene_override_applied is True
    assert result.final_selected_move != "h2h4"
    assert result.final_selected_move_is_legal is True


def test_phase22e52_prioritises_capturing_intruding_queen(tmp_path: Path):
    result = run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4K3 w - - 0 1",
        side_to_move="white",
        forced_base_selected_move="e1f1",
        forced_active_intent="king_safety",
        memory_path=tmp_path / "memory.json",
    )

    assert result.queen_intrusion_detected is True
    assert result.queen_trap_or_expel_available is True
    assert result.queen_intrusion_override_applied is True
    assert result.threat_hygiene_override_applied is True
    assert result.final_selected_move_is_legal is True
    assert result.final_selected_move != "e1f1"


def test_phase22e52_non_critical_passthrough(tmp_path: Path):
    result = run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        forced_base_selected_move="g1f3",
        forced_active_intent="rapid_development",
        memory_path=tmp_path / "memory.json",
    )

    assert result.critical_threat_hygiene_checked is False
    assert result.threat_hygiene_override_applied is False
    assert result.final_selected_move_is_legal is True


def test_phase22e52_memory_persists(tmp_path: Path):
    memory = tmp_path / "memory.json"

    first = run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
        input_fen="r1b2rk1/p1Pn1p1p/1p2p1p1/8/3P4/2P2P2/P1P4P/R2QKBq1 w Q - 0 15",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="neutralise_critical_threat",
        memory_path=memory,
    )
    second = run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
        input_fen="r1b2rk1/p1Pn1p1p/1p2p1p1/8/3P4/2P2P2/P1P4P/R2QKBq1 w Q - 0 15",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="neutralise_critical_threat",
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e52_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4K3 w - - 0 1",
        side_to_move="white",
        forced_base_selected_move="e1f1",
        forced_active_intent="king_safety",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
