from backend.modules.aion.goal_engine.outcome_scoring import (
    EXPERIMENT_RESULT_EVIDENCE_SCHEMA_VERSION,
    VARIANT_OUTCOME_SCORE_SCHEMA_VERSION,
    build_experiment_result_evidence_preview,
    build_variant_outcome_score_preview,
)


def test_experiment_result_evidence_preview_requires_variant_evidence():
    preview = build_experiment_result_evidence_preview(
        experiment_id="exp_1",
        goal_id="goal_1",
        metric="leads",
        variants=[
            {"variant_id": "a", "metric_actual": 5, "sample_size": 20},
            {"variant_id": "b", "sample_size": 20},
        ],
        evidence=[{"source": "utm", "reference": "utm_1"}],
    )

    assert preview["schema_version"] == EXPERIMENT_RESULT_EVIDENCE_SCHEMA_VERSION
    assert preview["trace_type"] == "experiment_result_evidence_preview"
    assert preview["evidence_ready"] is False
    assert "experiment_result_evidence_required" in preview["blocked_reasons"]
    assert preview["winner_declared"] is False
    assert preview["dry_run_only"] is True


def test_experiment_result_evidence_preview_marks_ready_when_all_variants_have_support():
    preview = build_experiment_result_evidence_preview(
        experiment_id="exp_1",
        goal_id="goal_1",
        metric="leads",
        variants=[
            {"variant_id": "a", "metric_actual": 5, "sample_size": 20},
            {"variant_id": "b", "metric_actual": 8, "sample_size": 25},
        ],
        evidence=[{"source": "utm", "reference": "utm_1"}],
    )

    assert preview["evidence_ready"] is True
    assert preview["blocked_reasons"] == []
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False


def test_variant_outcome_score_preview_ranks_variants_without_declaring_winner():
    preview = build_variant_outcome_score_preview(
        experiment_id="exp_1",
        goal_id="goal_1",
        metric="leads",
        target_value=10,
        variants=[
            {"variant_id": "a", "metric_actual": 5, "cost": 1, "confidence": 0.6},
            {"variant_id": "b", "metric_actual": 9, "cost": 1, "confidence": 0.8},
        ],
    )

    assert preview["schema_version"] == VARIANT_OUTCOME_SCORE_SCHEMA_VERSION
    assert preview["trace_type"] == "variant_outcome_score_preview"
    assert preview["ranked_variant_ids"][0] == "b"
    assert preview["top_variant_id"] == "b"
    assert preview["winner_declared"] is False
    assert preview["loser_stopped"] is False
    assert preview["dry_run_only"] is True


def test_variant_outcome_score_preview_never_grants_permission():
    preview = build_variant_outcome_score_preview(
        experiment_id="exp_1",
        goal_id="goal_1",
        metric="leads",
        variants=[{"variant_id": "a", "metric_actual": 1}],
    )

    assert preview["would_execute"] is False
    assert preview["would_write_external"] is False
    assert preview["would_grant_permission"] is False
    assert "human_review_required_before_winner_activation" in preview["blocked_reasons"]
