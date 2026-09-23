from pathlib import Path

from backend.modules.aion_games.full_chess_queen_endgame_override_live_sender_kernel import (
    run_full_chess_queen_endgame_override_live_sender_kernel,
)


def test_phase22e21_queen_endgame_override_activates(tmp_path: Path):
    result = run_full_chess_queen_endgame_override_live_sender_kernel(
        game_id="TEST",
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        repeated_moves=["d6b8"],
        repeated_queen_squares=["b8", "d6"],
        clock_seconds_remaining=30,
        memory_path=tmp_path / "memory.json",
        queen_memory_path=tmp_path / "queen_memory.json",
    )

    assert result.queen_endgame_override_active is True
    assert result.base_sender_consumed is False
    assert result.final_selected_move == result.override_selected_move
    assert result.final_selected_move_is_legal is True
    assert result.move_post_attempted is False


def test_phase22e21_mock_post_when_all_live_flags_true(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test-token")
    calls = []

    def fake_post(token: str, game_id: str, move_uci: str):
        calls.append((token, game_id, move_uci))
        return True, 200, None

    result = run_full_chess_queen_endgame_override_live_sender_kernel(
        game_id="TEST",
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        repeated_moves=["d6b8"],
        repeated_queen_squares=["b8", "d6"],
        clock_seconds_remaining=30,
        explicit_live_send_authorized=True,
        human_operator_confirmed=True,
        live_game_stream_confirmed=True,
        one_move_gate_enabled=True,
        live_sender_enabled=True,
        allow_real_post=True,
        post_move_callable=fake_post,
        memory_path=tmp_path / "memory.json",
        queen_memory_path=tmp_path / "queen_memory.json",
    )

    assert result.move_post_attempted is True
    assert result.move_post_succeeded is True
    assert result.move_post_status_code == 200
    assert len(calls) == 1
    assert calls[0][2] == result.final_selected_move


def test_phase22e21_blocks_without_flags_even_with_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test-token")

    result = run_full_chess_queen_endgame_override_live_sender_kernel(
        game_id="TEST",
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
        queen_memory_path=tmp_path / "queen_memory.json",
    )

    assert result.queen_endgame_override_active is True
    assert result.move_post_attempted is False
    assert result.move_post_succeeded is False


def test_phase22e21_non_queen_endgame_falls_back_to_base_sender(tmp_path: Path):
    result = run_full_chess_queen_endgame_override_live_sender_kernel(
        game_id="TEST",
        input_fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
        queen_memory_path=tmp_path / "queen_memory.json",
        base_sender_memory_path=tmp_path / "base_memory.json",
        smoke_memory_path=tmp_path / "smoke_memory.json",
        preflight_memory_path=tmp_path / "preflight_memory.json",
        gate_memory_path=tmp_path / "gate_memory.json",
        adapter_memory_path=tmp_path / "adapter_memory.json",
        loop_memory_path=tmp_path / "loop_memory.json",
        rerank_memory_path=tmp_path / "rerank_memory.json",
        bias_memory_path=tmp_path / "bias_memory.json",
        concept_memory_path=tmp_path / "concept_memory.json",
        forecast_memory_path=tmp_path / "forecast_memory.json",
        long_term_plan_memory_path=tmp_path / "long_term_plan_memory.json",
        curriculum_memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.queen_endgame_override_active is False
    assert result.base_sender_consumed is True
    assert result.base_selected_move
    assert result.final_selected_move == result.base_selected_move


def test_phase22e21_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_queen_endgame_override_live_sender_kernel(
        game_id="TEST",
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=memory_path,
        queen_memory_path=tmp_path / "queen_memory.json",
    )
    second = run_full_chess_queen_endgame_override_live_sender_kernel(
        game_id="TEST",
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=memory_path,
        queen_memory_path=tmp_path / "queen_memory.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_override_policy["kernel_run_count"] == 2


def test_phase22e21_boundary_no_engine_calls(tmp_path: Path):
    result = run_full_chess_queen_endgame_override_live_sender_kernel(
        game_id="TEST",
        input_fen="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
        queen_memory_path=tmp_path / "queen_memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["queen_endgame_override_active"] is True
