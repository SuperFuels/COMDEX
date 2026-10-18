from __future__ import annotations

from backend.modules.local_node.contracts_local_node import LocalNodeConfig
from backend.modules.local_node.local_node_runtime import LocalNodeRuntime


def test_run_can_pause_for_approval_and_resume(tmp_path):
    runtime = LocalNodeRuntime(
        LocalNodeConfig(
            node_id="test_node_01",
            workspace_id="test_workspace",
            base_dir=str(tmp_path),
        )
    )
    runtime.start()

    launch = runtime.enqueue_workflow(
        workflow_id="workflow_marketing_content_draft_v1",
        operator_id="operator_marketing_v1",
        department_key="marketing",
        payload={
            "brief": "Needs approval",
            "require_approval": True,
        },
    )
    queue_item_id = launch["item"]["id"]

    run_result = runtime.run_next()
    assert run_result["ok"] is True
    assert run_result["status"] == "waiting_approval"
    assert run_result["queue_item_id"] == queue_item_id

    runs = runtime.list_queue_items()["items"]
    assert len(runs) == 1
    assert runs[0]["status"] == "waiting_approval"

    approvals = runtime.list_approvals()["items"]
    assert len(approvals) == 1
    approval_id = approvals[0]["id"]
    assert approvals[0]["status"] == "pending"
    assert approvals[0]["queue_item_id"] == queue_item_id

    resolved = runtime.approval_store.resolve(
        approval_id,
        approve=True,
        resolved_by="tester",
        resolution_note="approved in test",
    )
    assert resolved is not None
    assert resolved.status == "approved"

    resume_result = runtime.resume_approval(queue_item_id)
    assert resume_result["ok"] is True
    assert resume_result["status"] == "completed"

    runs_after = runtime.list_queue_items()["items"]
    assert runs_after[0]["status"] == "completed"

    approvals_after = runtime.list_approvals()["items"]
    assert approvals_after[0]["status"] == "approved"

    audit_events = runtime.list_audit_events(limit=50)["items"]
    event_types = [event["event_type"] for event in audit_events]

    assert "local_node.workflow_waiting_approval" in event_types
    assert "local_node.workflow_resume_started" in event_types
    assert "local_node.workflow_resumed_completed" in event_types


def test_run_without_approval_completes(tmp_path):
    runtime = LocalNodeRuntime(
        LocalNodeConfig(
            node_id="test_node_02",
            workspace_id="test_workspace",
            base_dir=str(tmp_path),
        )
    )
    runtime.start()

    launch = runtime.enqueue_workflow(
        workflow_id="workflow_marketing_content_draft_v1",
        operator_id="operator_marketing_v1",
        department_key="marketing",
        payload={
            "brief": "No approval required",
        },
    )
    queue_item_id = launch["item"]["id"]

    run_result = runtime.run_next()
    assert run_result["ok"] is True
    assert run_result["status"] == "completed"
    assert run_result["queue_item_id"] == queue_item_id

    runs = runtime.list_queue_items()["items"]
    assert runs[0]["status"] == "completed"

    approvals = runtime.list_approvals()["items"]
    assert approvals == []