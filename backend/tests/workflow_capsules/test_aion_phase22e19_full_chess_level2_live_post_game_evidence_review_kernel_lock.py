import json
from pathlib import Path

from backend.modules.aion_games.full_chess_level2_live_post_game_evidence_review_kernel import (
    run_full_chess_level2_live_post_game_evidence_review_kernel,
)


def _write_fixture(path: Path) -> None:
    payload = {
        "phase": "22E.18",
        "run_type": "full_level2_live_rerun",
        "game_id": "Jh3hn2ru",
        "full_id": "Jh3hn2ruYUQW",
        "aion_colour": "white",
        "final_status": "outoftime",
        "final_winner": "black",
        "final_moves": [
            "e2e4", "e7e5", "d2d4", "e5d4", "g1f3", "b8c6",
            "f3g5", "h7h6", "g5f7", "e8f7",
            "c2c4", "d8f6", "d1h5", "f7e7", "h5c5", "d7d6",
            "c5d6", "e7e8", "b1c3", "d4c3", "d6f6", "g8e7",
            "f6f8", "e8d7", "f8h8", "c6d4", "h8c8", "a8c8",
            "b2c3", "d4e6", "h1g1", "e7c6", "g1h1", "c6e5",
            "e1d1", "e6c5", "f1e2", "c8e8", "e2g4", "d7e7",
            "g4c8", "e8f8", "c8b7", "f8d8", "d1e1", "c5d3",
            "e1f1", "e5c4", "f1g1", "d3c1", "a1c1", "c4d6",
            "b7d5", "d8e8", "d5g8", "e7f6", "c1d1", "e8g8",
            "d1d6", "c7d6", "c3c4", "g8c8", "e4e5", "f6e7",
            "e5d6", "e7e6", "d6d7", "c8b8", "d7d8q", "b8b4",
            "d8g8", "e6e7", "g8g7", "e7d6", "g7h6", "d6c7",
            "h6h7", "c7d6", "h7h8", "d6e6", "h8e8", "e6f5",
            "e8c8", "f5f4", "c8c7", "f4f5", "c7c5", "f5e4",
            "c5e7", "e4d3", "e7e5", "b4a4", "e5d5", "d3c2",
            "d5g8", "c2c3", "g8h8", "c3d3", "h8d8", "d3c4",
            "d8c7", "c4b5", "c7c5", "b5a6", "c5d6", "a6b5",
            "d6b8", "b5a5", "b8a7", "a5b5", "a7d7", "b5a6",
            "d7d5", "a6b6", "d5d6", "b6a7", "d6b8", "a7a6",
            "b8d6", "a6b7",
        ],
        "final_ply_count": 120,
        "aion_move_count": 61,
        "move_send_ok_count": 61,
        "move_records": [
            {"move_post_succeeded": True, "selected_move_is_legal": True}
            for _ in range(61)
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_phase22e19_locks_live_level2_result(tmp_path: Path):
    evidence_path = tmp_path / "22e18.json"
    _write_fixture(evidence_path)

    result = run_full_chess_level2_live_post_game_evidence_review_kernel(
        evidence_path=evidence_path,
        memory_path=tmp_path / "memory.json",
    )

    assert result.game_id == "Jh3hn2ru"
    assert result.full_id == "Jh3hn2ruYUQW"
    assert result.final_status == "outoftime"
    assert result.final_winner == "black"
    assert result.aion_move_count == 61
    assert result.move_send_ok_count == 61
    assert result.all_aion_sends_succeeded is True


def test_phase22e19_detects_promotion_and_zero_illegal_moves(tmp_path: Path):
    evidence_path = tmp_path / "22e18.json"
    _write_fixture(evidence_path)

    result = run_full_chess_level2_live_post_game_evidence_review_kernel(
        evidence_path=evidence_path,
        memory_path=tmp_path / "memory.json",
    )

    assert result.illegal_move_count == 0
    assert result.promoted_move_detected is True
    assert result.promoted_move == "d7d8q"


def test_phase22e19_names_failure_mode_shift(tmp_path: Path):
    evidence_path = tmp_path / "22e18.json"
    _write_fixture(evidence_path)

    result = run_full_chess_level2_live_post_game_evidence_review_kernel(
        evidence_path=evidence_path,
        memory_path=tmp_path / "memory.json",
    )

    assert result.old_failure_mode == "mate_collapse_or_early_tactical_collapse"
    assert result.new_failure_mode == "outoftime_after_long_queen_endgame_repetition"
    assert result.failure_review["primary_failure"] == "clock_loss"
    assert result.failure_review["secondary_failure"] == "queen_endgame_conversion_failure"


def test_phase22e19_next_patch_targets_queen_and_clock(tmp_path: Path):
    evidence_path = tmp_path / "22e18.json"
    _write_fixture(evidence_path)

    result = run_full_chess_level2_live_post_game_evidence_review_kernel(
        evidence_path=evidence_path,
        memory_path=tmp_path / "memory.json",
    )

    assert "queen_endgame_conversion_kernel" in result.next_patch_targets
    assert "clock_pressure_override" in result.next_patch_targets
    assert result.evidence["requires_queen_endgame_patch"] is True
    assert result.evidence["requires_clock_pressure_patch"] is True


def test_phase22e19_memory_persists(tmp_path: Path):
    evidence_path = tmp_path / "22e18.json"
    memory_path = tmp_path / "memory.json"
    _write_fixture(evidence_path)

    first = run_full_chess_level2_live_post_game_evidence_review_kernel(
        evidence_path=evidence_path,
        memory_path=memory_path,
    )
    second = run_full_chess_level2_live_post_game_evidence_review_kernel(
        evidence_path=evidence_path,
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_review_policy["kernel_run_count"] == 2


def test_phase22e19_boundary_no_live_or_engine_calls(tmp_path: Path):
    evidence_path = tmp_path / "22e18.json"
    _write_fixture(evidence_path)

    result = run_full_chess_level2_live_post_game_evidence_review_kernel(
        evidence_path=evidence_path,
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish_by_aion"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "does not call Lichess" in result.boundary_statement
