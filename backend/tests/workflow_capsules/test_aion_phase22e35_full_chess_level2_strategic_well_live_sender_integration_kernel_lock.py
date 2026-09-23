from pathlib import Path

from backend.modules.aion_games.full_chess_level2_strategic_well_live_sender_integration_kernel import (
    run_full_chess_level2_strategic_well_live_sender_integration_kernel,
)


def test_phase22e35_integrates_strategic_well_without_posting(tmp_path: Path):
    result = run_full_chess_level2_strategic_well_live_sender_integration_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        game_id="test_game",
        memory_path=tmp_path / "memory.json",
    )

    assert result.live_sender_integration_active is True
    assert result.selected_move == "a7a8q"
    assert result.selected_move_is_legal is True
    assert result.safe_to_send is True
    assert result.live_post_attempted is False
    assert result.live_post_succeeded is False


def test_phase22e35_blocks_live_post_when_gates_false(tmp_path: Path):
    result = run_full_chess_level2_strategic_well_live_sender_integration_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        game_id="test_game",
        allow_live_post=False,
        human_confirmed=False,
        live_stream_confirmed=False,
        memory_path=tmp_path / "memory.json",
    )

    assert result.safe_to_send is True
    assert result.live_post_allowed is False
    assert result.sender_mode == "dry_run_ready"


def test_phase22e35_marks_ready_when_all_live_gates_true(tmp_path: Path):
    result = run_full_chess_level2_strategic_well_live_sender_integration_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        game_id="test_game",
        allow_live_post=True,
        human_confirmed=True,
        live_stream_confirmed=True,
        one_move_gate_enabled=True,
        memory_path=tmp_path / "memory.json",
    )

    assert result.safe_to_send is True
    assert result.live_post_allowed is True
    assert result.live_post_attempted is False
    assert result.sender_mode == "ready_for_authorised_live_sender"


def test_phase22e35_preserves_repetition_context(tmp_path: Path):
    result = run_full_chess_level2_strategic_well_live_sender_integration_kernel(
        input_fen="r2q4/1ppbp1k1/p2p2p1/8/2P3n1/2N5/PP3PPP/R1B1R2K w - - 2 21",
        side_to_move="white",
        game_id="test_game",
        repeated_moves=["f1e1", "e1g1", "g1e1", "e1g1"],
        repeated_squares=["e1", "g1", "e1", "g1"],
        memory_path=tmp_path / "memory.json",
    )

    assert result.repeated_moves
    assert result.repeated_squares
    assert result.strategic_well_summary["repetition_detected"] is True
    assert result.selected_move_is_legal is True


def test_phase22e35_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_level2_strategic_well_live_sender_integration_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        game_id="test_game",
        memory_path=memory_path,
    )
    second = run_full_chess_level2_strategic_well_live_sender_integration_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        game_id="test_game",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_sender_policy["kernel_run_count"] == 2


def test_phase22e35_boundary_no_engine_analysis_or_post(tmp_path: Path):
    result = run_full_chess_level2_strategic_well_live_sender_integration_kernel(
        input_fen="8/P7/8/8/8/8/8/4K2k w - - 0 1",
        side_to_move="white",
        game_id="test_game",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["integration_only_no_post_attempted"] is True
    assert "does not POST to Lichess" in result.boundary_statement
