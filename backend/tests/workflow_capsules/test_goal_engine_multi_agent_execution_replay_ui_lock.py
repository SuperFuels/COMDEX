from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_multi_agent_execution_replay_panel_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineMultiAgentExecutionReplayPanelV1" in text
    assert 'data-aion-goal-engine-multi-agent-execution-replay="v1"' in text
    assert "Multi-Agent Execution Replay" in text
    assert "Replay only" in text


def test_multi_agent_execution_replay_reads_parent_child_payloads():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineMultiAgentExecutionReplayPanelV1"):
        text.index("window.renderAionGoalEngineMultiAgentExecutionReplayPanelV1")
    ]

    assert "orchestrator_parent_child_aggregation_runtime_summary" in block
    assert "parent_child_aggregation_runtime_summary" in block
    assert "parent_child_aggregation_previews" in block
    assert "orchestrator_parent_child_aggregation_previews" in block
    assert "child_agents" in block
    assert "child_glyphs" in block
    assert "parent_goal_update_proposal" in block
    assert "child_agent_conflict_preview" in block


def test_multi_agent_execution_replay_is_dry_run_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineMultiAgentExecutionReplayPanelV1"):
        text.index("window.renderAionGoalEngineMultiAgentExecutionReplayPanelV1")
    ]

    assert "would_execute" in block
    assert "would_mutate_parent_goal" in block
    assert "would_auto_resolve" in block
    assert "manual_review_required" in block
    assert "dry_run_only" in block


def test_multi_agent_execution_replay_mounts_into_boardroom():
    text = APP.read_text()
    assert "mountAionGoalEngineMultiAgentExecutionReplayPanelV1" in text
    assert "renderAionGoalEngineMultiAgentExecutionReplayPanelV1(source)" in text
    assert "aion-boardroom-runtime-root" in text


def test_multi_agent_execution_replay_exports_renderer():
    text = APP.read_text()
    assert "window.renderAionGoalEngineMultiAgentExecutionReplayPanelV1" in text
    assert "window.mountAionGoalEngineMultiAgentExecutionReplayPanelV1" in text


def test_multi_agent_execution_replay_lock_is_in_focused_suite():
    text = SUITE.read_text()
    assert "test_goal_engine_multi_agent_execution_replay_ui_lock.py" in text
