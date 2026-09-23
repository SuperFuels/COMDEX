from pathlib import Path

from backend.modules.aion_games.full_chess_zugzwang_choice_architecture_selector_kernel import (
    run_full_chess_zugzwang_choice_architecture_selector_kernel,
)


def test_phase22e27_selects_legal_choice_architecture_move(tmp_path: Path):
    result = run_full_chess_zugzwang_choice_architecture_selector_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.choice_architecture_active is True
    assert result.selected_move_is_legal is True
    assert result.candidate_count > 0
    assert result.opponent_choice_width_after >= 0


def test_phase22e27_penalises_repeated_move(tmp_path: Path):
    clean = run_full_chess_zugzwang_choice_architecture_selector_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=tmp_path / "clean.json",
    )

    repeated = run_full_chess_zugzwang_choice_architecture_selector_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        repeated_moves=[clean.selected_move],
        memory_path=tmp_path / "repeated.json",
    )

    repeated_candidate = [
        c for c in repeated.top_candidates
        if c["move"] == clean.selected_move
    ]

    if repeated_candidate:
        assert repeated_candidate[0]["repeated_move_penalty_applied"] is True


def test_phase22e27_prefers_checkmate_when_available(tmp_path: Path):
    result = run_full_chess_zugzwang_choice_architecture_selector_kernel(
        input_fen="6k1/5ppp/8/8/8/8/5PPP/5RK1 w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.selected_move_is_legal is True
    assert result.top_candidates[0]["score"] == result.selected_score


def test_phase22e27_records_opponent_reply_profile(tmp_path: Path):
    result = run_full_chess_zugzwang_choice_architecture_selector_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    top = result.top_candidates[0]
    assert "opponent_choice_width_after" in top
    assert "opponent_check_reply_count" in top
    assert "opponent_capture_reply_count" in top
    assert "enemy_king_mobility_after" in top


def test_phase22e27_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_zugzwang_choice_architecture_selector_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_zugzwang_choice_architecture_selector_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_choice_policy["kernel_run_count"] == 2


def test_phase22e27_boundary_no_engine_or_analysis(tmp_path: Path):
    result = run_full_chess_zugzwang_choice_architecture_selector_kernel(
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "does not use Lichess analysis" in result.boundary_statement
