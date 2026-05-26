from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_child_run_executor_bridge_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text() -> str:
    return DOC.read_text()


def test_child_run_executor_bridge_lock_doc_exists():
    assert DOC.exists()


def test_child_run_executor_bridge_lock_doc_status_and_result():
    text = _text()
    assert "Status: LOCKED" in text
    assert "460 passed" in text


def test_child_run_executor_bridge_lock_doc_schema_and_trace():
    text = _text()
    assert "aion.goal_engine.child_run_executor_bridge.v1" in text
    assert "child_run_executor_bridge_packet" in text
    assert "build_child_run_executor_bridge_packet" in text


def test_child_run_executor_bridge_lock_doc_runtime_seed_contract():
    text = _text()
    assert "runtime_seed.workflow_id" in text
    assert "runtime_seed.run_id" in text
    assert "MUST NOT be used as fallback execution inputs" in text


def test_child_run_executor_bridge_lock_doc_approval_gates():
    text = _text()
    assert "child_run_creation_allowed = true" in text
    assert "approval_decision = approved" in text
    assert "requires_runtime_executor = true" in text
    assert "workflow_run_creation_allowed" in text


def test_child_run_executor_bridge_lock_doc_safety_invariants():
    text = _text()
    assert "does not create child runs directly" in text
    assert "creates no external side effects" in text
    assert "does not allow autonomous execution" in text
    assert "external_writes_allowed = false" in text
    assert "business_mutation_allowed = false" in text
    assert "fail closed" in text


def test_child_run_executor_bridge_lock_doc_footer():
    text = _text()
    assert "Lock ID: AION-GOAL-ENGINE-CHILD-RUN-EXECUTOR-BRIDGE-v1" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_child_run_executor_bridge_lock_doc_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_goal_engine_child_run_executor_bridge_lock_doc.py" in suite
