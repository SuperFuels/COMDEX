from pathlib import Path


DOC = Path("docs/rfc/aion_goal_engine_child_run_creation_end_to_end_lock.tex")


def _text():
    return DOC.read_text()


def test_child_run_creation_e2e_lock_doc_exists():
    assert DOC.exists()


def test_child_run_creation_e2e_lock_doc_names_canonical_chain():
    text = _text()

    assert "guarded_child_agent_execution_handoff" in text
    assert "guarded_child_run_creation_request" in text
    assert "human_approved_child_run_creation_action" in text
    assert "runtime_seed" in text
    assert "child_run_executor_bridge_packet" in text
    assert "GoalEnginePreviewBundle" in text


def test_child_run_creation_e2e_lock_doc_locks_runtime_seed_boundary():
    text = _text()

    assert "The executor bridge MUST trust only canonical identifiers inside \\texttt{runtime\\_seed}" in text
    assert "child\\_run\\_seed" in text
    assert "compatibility" in text
    assert "not the canonical executor input" in text


def test_child_run_creation_e2e_lock_doc_locks_safety_invariants():
    text = _text()

    assert "execution_allowed = false" in text
    assert "writes_allowed = false" in text
    assert "child_run_created = false" in text
    assert "autonomous_execution = false" in text
    assert "external_writes_allowed = false" in text
    assert "business_mutation_allowed = false" in text
    assert "creates_external_side_effects = false" in text


def test_child_run_creation_e2e_lock_doc_records_current_green_counts():
    text = _text()

    assert "5 passed" in text
    assert "27 passed" in text
    assert "494 passed" in text


def test_child_run_creation_e2e_lock_doc_has_lock_footer():
    text = _text()

    assert "Lock ID: AION-GOAL-ENGINE-CHILD-RUN-CREATION-E2E-v1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
