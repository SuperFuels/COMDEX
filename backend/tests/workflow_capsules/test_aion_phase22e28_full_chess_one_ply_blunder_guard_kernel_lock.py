from pathlib import Path

from backend.modules.aion_games.full_chess_one_ply_blunder_guard_kernel import (
    run_full_chess_one_ply_blunder_guard_kernel,
)


def test_phase22e28_rejects_illegal_candidate(tmp_path: Path):
    result = run_full_chess_one_ply_blunder_guard_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        side_to_move="white",
        candidate_move="e1e8",
        memory_path=tmp_path / "memory.json",
    )

    assert result.candidate_move_is_legal is False
    assert result.safe_to_send is False
    assert result.move_rejected_as_blunder is True


def test_phase22e28_rejects_candidate_that_allows_mate_or_major_reply(tmp_path: Path):
    result = run_full_chess_one_ply_blunder_guard_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        side_to_move="white",
        candidate_move="f1f2",
        max_allowed_reply_score=900,
        memory_path=tmp_path / "memory.json",
    )

    assert result.blunder_guard_active is True
    assert result.worst_reply_score > result.max_allowed_reply_score
    assert result.move_rejected_as_blunder is True
    assert result.safe_to_send is False


def test_phase22e28_allows_quiet_safe_king_move(tmp_path: Path):
    result = run_full_chess_one_ply_blunder_guard_kernel(
        input_fen="8/8/8/8/8/8/5k2/4K3 w - - 0 1",
        side_to_move="white",
        candidate_move="e1d1",
        max_allowed_reply_score=900,
        memory_path=tmp_path / "memory.json",
    )

    assert result.candidate_move_is_legal is True
    assert result.safe_to_send is True
    assert result.move_rejected_as_blunder is False


def test_phase22e28_reports_safest_alternative(tmp_path: Path):
    result = run_full_chess_one_ply_blunder_guard_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        side_to_move="white",
        candidate_move="f1f2",
        memory_path=tmp_path / "memory.json",
    )

    assert result.legal_alternatives_count > 0
    assert result.safest_alternative_move
    assert result.safest_alternative_reply_score >= 0


def test_phase22e28_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_one_ply_blunder_guard_kernel(
        input_fen="8/8/8/8/8/8/5k2/4K3 w - - 0 1",
        side_to_move="white",
        candidate_move="e1d1",
        memory_path=memory_path,
    )
    second = run_full_chess_one_ply_blunder_guard_kernel(
        input_fen="8/8/8/8/8/8/5k2/4K3 w - - 0 1",
        side_to_move="white",
        candidate_move="e1d1",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_guard_policy["kernel_run_count"] == 2


def test_phase22e28_boundary_no_engine_or_analysis(tmp_path: Path):
    result = run_full_chess_one_ply_blunder_guard_kernel(
        input_fen="8/8/8/8/8/8/5k2/4K3 w - - 0 1",
        side_to_move="white",
        candidate_move="e1d1",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "one-ply blunder guard" in result.boundary_statement
