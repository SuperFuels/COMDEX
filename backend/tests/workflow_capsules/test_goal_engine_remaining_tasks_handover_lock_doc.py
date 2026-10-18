from pathlib import Path


DOC = Path("docs/rfc/aion_goal_engine_remaining_tasks_handover.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _doc_text():
    return DOC.read_text()


def test_remaining_tasks_handover_doc_exists():
    assert DOC.exists()


def test_remaining_tasks_handover_doc_states_current_green_status():
    text = _doc_text()

    assert "AION Goal Engine Remaining Tasks Handover" in text
    assert "focused Goal Engine lock suite passing with 505 tests" in text
    assert "505 passed" in text


def test_remaining_tasks_handover_doc_explains_what_we_are_building():
    text = _doc_text()

    assert "guarded planning and orchestration layer" in text
    assert "not about free autonomous execution yet" in text
    assert "locking the contracts that make future execution safe" in text


def test_remaining_tasks_handover_doc_preserves_canonical_lessons():
    text = _doc_text()

    assert "child\\_run\\_creation\\_request\\_valid" in text
    assert "runtime\\_seed" in text
    assert "child\\_run\\_seed" in text
    assert "executor bridge must trust only" in text


def test_remaining_tasks_handover_doc_has_single_remaining_task_list():
    text = _doc_text()

    assert "\\subsection{Single Remaining Task List}" in text
    assert "Boardroom surface for child-run executor bridge packets" in text
    assert "real Workflow Capsule run creation behind explicit approval" in text
    assert "real evidence source ingestion" in text
    assert "simple user-facing Goal Engine tab" in text


def test_remaining_tasks_handover_doc_blocks_unsafe_next_steps():
    text = _doc_text()

    assert "Do Not Do Yet" in text
    assert "Do not yet connect child-run bridge packets to real Workflow Capsule execution" in text
    assert "Do not yet allow autonomous conflict resolution" in text
    assert "Do not yet mutate parent goals, child goals, business containers, or external systems" in text


def test_remaining_tasks_handover_doc_has_lock_footer():
    text = _doc_text()

    assert "Lock ID: AION-GOAL-ENGINE-REMAINING-TASKS-HANDOVER-v1" in text
    assert "Status: ACTIVE HANDOVER" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_remaining_tasks_handover_lock_is_in_focused_suite():
    text = SUITE.read_text()

    assert "test_goal_engine_remaining_tasks_handover_lock_doc.py" in text
