from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_orchestrator_parent_child_aggregation_lock.tex")


def test_orchestrator_parent_child_aggregation_lock_doc_exists():
    assert DOC.exists()


def test_orchestrator_parent_child_aggregation_lock_names_trace():
    text = DOC.read_text()
    assert "orchestrator_parent_child_aggregation_preview" in text
    assert "aion.goal_engine.orchestrator_parent_child_aggregation.v1" in text


def test_orchestrator_parent_child_aggregation_lock_names_required_fields():
    text = DOC.read_text()
    for token in [
        "parent_goal_id",
        "child_status_counts",
        "child_agents",
        "child_glyphs",
        "aggregate_status",
        "manual_review_required = true",
        "dry_run_only = true",
        "would_mutate_parent_goal = false",
    ]:
        assert token in text


def test_orchestrator_parent_child_aggregation_lock_footer():
    text = DOC.read_text()
    assert "Lock ID: AION-GOAL-ENGINE-ORCHESTRATOR-PARENT-CHILD-AGGREGATION-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
