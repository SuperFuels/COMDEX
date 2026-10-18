from pathlib import Path

from backend.modules.aion_games.full_chess_concept_guided_live_lichess_dry_run_adapter_kernel import (
    run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel,
)


def test_phase22e12_builds_live_adapter_shaped_dry_run_preview(tmp_path: Path):
    result = run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
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

    assert result.adapter_mode == "concept_guided_live_lichess_dry_run_adapter"
    assert result.dry_run_only is True
    assert result.selected_move_preview
    assert result.selected_move_is_legal is True
    assert result.local_loop_preview_consumed is True
    assert result.local_loop_plies_completed >= 1


def test_phase22e12_never_attempts_lichess_post(tmp_path: Path):
    result = run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
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

    assert result.live_lichess_send_enabled is False
    assert result.lichess_move_post_attempted is False
    assert result.evidence["no_move_post"] is True
    assert result.evidence["live_lichess_send_enabled"] is False
    assert result.evidence["lichess_move_post_attempted"] is False


def test_phase22e12_preview_has_trace_hash_and_concept_data(tmp_path: Path):
    result = run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
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

    preview = result.dry_run_previews[0]
    assert preview["selected_move"]
    assert preview["selected_move_is_legal"] is True
    assert preview["applied_concept_count"] >= 1
    assert preview["concept_bias_score_total"] > 0
    assert preview["preview_trace_hash"]
    assert result.adapter_trace_hash


def test_phase22e12_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "adapter_memory.json"

    first = run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel(
        memory_path=memory_path,
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
    second = run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel(
        memory_path=memory_path,
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
    assert second.final_dry_run_adapter_policy["kernel_run_count"] == 2
    assert second.final_dry_run_adapter_policy["preview_total"] == 2
    assert second.final_dry_run_adapter_policy["move_post_attempt_total"] == 0


def test_phase22e12_boundary_no_external_engines_or_live_send(tmp_path: Path):
    result = run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
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

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
