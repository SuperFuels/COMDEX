from pathlib import Path

from backend.modules.aion_games.full_chess_live_one_move_strategic_well_sender_kernel import (
    run_full_chess_live_one_move_strategic_well_sender_kernel,
)


def test_phase22e38_uses_22e37_and_blocks_by_default(tmp_path: Path):
    result = run_full_chess_live_one_move_strategic_well_sender_kernel(
        game_id="test_game",
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        repeated_moves=["d2d4", "d7d5"],
        repeated_squares=["d4", "d5"],
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["phase22e37_intent_driven_well_used"] is True
    assert result.selected_move == "g1f3"
    assert result.base_well_selected_move == "h2h4"
    assert result.intent_override_applied is True
    assert result.move_post_attempted is False
    assert result.all_live_gates_passed is False


def test_phase22e38_requires_all_live_gates(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AION_LICHESS_LIVE", "1")

    result = run_full_chess_live_one_move_strategic_well_sender_kernel(
        game_id="test_game",
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        repeated_moves=["d2d4", "d7d5"],
        repeated_squares=["d4", "d5"],
        explicit_live_send_authorized=True,
        human_operator_confirmed=True,
        live_game_stream_confirmed=True,
        one_move_gate_enabled=True,
        live_sender_enabled=True,
        allow_real_post=False,
        token="fake",
        memory_path=tmp_path / "memory.json",
    )

    assert result.selected_move == "g1f3"
    assert result.all_live_gates_passed is False
    assert result.move_post_attempted is False


def test_phase22e38_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_live_one_move_strategic_well_sender_kernel(
        game_id="test_game",
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_live_one_move_strategic_well_sender_kernel(
        game_id="test_game",
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_sender_policy["kernel_run_count"] == 2


def test_phase22e38_boundary_no_engine_or_llm(tmp_path: Path):
    result = run_full_chess_live_one_move_strategic_well_sender_kernel(
        game_id="test_game",
        input_fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["one_move_only"] is True
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "at most one live Lichess move" in result.boundary_statement
