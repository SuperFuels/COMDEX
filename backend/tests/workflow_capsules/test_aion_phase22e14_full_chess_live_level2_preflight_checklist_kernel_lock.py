from pathlib import Path

from backend.modules.aion_games.full_chess_live_level2_preflight_checklist_kernel import (
    run_full_chess_live_level2_preflight_checklist_kernel,
)


def test_phase22e14_preflight_passes_when_token_not_required(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("LICHESS_BOT_TOKEN", raising=False)

    result = run_full_chess_live_level2_preflight_checklist_kernel(
        memory_path=tmp_path / "preflight_memory.json",
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
        require_token_for_pass=False,
    )

    assert result.preflight_mode == "live_level2_preflight_checklist"
    assert result.target_level == 2
    assert result.token_env_checked is True
    assert result.token_present is False
    assert result.preflight_passed is True
    assert result.preflight_blockers == []


def test_phase22e14_preflight_blocks_when_token_required_and_missing(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("LICHESS_BOT_TOKEN", raising=False)

    result = run_full_chess_live_level2_preflight_checklist_kernel(
        memory_path=tmp_path / "preflight_memory.json",
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
        require_token_for_pass=True,
    )

    assert result.preflight_passed is False
    assert "lichess_token_missing" in result.preflight_blockers


def test_phase22e14_preflight_consumes_guard_and_keeps_sender_blocked(tmp_path: Path):
    result = run_full_chess_live_level2_preflight_checklist_kernel(
        memory_path=tmp_path / "preflight_memory.json",
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

    assert result.guarded_gate_consumed is True
    assert result.guarded_gate_trace_hash
    assert result.selected_move_is_legal is True
    assert result.live_sender_gate_enabled is False
    assert result.live_sender_gate_passed is False
    assert result.live_lichess_send_enabled is False
    assert result.lichess_move_post_attempted is False


def test_phase22e14_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "preflight_memory.json"

    first = run_full_chess_live_level2_preflight_checklist_kernel(
        memory_path=memory_path,
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
    second = run_full_chess_live_level2_preflight_checklist_kernel(
        memory_path=memory_path,
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
    assert second.final_preflight_policy["kernel_run_count"] == 2


def test_phase22e14_boundary_no_live_game_or_post(tmp_path: Path):
    result = run_full_chess_live_level2_preflight_checklist_kernel(
        memory_path=tmp_path / "preflight_memory.json",
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

    assert result.evidence["live_lichess_send_enabled"] is False
    assert result.evidence["lichess_move_post_attempted"] is False
    assert result.evidence["no_move_post"] is True
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_lichess_analysis"] is False
