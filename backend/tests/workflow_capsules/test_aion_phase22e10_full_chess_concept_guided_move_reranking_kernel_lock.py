from pathlib import Path

from backend.modules.aion_games.full_chess_concept_guided_move_reranking_kernel import (
    run_full_chess_concept_guided_move_reranking_kernel,
)


def test_phase22e10_reranks_legal_candidate_moves(tmp_path: Path):
    result = run_full_chess_concept_guided_move_reranking_kernel(
        memory_path=tmp_path / "rerank_memory.json",
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

    assert result.rerank_mode == "concept_guided_move_reranking"
    assert result.legal_candidate_count == 20
    assert result.reranked_candidate_count == 20
    assert len(result.top_reranked_moves) == 8
    assert result.concept_guided_selected_move
    assert result.evidence["concept_guided_move_reranking_active"] is True


def test_phase22e10_applies_concept_bias_to_moves(tmp_path: Path):
    result = run_full_chess_concept_guided_move_reranking_kernel(
        memory_path=tmp_path / "rerank_memory.json",
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

    assert result.evidence["concept_guided_search_plan_bias_consumed"] is True
    assert result.evidence["concept_bias_applied_to_candidate_moves"] is True
    assert result.applied_concept_count >= 1
    assert result.concept_bias_score_total > 0

    biased = [move for move in result.top_reranked_moves if move["concept_bias_score"] > 0]
    assert biased


def test_phase22e10_top_moves_have_trace_hashes_and_scores(tmp_path: Path):
    result = run_full_chess_concept_guided_move_reranking_kernel(
        memory_path=tmp_path / "rerank_memory.json",
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

    for move in result.top_reranked_moves:
        assert move["move_uci"]
        assert move["base_score"] > 0
        assert move["final_score"] >= move["base_score"]
        assert move["rerank_trace_hash"]
        assert move["reranked_rank"] >= 1


def test_phase22e10_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "rerank_memory.json"

    first = run_full_chess_concept_guided_move_reranking_kernel(
        memory_path=memory_path,
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
    second = run_full_chess_concept_guided_move_reranking_kernel(
        memory_path=memory_path,
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
    assert second.final_move_reranking_policy["kernel_run_count"] == 2
    assert second.final_move_reranking_policy["reranked_move_total"] >= first.reranked_candidate_count


def test_phase22e10_boundary_no_live_send_or_external_engines(tmp_path: Path):
    result = run_full_chess_concept_guided_move_reranking_kernel(
        memory_path=tmp_path / "rerank_memory.json",
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

    assert result.evidence["concept_guided_selected_move_is_legal"] is True
    assert result.evidence["live_lichess_send_enabled"] is False
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
