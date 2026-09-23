from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text() -> str:
    return APP.read_text()


def _block() -> str:
    text = _text()
    start = text.index("AION PATCH: Goal Engine Child-Run Executor Bridge Boardroom Visibility v1")
    end = text.index("console.log(\"[AION] Goal Engine Child-Run Executor Bridge Boardroom Visibility v1 installed\")", start)
    return text[start:end]


def test_child_run_executor_bridge_boardroom_panel_exists():
    text = _text()

    assert "AION PATCH: Goal Engine Child-Run Executor Bridge Boardroom Visibility v1" in text
    assert "renderAionGoalEngineChildRunExecutorBridgePanelV1" in text
    assert "mountAionGoalEngineChildRunExecutorBridgePanelV1" in text
    assert 'data-aion-goal-engine-child-run-executor-bridge="v1"' in text


def test_child_run_executor_bridge_boardroom_reads_canonical_summary_and_aliases():
    block = _block()

    assert "child_run_executor_bridge_runtime_summary" in block
    assert "workflow_run_creation_bridge_runtime_summary" in block
    assert "child_run_executor_bridge_packets" in block
    assert "workflow_run_creation_bridge_packets" in block
    assert "child_run_executor_bridge_packet" in block
    assert "ready_for_workflow_runtime" in block


def test_child_run_executor_bridge_boardroom_shows_seed_identity_and_reviewer():
    block = _block()

    assert "runtime_seed" in block
    assert "workflow_id" in block
    assert "run_id" in block
    assert "reviewer_id" in block
    assert "blocked_reasons" in block


def test_child_run_executor_bridge_boardroom_is_visibility_only():
    block = _block()

    assert "Visibility only" in block
    assert "review-only bridge packets" in block
    assert "No execute button" in block
    assert "No Workflow Capsule run creation from this panel" in block
    assert "would_execute" in block
    assert "would_write_external" in block
    assert "would_grant_permission" in block
    assert "would_mutate_business_state" in block


def test_child_run_executor_bridge_boardroom_has_no_execute_button_or_runtime_creation_call():
    block = _block().lower()

    assert "createworkflowcapsulerun" not in block
    assert "executechildrun" not in block
    assert "runchildagent" not in block
    assert "sendemail" not in block
    assert "<button" not in block


def test_child_run_executor_bridge_boardroom_mount_uses_boardroom_roots():
    block = _block()

    assert "data-aion-goal-engine-boardroom-runtime-preview-root" in block
    assert "data-aion-boardroom-runtime-preview-root" in block
    assert "data-aion-boardroom-runtime-preview" in block
    assert ".aion-boardroom-runtime-preview" in block


def test_child_run_executor_bridge_boardroom_lock_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_goal_engine_child_run_executor_bridge_boardroom_ui_lock.py" in suite
