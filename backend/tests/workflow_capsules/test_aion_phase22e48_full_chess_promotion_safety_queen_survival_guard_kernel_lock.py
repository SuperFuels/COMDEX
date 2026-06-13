from pathlib import Path

from backend.modules.aion_games.full_chess_promotion_safety_queen_survival_guard_kernel import (
    run_full_chess_promotion_safety_queen_survival_guard_kernel,
)


def test_phase22e48_detects_unsafe_promoted_queen_capture(tmp_path: Path):
    result = run_full_chess_promotion_safety_queen_survival_guard_kernel(
        input_fen="r7/1pk1p1P1/8/p1P5/3b1Pn1/n4K2/8/6r1 w - - 0 28",
        side_to_move="white",
        forced_base_selected_move="g7g8q",
        forced_active_intent="convert_passed_pawn",
        memory_path=tmp_path / "memory.json",
    )

    assert result.promotion_safety_checked is True
    assert result.promotion_move_detected is True
    assert result.promoted_piece_square == "g8"
    assert result.promoted_piece_immediately_capturable is True
    assert result.promotion_survival_override_applied is True
    assert result.safe_alternative_found is True
    assert result.final_selected_move != "g7g8q"
    assert result.final_selected_move_is_legal is True


def test_phase22e48_keeps_safe_promotion(tmp_path: Path):
    result = run_full_chess_promotion_safety_queen_survival_guard_kernel(
        input_fen="8/6P1/8/8/8/4K3/8/6k1 w - - 0 1",
        side_to_move="white",
        forced_base_selected_move="g7g8q",
        forced_active_intent="convert_passed_pawn",
        memory_path=tmp_path / "memory.json",
    )

    assert result.promotion_safety_checked is True
    assert result.promotion_move_detected is True
    assert result.promoted_piece_immediately_capturable is False
    assert result.promotion_survival_override_applied is False
    assert result.final_selected_move == "g7g8q"
    assert result.final_selected_move_is_legal is True


def test_phase22e48_non_promotion_passthrough(tmp_path: Path):
    result = run_full_chess_promotion_safety_queen_survival_guard_kernel(
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        forced_base_selected_move="g1f3",
        forced_active_intent="rapid_development",
        memory_path=tmp_path / "memory.json",
    )

    assert result.promotion_safety_checked is False
    assert result.promotion_move_detected is False
    assert result.final_selected_move == "g1f3"
    assert result.final_selected_move_is_legal is True


def test_phase22e48_memory_persists(tmp_path: Path):
    memory = tmp_path / "memory.json"

    first = run_full_chess_promotion_safety_queen_survival_guard_kernel(
        input_fen="r7/1pk1p1P1/8/p1P5/3b1Pn1/n4K2/8/6r1 w - - 0 28",
        side_to_move="white",
        forced_base_selected_move="g7g8q",
        forced_active_intent="convert_passed_pawn",
        memory_path=memory,
    )
    second = run_full_chess_promotion_safety_queen_survival_guard_kernel(
        input_fen="r7/1pk1p1P1/8/p1P5/3b1Pn1/n4K2/8/6r1 w - - 0 28",
        side_to_move="white",
        forced_base_selected_move="g7g8q",
        forced_active_intent="convert_passed_pawn",
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e48_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_promotion_safety_queen_survival_guard_kernel(
        input_fen="r7/1pk1p1P1/8/p1P5/3b1Pn1/n4K2/8/6r1 w - - 0 28",
        side_to_move="white",
        forced_base_selected_move="g7g8q",
        forced_active_intent="convert_passed_pawn",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
