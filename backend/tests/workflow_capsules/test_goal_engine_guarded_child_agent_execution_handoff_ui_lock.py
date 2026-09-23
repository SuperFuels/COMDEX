from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_guarded_child_agent_execution_handoff_panel_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1" in text
    assert 'data-aion-goal-engine-guarded-child-agent-execution-handoff="v1"' in text
    assert "Guarded Child-Agent Execution Handoff" in text
    assert "child_agent_execution_review" in text


def test_guarded_child_agent_execution_handoff_reads_canonical_payloads():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1"):
        text.index("window.renderAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1")
    ]

    assert "guarded_child_agent_execution_handoff_preview" in block
    assert "child_agent_execution_review" in block
    assert "parent_goal_id" in block
    assert "child_agent_id" in block
    assert "child_goal_id" in block
    assert "approval_gate" in block


def test_guarded_child_agent_execution_handoff_ui_is_visibility_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1"):
        text.index("window.renderAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1")
    ]

    assert "would_execute" in block
    assert "would_write_external" in block
    assert "would_mutate_parent_goal" in block
    assert "dry_run_only" in block
    assert "No execution" in block
    assert "No child-agent dispatch" in block


def test_guarded_child_agent_execution_handoff_mounts_after_resolution_panel():
    text = APP.read_text()
    assert "mountAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1" in text
    assert "renderAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1(source)" in text

    resolution_idx = text.index("renderAionGoalEngineHumanApprovedConflictResolutionPanelV1")
    handoff_idx = text.index("renderAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1")
    assert resolution_idx < handoff_idx


def test_guarded_child_agent_execution_handoff_window_exports_renderer():
    text = APP.read_text()
    assert "window.renderAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1" in text
    assert "window.mountAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1" in text


def test_guarded_child_agent_execution_handoff_lock_in_focused_suite():
    text = SUITE.read_text()
    assert "test_goal_engine_guarded_child_agent_execution_handoff_ui_lock.py" in text
