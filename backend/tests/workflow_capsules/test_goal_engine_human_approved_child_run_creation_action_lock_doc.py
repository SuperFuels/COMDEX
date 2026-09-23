from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_human_approved_child_run_creation_action_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text():
    return DOC.read_text()


def test_human_approved_child_run_creation_action_lock_doc_exists():
    assert DOC.exists()


def test_human_approved_child_run_creation_action_lock_doc_status_and_result():
    text = _text()
    assert "Status: LOCKED" in text
    assert "447 passed" in text


def test_human_approved_child_run_creation_action_lock_doc_schema_and_trace():
    text = _text()
    assert "aion.goal_engine.human_approved_child_run_creation_action.v1" in text
    assert "human_approved_child_run_creation_action" in text
    assert "build_human_approved_child_run_creation_action" in text


def test_human_approved_child_run_creation_action_lock_doc_runtime_seed_contract():
    text = _text()
    assert "child_run_creation_allowed" in text
    assert "requires_runtime_executor" in text
    assert "reviewer identifier" in text
    assert "target workflow identifier" in text
    assert "target child run identifier" in text


def test_human_approved_child_run_creation_action_lock_doc_safety_invariants():
    text = _text()
    assert "MUST NOT directly create a child run" in text
    assert "autonomous_execution = false" in text
    assert "external_writes_allowed = false" in text
    assert "business_mutation_allowed = false" in text
    assert "fail closed" in text


def test_human_approved_child_run_creation_action_lock_doc_footer():
    text = _text()
    assert "Lock ID: AION-GOAL-ENGINE-HUMAN-APPROVED-CHILD-RUN-CREATION-ACTION-v1" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_human_approved_child_run_creation_action_lock_doc_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_goal_engine_human_approved_child_run_creation_action_lock_doc.py" in suite
