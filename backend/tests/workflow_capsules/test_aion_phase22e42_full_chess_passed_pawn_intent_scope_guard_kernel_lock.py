from pathlib import Path

from backend.modules.aion_games.full_chess_passed_pawn_intent_scope_guard_kernel import (
    run_full_chess_passed_pawn_intent_scope_guard_kernel,
)


def test_phase22e42_rejects_convert_pawn_for_rook_shuffle(tmp_path: Path):
    result = run_full_chess_passed_pawn_intent_scope_guard_kernel(
        input_fen="r3r3/Ppk1N1b1/8/4N1pp/4P1Pp/5P2/P1P1B3/R3K2R w KQ - 1 23",
        side_to_move="white",
        forced_base_selected_move="h1h4",
        memory_path=tmp_path / "memory.json",
    )

    assert result.active_intent_before_scope == "convert_passed_pawn"
    assert result.final_selected_move == "h1h4"
    assert result.passed_pawn_scope_checked is True
    assert result.passed_pawn_scope_valid is False
    assert result.passed_pawn_scope_override_applied is True
    assert result.active_intent == "initiative_pressure"


def test_phase22e42_allows_direct_pawn_progress(tmp_path: Path):
    result = run_full_chess_passed_pawn_intent_scope_guard_kernel(
        input_fen="r4b1r/ppk1n2p/8/1P2N1p1/4P2p/2N5/P1P1BPP1/R3K2R w KQ - 0 17",
        side_to_move="white",
        forced_base_selected_move="b5b6",
        memory_path=tmp_path / "memory.json",
    )

    assert result.active_intent_before_scope == "convert_passed_pawn"
    assert result.final_selected_move == "b5b6"
    assert result.passed_pawn_scope_valid is True
    assert result.passed_pawn_scope_override_applied is False
    assert result.active_intent == "convert_passed_pawn"


def test_phase22e42_allows_queen_promotion(tmp_path: Path):
    result = run_full_chess_passed_pawn_intent_scope_guard_kernel(
        input_fen="r1bk1b1r/ppqPn1pp/3p4/4p1p1/1P2P2P/2N2N2/P1P1BPP1/R2QK2R w KQ - 1 12",
        side_to_move="white",
        forced_base_selected_move="d7c8r",
        memory_path=tmp_path / "memory.json",
    )

    assert result.final_selected_move == "d7c8q"
    assert result.queen_override_applied is True
    assert result.passed_pawn_scope_valid is True
    assert result.passed_pawn_scope_override_applied is False


def test_phase22e42_memory_persists(tmp_path: Path):
    memory = tmp_path / "memory.json"

    first = run_full_chess_passed_pawn_intent_scope_guard_kernel(
        input_fen="r3r3/Ppk1N1b1/8/4N1pp/4P1Pp/5P2/P1P1B3/R3K2R w KQ - 1 23",
        side_to_move="white",
        forced_base_selected_move="h1h4",
        memory_path=memory,
    )
    second = run_full_chess_passed_pawn_intent_scope_guard_kernel(
        input_fen="r3r3/Ppk1N1b1/8/4N1pp/4P1Pp/5P2/P1P1B3/R3K2R w KQ - 1 23",
        side_to_move="white",
        forced_base_selected_move="h1h4",
        memory_path=memory,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2


def test_phase22e42_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_passed_pawn_intent_scope_guard_kernel(
        input_fen="r3r3/Ppk1N1b1/8/4N1pp/4P1Pp/5P2/P1P1B3/R3K2R w KQ - 1 23",
        side_to_move="white",
        forced_base_selected_move="h1h4",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
