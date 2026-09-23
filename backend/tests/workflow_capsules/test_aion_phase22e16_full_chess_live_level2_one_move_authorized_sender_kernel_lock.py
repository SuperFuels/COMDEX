from pathlib import Path

from backend.modules.aion_games.full_chess_live_level2_one_move_authorized_sender_kernel import (
    run_full_chess_live_level2_one_move_authorized_sender_kernel,
)


def test_phase22e16_blocks_by_default(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("LICHESS_BOT_TOKEN", raising=False)

    result = run_full_chess_live_level2_one_move_authorized_sender_kernel(
        memory_path=tmp_path / "sender_memory.json",
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

    assert result.sender_mode == "live_level2_one_move_authorized_sender"
    assert result.selected_move_is_legal is True
    assert result.move_post_attempted is False
    assert result.move_post_succeeded is False
    assert result.live_sender_enabled is False


def test_phase22e16_requires_all_authorization_flags(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test-token")

    result = run_full_chess_live_level2_one_move_authorized_sender_kernel(
        memory_path=tmp_path / "sender_memory.json",
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
        explicit_live_send_authorized=True,
        human_operator_confirmed=False,
        live_game_stream_confirmed=True,
        one_move_gate_enabled=True,
        live_sender_enabled=True,
        allow_real_post=True,
    )

    assert result.token_present is True
    assert result.explicit_live_send_authorized is True
    assert result.human_operator_confirmed is False
    assert result.move_post_attempted is False
    assert "human_operator_confirmed" in result.send_blocked_reason


def test_phase22e16_mock_post_only_when_all_flags_true(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LICHESS_BOT_TOKEN", "test-token")
    calls = []

    def fake_post(token: str, game_id: str, move_uci: str):
        calls.append((token, game_id, move_uci))
        return True, 200, None

    result = run_full_chess_live_level2_one_move_authorized_sender_kernel(
        memory_path=tmp_path / "sender_memory.json",
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
        explicit_live_send_authorized=True,
        human_operator_confirmed=True,
        live_game_stream_confirmed=True,
        one_move_gate_enabled=True,
        live_sender_enabled=True,
        allow_real_post=True,
        post_move_callable=fake_post,
    )

    assert result.move_post_attempted is True
    assert result.move_post_succeeded is True
    assert result.move_post_status_code == 200
    assert len(calls) == 1
    assert calls[0][2] == result.selected_move


def test_phase22e16_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "sender_memory.json"

    first = run_full_chess_live_level2_one_move_authorized_sender_kernel(
        memory_path=memory_path,
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
    second = run_full_chess_live_level2_one_move_authorized_sender_kernel(
        memory_path=memory_path,
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

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_sender_policy["kernel_run_count"] == 2


def test_phase22e16_boundary_no_external_engines(tmp_path: Path):
    result = run_full_chess_live_level2_one_move_authorized_sender_kernel(
        memory_path=tmp_path / "sender_memory.json",
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

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
