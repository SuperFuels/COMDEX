from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_human_approved_conflict_resolution_panel_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineHumanApprovedConflictResolutionPanelV1" in text
    assert 'data-aion-goal-engine-human-approved-conflict-resolution="v1"' in text
    assert "Human-Approved Conflict Resolution" in text
    assert "conflict_resolution_human_review" in text


def test_human_approved_conflict_resolution_panel_reads_canonical_payloads():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineHumanApprovedConflictResolutionPanelV1"):
        text.index("window.renderAionGoalEngineHumanApprovedConflictResolutionPanelV1")
    ]

    assert "human_approved_conflict_resolution_preview" in block
    assert "child_agent_conflict_preview" in block
    assert "parent_goal_update_proposal" in block
    assert "conflict_resolution_human_review" in block
    assert "human_decision" in block
    assert "reviewer" in block


def test_human_approved_conflict_resolution_panel_is_review_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineHumanApprovedConflictResolutionPanelV1"):
        text.index("window.renderAionGoalEngineHumanApprovedConflictResolutionPanelV1")
    ]

    assert "Review only" in block
    assert "No automatic resolution" in block
    assert "No parent-goal mutation" in block
    assert "No child-agent execution" in block


def test_human_approved_conflict_resolution_mount_exists():
    text = APP.read_text()
    assert "window.mountAionGoalEngineHumanApprovedConflictResolutionPanelV1" in text
    assert "renderAionGoalEngineHumanApprovedConflictResolutionPanelV1(source)" in text


def test_human_approved_conflict_resolution_registered_after_parent_conflict_panel():
    text = APP.read_text()
    conflict_idx = text.index("renderAionGoalEngineParentGoalProposalConflictPanelV1")
    resolution_idx = text.index("renderAionGoalEngineHumanApprovedConflictResolutionPanelV1")
    assert conflict_idx < resolution_idx


def test_human_approved_conflict_resolution_lock_in_focused_suite():
    text = SUITE.read_text()
    assert "test_goal_engine_human_approved_conflict_resolution_ui_lock.py" in text
