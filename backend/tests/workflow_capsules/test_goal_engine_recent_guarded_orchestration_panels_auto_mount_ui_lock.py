from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text() -> str:
    return APP.read_text()


def test_recent_guarded_orchestration_auto_mount_bridge_exists():
    text = _text()
    assert "AION PATCH: Goal Engine Recent Guarded Orchestration Panels Auto-Mount Bridge v1" in text
    assert "mountAionGoalEngineRecentGuardedOrchestrationPanelsV1" in text
    assert "data-aion-goal-engine-recent-guarded-orchestration-panels-mounted" in text


def test_recent_guarded_orchestration_auto_mount_calls_recent_panels():
    text = _text()
    assert "mountAionGoalEngineMultiAgentExecutionReplayPanelV1?.(payload)" in text
    assert "mountAionGoalEngineGuardedChildAgentExecutionHandoffPanelV1?.(payload)" in text
    assert "mountAionGoalEngineChildRunExecutorBridgePanelV1?.(payload)" in text
    assert "mountAionGoalEngineHumanApprovedConflictResolutionPanelV1?.(payload)" in text


def test_recent_guarded_orchestration_auto_mount_uses_boardroom_roots():
    text = _text()
    assert "data-aion-goal-engine-boardroom-runtime-preview-root" in text
    assert "data-aion-boardroom-runtime-preview" in text
    assert ".aion-boardroom-runtime-preview" in text
    assert "data-aion-goal-engine-parent-child-orchestration" in text
    assert "data-aion-goal-engine-parent-goal-proposal-conflict" in text


def test_recent_guarded_orchestration_auto_mount_is_visibility_only():
    text = _text()
    assert "visibility-only" in text
    assert "does not execute child agents" in text
    assert "does not execute child agents, resolve conflicts" in text
    assert "write externally" in text
    assert "grant permissions" in text


def test_recent_guarded_orchestration_auto_mount_has_retry_bridge():
    text = _text()
    assert "window.setInterval" in text
    assert "attempts >= 20" in text
    assert "window.clearInterval(timer)" in text


def test_recent_guarded_orchestration_auto_mount_lock_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_goal_engine_recent_guarded_orchestration_panels_auto_mount_ui_lock.py" in suite
