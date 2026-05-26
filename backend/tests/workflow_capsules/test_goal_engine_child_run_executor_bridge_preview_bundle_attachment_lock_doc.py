from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_child_run_executor_bridge_preview_bundle_attachment_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def _text():
    return DOC.read_text()


def test_child_run_executor_bridge_preview_bundle_attachment_lock_doc_exists():
    assert DOC.exists()


def test_child_run_executor_bridge_preview_bundle_attachment_lock_doc_status_and_result():
    text = _text()
    assert "Status: LOCKED" in text
    assert "472 passed" in text


def test_child_run_executor_bridge_preview_bundle_attachment_lock_doc_schema_and_trace():
    text = _text()
    assert "aion.goal_engine.child_run_executor_bridge_runtime_summary.v1" in text
    assert "child_run_executor_bridge_runtime_summary" in text
    assert "child_run_executor_bridge_packets" in text


def test_child_run_executor_bridge_preview_bundle_attachment_lock_doc_aliases():
    text = _text()
    assert "workflow_run_creation_bridge_runtime_summary" in text
    assert "workflow_run_creation_bridge_packets" in text
    assert "machine_trace" in text


def test_child_run_executor_bridge_preview_bundle_attachment_lock_doc_safety_invariants():
    text = _text()
    assert "dry_run_only = true" in text
    assert "would_execute = false" in text
    assert "would_write_external = false" in text
    assert "would_grant_permission = false" in text
    assert "would_mutate_business_state = false" in text


def test_child_run_executor_bridge_preview_bundle_attachment_lock_doc_footer():
    text = _text()
    assert (
        "Lock ID: AION-GOAL-ENGINE-CHILD-RUN-EXECUTOR-BRIDGE-PREVIEW-BUNDLE-ATTACHMENT-v1"
        in text
    )
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text


def test_child_run_executor_bridge_preview_bundle_attachment_lock_doc_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_goal_engine_child_run_executor_bridge_preview_bundle_attachment_lock_doc.py" in suite
