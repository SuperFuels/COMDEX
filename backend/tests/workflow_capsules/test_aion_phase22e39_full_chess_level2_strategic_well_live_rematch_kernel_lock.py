from pathlib import Path

from backend.modules.aion_games.full_chess_level2_strategic_well_live_rematch_kernel import (
    run_full_chess_level2_strategic_well_live_rematch_kernel,
)


def test_phase22e39_dry_run_uses_22e38_sender_and_corrects_h2h4(tmp_path: Path):
    result = run_full_chess_level2_strategic_well_live_rematch_kernel(
        dry_run=True,
        network_enabled=False,
        memory_path=tmp_path / "memory.json",
    )

    assert result.dry_run is True
    assert result.network_enabled is False
    assert result.challenge_attempted is False
    assert result.challenge_created is False
    assert result.strategic_sender_used_count == 1
    assert result.first_base_well_move == "h2h4"
    assert result.first_selected_move == "g1f3"
    assert result.first_intent_override_applied is True
    assert result.evidence["phase22e38_sender_used"] is True
    assert result.evidence["phase22e25_recovery_enabled"] is True


def test_phase22e39_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_level2_strategic_well_live_rematch_kernel(
        dry_run=True,
        network_enabled=False,
        memory_path=memory_path,
    )
    second = run_full_chess_level2_strategic_well_live_rematch_kernel(
        dry_run=True,
        network_enabled=False,
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e39_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_level2_strategic_well_live_rematch_kernel(
        dry_run=True,
        network_enabled=False,
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "full Lichess Level-2 rematch loop" in result.boundary_statement
