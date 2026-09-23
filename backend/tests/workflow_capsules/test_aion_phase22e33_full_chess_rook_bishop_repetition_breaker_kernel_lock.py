from pathlib import Path

from backend.modules.aion_games.full_chess_rook_bishop_repetition_breaker_kernel import (
    run_full_chess_rook_bishop_repetition_breaker_kernel,
)


def test_phase22e33_detects_rook_repetition(tmp_path: Path):
    result = run_full_chess_rook_bishop_repetition_breaker_kernel(
        input_fen="r2q4/1ppbp1k1/p2p2p1/8/2P3n1/2N5/PP3PPP/R1B1R2K w - - 2 21",
        side_to_move="white",
        repeated_moves=["f1e1", "e1g1", "g1e1", "e1g1"],
        repeated_squares=["e1", "g1", "e1", "g1"],
        memory_path=tmp_path / "memory.json",
    )

    assert result.repetition_breaker_active is True
    assert result.repetition_detected is True
    assert result.selected_breaker_move_is_legal is True
    assert result.candidate_count > 0


def test_phase22e33_penalises_repeated_rook_move_if_present(tmp_path: Path):
    result = run_full_chess_rook_bishop_repetition_breaker_kernel(
        input_fen="r2q4/1ppbp1k1/p2p2p1/8/2P3n1/2N5/PP3PPP/R1B1R2K w - - 2 21",
        side_to_move="white",
        repeated_moves=["f1e1", "e1g1", "g1e1", "e1g1"],
        repeated_squares=["e1", "g1", "e1", "g1"],
        memory_path=tmp_path / "memory.json",
    )

    repeated = [
        c for c in result.top_candidates
        if c["move"] in {"f1e1", "e1g1", "g1e1"}
    ]
    for candidate in repeated:
        assert candidate["repeated_move_penalty_applied"] or candidate["repeated_square_penalty_applied"]


def test_phase22e33_prefers_irreversible_progress_when_available(tmp_path: Path):
    result = run_full_chess_rook_bishop_repetition_breaker_kernel(
        input_fen="8/8/8/8/8/8/P7/4K2k w - - 0 1",
        side_to_move="white",
        repeated_moves=["e1d1", "d1e1", "e1d1", "d1e1"],
        repeated_squares=["d1", "e1", "d1", "e1"],
        memory_path=tmp_path / "memory.json",
    )

    assert result.selected_breaker_move_is_legal is True
    assert result.top_candidates[0]["irreversible_progress"] is True


def test_phase22e33_handles_no_repetition_context(tmp_path: Path):
    result = run_full_chess_rook_bishop_repetition_breaker_kernel(
        input_fen="8/8/8/8/8/8/P7/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.repetition_detected is False
    assert result.selected_breaker_move_is_legal is True


def test_phase22e33_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_rook_bishop_repetition_breaker_kernel(
        input_fen="8/8/8/8/8/8/P7/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_rook_bishop_repetition_breaker_kernel(
        input_fen="8/8/8/8/8/8/P7/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_breaker_policy["kernel_run_count"] == 2


def test_phase22e33_boundary_no_engine_or_analysis(tmp_path: Path):
    result = run_full_chess_rook_bishop_repetition_breaker_kernel(
        input_fen="8/8/8/8/8/8/P7/4K2k w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "rook/bishop repetition breaker" in result.boundary_statement
