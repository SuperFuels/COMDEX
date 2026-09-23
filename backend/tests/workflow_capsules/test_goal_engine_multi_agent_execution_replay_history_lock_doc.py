from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_multi_agent_replay_history_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text():
    return DOC.read_text()


def test_replay_history_lock_doc_exists():
    assert DOC.exists()


def test_replay_history_lock_doc_status_and_result():
    text = _text()
    assert "Status: LOCKED" in text
    assert "420 passed" in text


def test_replay_history_lock_doc_frontend_contracts():
    text = _text()
    assert "AION_GOAL_ENGINE_MULTI_AGENT_REPLAY_HISTORY_V1" in text
    assert "recordAionGoalEngineMultiAgentReplaySnapshotV1" in text
    assert 'data-aion-goal-engine-multi-agent-execution-replay="v1"' in text


def test_replay_history_lock_doc_backend_contracts():
    text = _text()
    assert "aion.goal_engine.multi_agent_execution_replay_history.v1" in text
    assert "multi_agent_execution_replay_history_record" in text
    assert "build_multi_agent_execution_replay_history_record" in text
    assert "append_multi_agent_execution_replay_history_record" in text


def test_replay_history_lock_doc_safety_invariants():
    text = _text()
    assert "execute child agents" in text
    assert "mutate parent goals" in text
    assert "resolve conflicts automatically" in text
    assert "write externally" in text
    assert "grant connector permissions" in text


def test_replay_history_lock_doc_closed_task():
    text = _text()
    assert 'N4["Persist multi-agent replay history, not just render current preview"]' in text
    assert "frontend replay history is persisted locally" in text
    assert "backend replay history has a canonical persistence-safe record contract" in text


def test_replay_history_lock_doc_footer():
    text = _text()
    assert "Lock ID: AION-GOAL-ENGINE-MULTI-AGENT-REPLAY-HISTORY-v1" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_replay_history_lock_doc_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_goal_engine_multi_agent_execution_replay_history_lock_doc.py" in suite
