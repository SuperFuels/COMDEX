import json
from pathlib import Path

from backend.modules.aion_games.full_chess_level2_strategic_well_live_post_game_review_kernel import (
    run_full_chess_level2_strategic_well_live_post_game_review_kernel,
)


def _write_sample_22e39(path: Path) -> None:
    payload = {
        "last_result": {
            "game_id": "sample_game",
            "final_status": "draw",
            "final_winner": "",
            "final_ply_count": 84,
            "aion_move_count": 43,
            "move_send_ok_count": 43,
            "post_400_recovery_count": 1,
            "first_base_well_move": "h2h4",
            "first_selected_move": "g1f3",
            "final_moves": [
                "g1f3", "c7c6", "b1c3", "e7e6", "e2e4", "d7d6",
                "d7c8r", "d8c7", "h2h4", "b7b8", "b8b7", "b7a7", "a7b7",
            ],
            "move_records": [
                {"ply_before": 0, "active_intent": "rapid_development", "base_well_selected_move": "h2h4", "selected_move": "g1f3", "intent_override_applied": True},
                {"ply_before": 14, "active_intent": "initiative_pressure", "base_well_selected_move": "h2h4", "selected_move": "h2h4", "intent_override_applied": False},
                {"ply_before": 22, "active_intent": "convert_passed_pawn", "base_well_selected_move": "d7c8r", "selected_move": "d7c8r", "intent_override_applied": False},
                {"ply_before": 36, "active_intent": "convert_passed_pawn", "base_well_selected_move": "g2g4", "selected_move": "g2g4", "intent_override_applied": False},
                {"ply_before": 38, "active_intent": "convert_passed_pawn", "base_well_selected_move": "f2f3", "selected_move": "f2f3", "intent_override_applied": False},
                {"ply_before": 52, "active_intent": "convert_passed_pawn", "base_well_selected_move": "a2a3", "selected_move": "a2a3", "intent_override_applied": False},
                {"ply_before": 54, "active_intent": "convert_passed_pawn", "base_well_selected_move": "f3f4", "selected_move": "f3f4", "intent_override_applied": False},
                {"ply_before": 40, "active_intent": "convert_passed_pawn", "base_well_selected_move": "c3d5", "selected_move": "c3d5", "intent_override_applied": False},
                {"ply_before": 44, "active_intent": "convert_passed_pawn", "base_well_selected_move": "h1h4", "selected_move": "h1h4", "intent_override_applied": False},
                {"ply_before": 56, "active_intent": "convert_passed_pawn", "base_well_selected_move": "a1d1", "selected_move": "a1d1", "intent_override_applied": False},
                {"ply_before": 58, "active_intent": "convert_passed_pawn", "base_well_selected_move": "d1d7", "selected_move": "d1d7", "intent_override_applied": False},
            ],
        }
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_phase22e40_reviews_22e39_failure_map(tmp_path: Path):
    source = tmp_path / "sample_22e39.json"
    _write_sample_22e39(source)

    result = run_full_chess_level2_strategic_well_live_post_game_review_kernel(
        source_path=source,
        memory_path=tmp_path / "memory.json",
    )

    assert result.opening_correction_confirmed is True
    assert result.first_base_well_move == "h2h4"
    assert result.first_selected_move == "g1f3"
    assert result.h2h4_returned_later is True
    assert result.non_queen_promotion_detected is True
    assert result.non_queen_promotion_move == "d7c8r"
    assert result.passed_pawn_scope_too_broad is True
    assert result.draw_conversion_failure is True
    assert "22E.41" in result.recommended_next_phases[0]


def test_phase22e40_memory_persists(tmp_path: Path):
    source = tmp_path / "sample_22e39.json"
    _write_sample_22e39(source)
    memory = tmp_path / "memory.json"

    first = run_full_chess_level2_strategic_well_live_post_game_review_kernel(
        source_path=source,
        memory_path=memory,
    )
    second = run_full_chess_level2_strategic_well_live_post_game_review_kernel(
        source_path=source,
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e40_boundary_no_engine_or_llm(tmp_path: Path):
    source = tmp_path / "sample_22e39.json"
    _write_sample_22e39(source)

    result = run_full_chess_level2_strategic_well_live_post_game_review_kernel(
        source_path=source,
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "post-game review" in result.boundary_statement
