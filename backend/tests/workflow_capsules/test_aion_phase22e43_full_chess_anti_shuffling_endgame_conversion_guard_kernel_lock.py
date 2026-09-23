from pathlib import Path

from backend.modules.aion_games.full_chess_anti_shuffling_endgame_conversion_guard_kernel import (
    run_full_chess_anti_shuffling_endgame_conversion_guard_kernel,
)


def test_phase22e43_replaces_repeated_rook_shuffle(tmp_path: Path):
    result = run_full_chess_anti_shuffling_endgame_conversion_guard_kernel(
        input_fen="1R6/k5b1/2P3P1/4r2p/4P3/P7/4B2p/4K3 w - - 3 40",
        side_to_move="white",
        repeated_moves=["d7b7", "b8a8", "b7b8", "a8a7", "b8b7"],
        repeated_squares=["b7", "b8", "a8", "a7", "b8", "b7"],
        forced_base_selected_move="b8c8",
        memory_path=tmp_path / "memory.json",
    )

    assert result.shuffle_detected is True
    assert result.conversion_alternative_found is True
    assert result.anti_shuffling_override_applied is True
    assert result.final_selected_move != "b8c8"
    assert result.final_selected_move_is_legal is True


def test_phase22e43_keeps_capture_or_progress(tmp_path: Path):
    result = run_full_chess_anti_shuffling_endgame_conversion_guard_kernel(
        input_fen="r4b1r/ppk1n2p/8/1P2N1p1/4P2p/2N5/P1P1BPP1/R3K2R w KQ - 0 17",
        side_to_move="white",
        repeated_moves=["b4b5"],
        repeated_squares=["b4", "b5"],
        forced_base_selected_move="b5b6",
        memory_path=tmp_path / "memory.json",
    )

    assert result.shuffle_detected is False
    assert result.anti_shuffling_override_applied is False
    assert result.final_selected_move == "b5b6"
    assert result.final_selected_move_is_legal is True


def test_phase22e43_memory_persists(tmp_path: Path):
    memory = tmp_path / "memory.json"

    first = run_full_chess_anti_shuffling_endgame_conversion_guard_kernel(
        input_fen="1R6/k5b1/2P3P1/4r2p/4P3/P7/4B2p/4K3 w - - 3 40",
        side_to_move="white",
        repeated_moves=["d7b7", "b8a8", "b7b8", "a8a7", "b8b7"],
        repeated_squares=["b7", "b8", "a8", "a7", "b8", "b7"],
        forced_base_selected_move="b8c8",
        memory_path=memory,
    )
    second = run_full_chess_anti_shuffling_endgame_conversion_guard_kernel(
        input_fen="1R6/k5b1/2P3P1/4r2p/4P3/P7/4B2p/4K3 w - - 3 40",
        side_to_move="white",
        repeated_moves=["d7b7", "b8a8", "b7b8", "a8a7", "b8b7"],
        repeated_squares=["b7", "b8", "a8", "a7", "b8", "b7"],
        forced_base_selected_move="b8c8",
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e43_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_anti_shuffling_endgame_conversion_guard_kernel(
        input_fen="1R6/k5b1/2P3P1/4r2p/4P3/P7/4B2p/4K3 w - - 3 40",
        side_to_move="white",
        repeated_moves=["d7b7", "b8a8", "b7b8", "a8a7", "b8b7"],
        repeated_squares=["b7", "b8", "a8", "a7", "b8", "b7"],
        forced_base_selected_move="b8c8",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
