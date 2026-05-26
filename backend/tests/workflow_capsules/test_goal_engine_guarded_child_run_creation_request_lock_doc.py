from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_guarded_child_run_creation_request_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text():
    return DOC.read_text()


def test_guarded_child_run_creation_request_lock_doc_exists():
    assert DOC.exists()


def test_guarded_child_run_creation_request_lock_doc_status_and_result():
    text = _text()
    assert "Status: LOCKED" in text
    assert "441 passed" in text


def test_guarded_child_run_creation_request_lock_doc_schema_and_trace():
    text = _text()
    assert "aion.goal_engine.guarded_child_run_creation_request.v1" in text
    assert "guarded_child_run_creation_request" in text
    assert "build_guarded_child_run_creation_request" in text


def test_guarded_child_run_creation_request_lock_doc_preserves_links():
    text = _text()
    assert "parent goal identity" in text
    assert "child goal identity" in text
    assert "child agent identity" in text
    assert "target workflow identity" in text
    assert "target child run identity" in text


def test_guarded_child_run_creation_request_lock_doc_safety_invariants():
    text = _text()
    assert "MUST NOT" in text
    assert "create a workflow run directly" in text
    assert "execute a child agent" in text
    assert "resolve a conflict automatically" in text
    assert "write externally" in text
    assert "grant permissions" in text
    assert "child_run_created" in text
    assert "MUST remain false" in text


def test_guarded_child_run_creation_request_lock_doc_footer():
    text = _text()
    assert "Lock ID: AION-GOAL-ENGINE-GUARDED-CHILD-RUN-CREATION-REQUEST-v1" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_guarded_child_run_creation_request_lock_doc_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_goal_engine_guarded_child_run_creation_request_lock_doc.py" in suite
