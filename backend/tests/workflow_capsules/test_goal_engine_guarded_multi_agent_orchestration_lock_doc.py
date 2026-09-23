from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_guarded_multi_agent_orchestration_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_guarded_multi_agent_orchestration_lock_doc_exists():
    assert DOC.exists()


def test_guarded_multi_agent_orchestration_lock_doc_status_and_result():
    text = DOC.read_text()
    assert "Status: LOCKED" in text
    assert "395 passed" in text
    assert "bash scripts/run_goal_engine_focused_lock_suite.sh" in text


def test_guarded_multi_agent_orchestration_lock_doc_runtime_contracts():
    text = DOC.read_text()
    assert "guarded_child_agent_execution_handoff_preview" in text
    assert "human_approved_conflict_resolution_preview" in text
    assert "parent_goal_update_proposal" in text
    assert "child_agent_conflict_preview" in text


def test_guarded_multi_agent_orchestration_lock_doc_approval_gates():
    text = DOC.read_text()
    assert "child_agent_execution_review" in text
    assert "conflict_resolution_human_review" in text


def test_guarded_multi_agent_orchestration_lock_doc_safety_invariants():
    text = DOC.read_text()
    assert "MUST NOT auto-resolve" in text
    assert "MUST NOT mutate a parent goal" in text
    assert "MUST NOT execute child agents" in text
    assert "MUST NOT grant permissions" in text


def test_guarded_multi_agent_orchestration_lock_doc_footer():
    text = DOC.read_text()
    assert "Lock ID: AION-GOAL-ENGINE-GUARDED-MULTI-AGENT-ORCHESTRATION-v1" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_guarded_multi_agent_orchestration_lock_doc_in_focused_suite():
    text = SUITE.read_text()
    assert "test_goal_engine_guarded_multi_agent_orchestration_lock_doc.py" in text
