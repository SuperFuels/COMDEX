from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text():
    return APP.read_text()


def _replay_history_block():
    text = _text()
    start = text.index("AION PATCH: Goal Engine Multi-Agent Execution Replay Boardroom Visibility v1")
    end = text.index("AION PATCH: Goal Engine Human-Approved Conflict Resolution Boardroom Visibility v1")
    return text[start:end]


def test_multi_agent_replay_history_helpers_exist():
    block = _replay_history_block()
    assert "AION_GOAL_ENGINE_MULTI_AGENT_REPLAY_HISTORY_V1" in block
    assert "function readAionGoalEngineMultiAgentReplayHistoryV1" in block
    assert "function writeAionGoalEngineMultiAgentReplayHistoryV1" in block
    assert "function recordAionGoalEngineMultiAgentReplaySnapshotV1" in block


def test_multi_agent_replay_history_uses_local_storage_guardedly():
    block = _replay_history_block()
    assert "window.localStorage.getItem" in block
    assert "window.localStorage.setItem" in block
    assert "try {" in block
    assert "catch" in block


def test_multi_agent_replay_history_records_canonical_payload():
    block = _replay_history_block()
    assert "run_id" in block
    assert "workflow_id" in block
    assert "recorded_at" in block
    assert "aggregation_count" in block
    assert "parent_child_aggregation_previews" in block
    assert "orchestrator_parent_child_aggregation_previews" in block
    assert "child_agent_conflict_preview" in block
    assert "parent_goal_update_proposal" in block


def test_multi_agent_replay_history_is_bounded():
    block = _replay_history_block()
    assert ".slice(0, 25)" in block or ".slice(0,25)" in block
    assert "dedupeKey" in block


def test_multi_agent_replay_panel_renders_history():
    block = _replay_history_block()
    assert "Replay History" in block
    assert "replayHistory" in block
    assert "No replay history stored yet" in block


def test_multi_agent_replay_history_is_recorded_when_panel_mounts():
    block = _replay_history_block()
    assert "recordAionGoalEngineMultiAgentReplaySnapshotV1(source)" in block


def test_multi_agent_replay_history_lock_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_goal_engine_multi_agent_execution_replay_history_ui_lock.py" in suite
