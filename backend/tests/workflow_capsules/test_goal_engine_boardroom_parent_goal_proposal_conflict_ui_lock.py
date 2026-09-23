from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_parent_goal_proposal_conflict_panel_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineParentGoalProposalConflictPanelV1" in text
    assert 'data-aion-goal-engine-parent-goal-proposal-conflict="v1"' in text
    assert "Parent Goal Proposal" in text
    assert "Child Agent Conflict" in text


def test_parent_goal_proposal_conflict_panel_reads_canonical_payloads():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineParentGoalProposalConflictPanelV1"):
        text.index("window.renderAionGoalEngineParentGoalProposalConflictPanelV1")
    ]

    assert "parent_goal_update_proposal" in block
    assert "child_agent_conflict_preview" in block
    assert "orchestrator_parent_child_aggregation_runtime_summary" in block
    assert "parent_child_aggregation_previews" in block


def test_parent_goal_proposal_conflict_panel_is_visibility_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineParentGoalProposalConflictPanelV1"):
        text.index("window.renderAionGoalEngineParentGoalProposalConflictPanelV1")
    ]

    assert "visibility only" in block
    assert "would_mutate_parent_goal" in block
    assert "would_execute" in block
    assert "manual_review_required" in block


def test_parent_goal_proposal_conflict_panel_mounts_after_parent_child_panel():
    text = APP.read_text()
    assert "renderAionGoalEngineParentGoalProposalConflictPanelV1(source)" in text

    parent_child_idx = text.index("renderAionGoalEngineParentChildOrchestrationPanelV1")
    proposal_idx = text.index("renderAionGoalEngineParentGoalProposalConflictPanelV1")
    assert proposal_idx > parent_child_idx


def test_parent_goal_proposal_conflict_panel_exported():
    text = APP.read_text()
    assert "window.renderAionGoalEngineParentGoalProposalConflictPanelV1" in text


def test_parent_goal_proposal_conflict_lock_added_to_focused_suite():
    text = SUITE.read_text()
    assert "test_goal_engine_boardroom_parent_goal_proposal_conflict_ui_lock.py" in text
