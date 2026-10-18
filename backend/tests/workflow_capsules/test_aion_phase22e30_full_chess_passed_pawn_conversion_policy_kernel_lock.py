from pathlib import Path

from backend.modules.aion_games.full_chess_passed_pawn_conversion_policy_kernel import (
    run_full_chess_passed_pawn_conversion_policy_kernel,
)


def test_phase22e30_detects_passed_pawn_and_push(tmp_path: Path):
    result = run_full_chess_passed_pawn_conversion_policy_kernel(
        input_fen="8/8/8/8/8/P7/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.passed_pawn_policy_active is True
    assert result.own_passed_pawn_count == 1
    assert result.recommended_policy in {"push_passed_pawn", "support_passed_pawn"}
    assert result.best_pawn["is_passed"] is True


def test_phase22e30_recommends_promotion_when_available(tmp_path: Path):
    result = run_full_chess_passed_pawn_conversion_policy_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.recommended_policy == "promote_now"
    assert result.recommended_move.endswith("q")
    assert result.recommended_move_is_legal is True


def test_phase22e30_detects_enemy_promotion_threat(tmp_path: Path):
    result = run_full_chess_passed_pawn_conversion_policy_kernel(
        input_fen="4K2k/8/8/8/8/8/p7/8 w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.enemy_passed_pawn_count == 1
    assert result.enemy_promotion_threat_found is True
    assert result.recommended_policy == "stop_enemy_promotion"


def test_phase22e30_no_passed_pawn_continues_normal(tmp_path: Path):
    result = run_full_chess_passed_pawn_conversion_policy_kernel(
        input_fen="8/8/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.own_passed_pawn_count == 0
    assert result.recommended_policy == "continue_normal_play"


def test_phase22e30_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_passed_pawn_conversion_policy_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_passed_pawn_conversion_policy_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_conversion_policy["kernel_run_count"] == 2


def test_phase22e30_boundary_no_engine_or_analysis(tmp_path: Path):
    result = run_full_chess_passed_pawn_conversion_policy_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "passed pawn conversion policy" in result.boundary_statement
