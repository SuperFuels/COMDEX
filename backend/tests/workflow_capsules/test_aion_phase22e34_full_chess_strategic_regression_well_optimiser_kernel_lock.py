from pathlib import Path

from backend.modules.aion_games.full_chess_strategic_regression_well_optimiser_kernel import (
    run_full_chess_strategic_regression_well_optimiser_kernel,
)


def test_phase22e34_runs_full_well_stack(tmp_path: Path):
    result = run_full_chess_strategic_regression_well_optimiser_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.strategic_regression_well_active is True
    assert result.selected_move
    assert result.selected_move_is_legal is True
    assert result.component_summary["zugzwang_selected_move"]


def test_phase22e34_consumes_all_components(tmp_path: Path):
    result = run_full_chess_strategic_regression_well_optimiser_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["zugzwang_choice_architecture_consumed"] is True
    assert result.evidence["one_ply_blunder_guard_consumed"] is True
    assert result.evidence["opponent_threat_map_consumed"] is True
    assert result.evidence["passed_pawn_policy_consumed"] is True
    assert result.evidence["endgame_box_mate_net_consumed"] is True
    assert result.evidence["plan_continuity_memory_consumed"] is True
    assert result.evidence["rook_bishop_repetition_breaker_consumed"] is True


def test_phase22e34_prioritises_passed_pawn_promotion(tmp_path: Path):
    result = run_full_chess_strategic_regression_well_optimiser_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.passed_pawn_policy == "promote_now"
    assert result.selected_move == "a7a8q"
    assert result.selected_move_is_legal is True


def test_phase22e34_handles_repetition_context(tmp_path: Path):
    result = run_full_chess_strategic_regression_well_optimiser_kernel(
        input_fen="r2q4/1ppbp1k1/p2p2p1/8/2P3n1/2N5/PP3PPP/R1B1R2K w - - 2 21",
        side_to_move="white",
        repeated_moves=["f1e1", "e1g1", "g1e1", "e1g1"],
        repeated_squares=["e1", "g1", "e1", "g1"],
        memory_path=tmp_path / "memory.json",
    )

    assert result.repetition_detected is True
    assert result.selected_move_is_legal is True


def test_phase22e34_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_strategic_regression_well_optimiser_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_strategic_regression_well_optimiser_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_well_policy["kernel_run_count"] == 2


def test_phase22e34_boundary_no_engine_or_analysis(tmp_path: Path):
    result = run_full_chess_strategic_regression_well_optimiser_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "Strategic Regression Well Optimiser" in result.boundary_statement
