from pathlib import Path

from backend.modules.aion_games.full_chess_guarded_concept_guided_live_sender_gate_kernel import (
    run_full_chess_guarded_concept_guided_live_sender_gate_kernel,
)


def test_phase22e13_blocks_live_send_by_default(tmp_path: Path):
    result = run_full_chess_guarded_concept_guided_live_sender_gate_kernel(
        memory_path=tmp_path / "gate_memory.json",
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

    assert result.gate_mode == "guarded_concept_guided_live_sender_gate"
    assert result.dry_run_adapter_consumed is True
    assert result.selected_move_is_legal is True
    assert result.live_sender_gate_enabled is False
    assert result.live_sender_gate_passed is False
    assert result.live_lichess_send_enabled is False
    assert result.lichess_move_post_attempted is False


def test_phase22e13_requires_all_live_authorization_conditions(tmp_path: Path):
    result = run_full_chess_guarded_concept_guided_live_sender_gate_kernel(
        memory_path=tmp_path / "gate_memory.json",
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

    assert result.evidence["requires_explicit_live_send_authorization"] is True
    assert result.evidence["requires_lichess_token"] is True
    assert result.evidence["requires_live_game_stream_confirmation"] is True
    assert result.evidence["requires_human_operator_confirmation"] is True
    assert result.guard_conditions["explicit_live_send_authorized"] is False
    assert result.guard_conditions["lichess_token_present"] is False


def test_phase22e13_even_with_conditions_live_sender_stays_disabled(tmp_path: Path):
    result = run_full_chess_guarded_concept_guided_live_sender_gate_kernel(
        memory_path=tmp_path / "gate_memory.json",
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
        dry_run_only=False,
        explicit_live_send_authorized=True,
        lichess_token_present=True,
        live_game_stream_confirmed=True,
        human_operator_confirmed=True,
    )

    assert result.live_sender_gate_enabled is False
    assert result.live_sender_gate_passed is False
    assert result.live_lichess_send_enabled is False
    assert result.lichess_move_post_attempted is False
    assert result.evidence["send_blocked_by_guard"] is True


def test_phase22e13_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "gate_memory.json"

    first = run_full_chess_guarded_concept_guided_live_sender_gate_kernel(
        memory_path=memory_path,
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
    second = run_full_chess_guarded_concept_guided_live_sender_gate_kernel(
        memory_path=memory_path,
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
    assert second.final_live_sender_gate_policy["kernel_run_count"] == 2
    assert second.final_live_sender_gate_policy["gate_block_count"] == 2
    assert second.final_live_sender_gate_policy["move_post_attempt_total"] == 0


def test_phase22e13_boundary_no_external_engines_or_post(tmp_path: Path):
    result = run_full_chess_guarded_concept_guided_live_sender_gate_kernel(
        memory_path=tmp_path / "gate_memory.json",
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

    assert result.evidence["no_move_post"] is True
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
