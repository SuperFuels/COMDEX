from pathlib import Path

from backend.modules.aion_games.full_chess_plan_continuity_memory_kernel import (
    run_full_chess_plan_continuity_memory_kernel,
)


def test_phase22e32_infers_passed_pawn_plan(tmp_path: Path):
    result = run_full_chess_plan_continuity_memory_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        candidate_move="a7a8q",
        memory_path=tmp_path / "memory.json",
    )

    assert result.plan_continuity_active is True
    assert result.current_plan == "convert_passed_pawn"
    assert result.move_supports_plan is True
    assert result.continuity_score > 0


def test_phase22e32_detects_mate_net_plan(tmp_path: Path):
    result = run_full_chess_plan_continuity_memory_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        candidate_move="d6c7",
        memory_path=tmp_path / "memory.json",
    )

    assert result.current_plan == "build_mate_net"
    assert result.candidate_move_is_legal is True


def test_phase22e32_penalises_illegal_candidate(tmp_path: Path):
    result = run_full_chess_plan_continuity_memory_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        candidate_move="a7a9q",
        memory_path=tmp_path / "memory.json",
    )

    assert result.candidate_move_is_legal is False
    assert result.move_breaks_plan is True
    assert result.continuity_score < 0


def test_phase22e32_memory_detects_plan_change(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_plan_continuity_memory_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        candidate_move="a7a8q",
        memory_path=memory_path,
    )
    second = run_full_chess_plan_continuity_memory_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        candidate_move="d6c7",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.previous_plan == "convert_passed_pawn"
    assert second.plan_changed is True


def test_phase22e32_explicit_plan_overrides_inference(tmp_path: Path):
    result = run_full_chess_plan_continuity_memory_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        candidate_move="d6c7",
        explicit_current_plan="force_zugzwang",
        memory_path=tmp_path / "memory.json",
    )

    assert result.current_plan == "force_zugzwang"


def test_phase22e32_boundary_no_engine_or_analysis(tmp_path: Path):
    result = run_full_chess_plan_continuity_memory_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        candidate_move="a7a8q",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "plan continuity memory" in result.boundary_statement
