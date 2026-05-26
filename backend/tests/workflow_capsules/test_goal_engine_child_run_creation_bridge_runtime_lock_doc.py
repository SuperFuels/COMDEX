from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_child_run_creation_bridge_runtime_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text() -> str:
    return DOC.read_text()


def test_child_run_creation_bridge_lock_doc_exists():
    assert DOC.exists()
    text = _text()
    assert "AION Goal Engine Child-Run Creation Bridge Runtime Lock" in text
    assert "AION-GOAL-ENGINE-CHILD-RUN-CREATION-BRIDGE-RUNTIME-v1" in text


def test_child_run_creation_bridge_lock_doc_marks_runtime_seed_canonical():
    text = _text()
    assert "runtime\\_seed" in text
    assert "MUST trust \\texttt{runtime\\_seed} only" in text


def test_child_run_creation_bridge_lock_doc_keeps_child_run_seed_compatibility_only():
    text = _text()
    assert "child\\_run\\_seed" in text
    assert "compatibility and provenance" in text
    assert "MUST NOT override \\texttt{runtime\\_seed}" in text


def test_child_run_creation_bridge_lock_doc_blocks_bad_packets():
    text = _text()
    assert "blocked packet MUST NOT create" in text
    assert "packet status is not \\texttt{ready\\_for\\_workflow\\_runtime}" in text
    assert "\\texttt{runtime\\_seed} is missing" in text


def test_child_run_creation_bridge_lock_doc_is_dry_run_only():
    text = _text()
    assert "dry-run first" in text
    assert "does not create live external effects" in text


def test_child_run_creation_bridge_lock_doc_forbids_execution_mutation_permission_grants():
    text = _text()
    assert "Execute live external writes" in text
    assert "Mutate parent goals" in text
    assert "Mutate child goals" in text
    assert "Mutate business containers" in text
    assert "Grant permissions" in text
    assert "Bypass human approval" in text


def test_child_run_creation_bridge_lock_doc_sets_switch_boundary():
    text = _text()
    assert "Goal Engine sprint is switch-ready" in text
    assert "AION Agent Gateway v0" in text
    assert "backend-only, dry-run-only, contract-first" in text


def test_child_run_creation_bridge_lock_doc_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_goal_engine_child_run_creation_bridge_runtime_lock_doc.py" in suite
