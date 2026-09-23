from pathlib import Path

from backend.modules.aion_games.full_chess_initiative_hygiene_guard_kernel import (
    run_full_chess_initiative_hygiene_guard_kernel,
)


def test_phase22e49_blocks_h2h4_under_initiative_pressure(tmp_path: Path):
    result = run_full_chess_initiative_hygiene_guard_kernel(
        input_fen="r1bk1bnr/pp2p1pp/2n2p2/2p3B1/4P3/2P2N2/PPP1BPPP/R3K2R w KQ - 0 8",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="initiative_pressure",
        memory_path=tmp_path / "memory.json",
    )

    assert result.initiative_hygiene_checked is True
    assert result.wing_pawn_lunge_detected is True
    assert result.wing_pawn_lunge_allowed is False
    assert result.initiative_hygiene_override_applied is True
    assert result.safe_alternative_found is True
    assert result.final_selected_move != "h2h4"
    assert result.final_selected_move_is_legal is True


def test_phase22e49_blocks_g2g4_under_initiative_pressure(tmp_path: Path):
    result = run_full_chess_initiative_hygiene_guard_kernel(
        input_fen="r1b2bnr/ppk1p1pp/2n2p2/2p3B1/4P2P/2P2N2/PPP1BPP1/R3K2R w KQ - 1 9",
        side_to_move="white",
        forced_base_selected_move="g2g4",
        forced_active_intent="initiative_pressure",
        memory_path=tmp_path / "memory.json",
    )

    assert result.wing_pawn_lunge_detected is True
    assert result.initiative_hygiene_override_applied is True
    assert result.final_selected_move != "g2g4"
    assert result.final_selected_move_is_legal is True


def test_phase22e49_allows_wing_pawn_capture(tmp_path: Path):
    result = run_full_chess_initiative_hygiene_guard_kernel(
        input_fen="8/8/8/6p1/7P/8/8/4K2k w - - 0 1",
        side_to_move="white",
        forced_base_selected_move="h4g5",
        forced_active_intent="initiative_pressure",
        memory_path=tmp_path / "memory.json",
    )

    assert result.wing_pawn_lunge_detected is False
    assert result.initiative_hygiene_override_applied is False
    assert result.final_selected_move == "h4g5"
    assert result.final_selected_move_is_legal is True


def test_phase22e49_non_initiative_passthrough(tmp_path: Path):
    result = run_full_chess_initiative_hygiene_guard_kernel(
        input_fen="r1bk1bnr/pp2p1pp/2n2p2/2p3B1/4P3/2P2N2/PPP1BPPP/R3K2R w KQ - 0 8",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="king_safety",
        memory_path=tmp_path / "memory.json",
    )

    assert result.active_intent != "initiative_pressure" or result.initiative_hygiene_checked is False
    assert result.final_selected_move_is_legal is True


def test_phase22e49_memory_persists(tmp_path: Path):
    memory = tmp_path / "memory.json"

    first = run_full_chess_initiative_hygiene_guard_kernel(
        input_fen="r1bk1bnr/pp2p1pp/2n2p2/2p3B1/4P3/2P2N2/PPP1BPPP/R3K2R w KQ - 0 8",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="initiative_pressure",
        memory_path=memory,
    )
    second = run_full_chess_initiative_hygiene_guard_kernel(
        input_fen="r1bk1bnr/pp2p1pp/2n2p2/2p3B1/4P3/2P2N2/PPP1BPPP/R3K2R w KQ - 0 8",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="initiative_pressure",
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e49_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_initiative_hygiene_guard_kernel(
        input_fen="r1bk1bnr/pp2p1pp/2n2p2/2p3B1/4P3/2P2N2/PPP1BPPP/R3K2R w KQ - 0 8",
        side_to_move="white",
        forced_base_selected_move="h2h4",
        forced_active_intent="initiative_pressure",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
