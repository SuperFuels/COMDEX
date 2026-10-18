from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_parent_goal_proposal_conflict_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_parent_goal_proposal_conflict_lock_doc_exists():
    text = DOC.read_text()
    assert "Goal Engine Parent-Goal Proposal and Child-Agent Conflict Lock" in text
    assert "Status: LOCKED" in text
    assert "353 passed" in text


def test_parent_goal_proposal_conflict_lock_doc_names_canonical_payloads():
    text = DOC.read_text()
    assert "parent\\_goal\\_update\\_proposal" in text
    assert "child\\_agent\\_conflict\\_preview" in text
    assert "orchestrator\\_parent\\_child\\_aggregation\\_runtime\\_summary" in text
    assert "parent\\_child\\_aggregation\\_previews" in text


def test_parent_goal_proposal_conflict_lock_doc_preserves_safety_guards():
    text = DOC.read_text()
    assert "would_mutate_parent_goal = false" in text
    assert "would_execute = false" in text
    assert "would_auto_resolve = false" in text
    assert "approval_gate = parent_goal_update_review" in text
    assert "manual_review_required = true" in text


def test_parent_goal_proposal_conflict_lock_doc_names_boardroom_panel():
    text = DOC.read_text()
    assert "renderAionGoalEngineParentGoalProposalConflictPanelV1" in text
    assert 'data-aion-goal-engine-parent-goal-proposal-conflict="v1"' in text
    assert "visibility only" in text


def test_parent_goal_proposal_conflict_lock_doc_has_footer():
    text = DOC.read_text()
    assert "Lock ID: AION-GOAL-ENGINE-PARENT-GOAL-PROPOSAL-CONFLICT-v1" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_parent_goal_proposal_conflict_lock_doc_added_to_focused_suite():
    text = SUITE.read_text()
    assert "test_goal_engine_parent_goal_proposal_conflict_lock_doc.py" in text
