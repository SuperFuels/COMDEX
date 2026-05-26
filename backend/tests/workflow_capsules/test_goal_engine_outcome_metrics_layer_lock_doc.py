from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_outcome_metrics_layer_lock.tex")


def test_outcome_metrics_layer_lock_doc_exists():
    assert DOC.exists()


def test_outcome_metrics_layer_lock_names_trace_blocks():
    text = DOC.read_text()
    assert "experiment_result_evidence_preview" in text
    assert "variant_outcome_score_preview" in text


def test_outcome_metrics_layer_lock_names_safety_invariants():
    text = DOC.read_text()
    for token in [
        "dry_run_only = true",
        "winner_declared = false",
        "loser_stopped = false",
        "would_execute = false",
        "would_write_external = false",
        "would_grant_permission = false",
        "human_review_required_before_winner_activation",
    ]:
        assert token in text


def test_outcome_metrics_layer_lock_keeps_evidence_rule():
    text = DOC.read_text()
    assert "MUST NOT be treated as a successful outcome unless valid evidence exists" in text


def test_outcome_metrics_layer_lock_has_footer():
    text = DOC.read_text()
    assert "Lock ID: AION-GOAL-ENGINE-OUTCOME-METRICS-LAYER-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
