from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.contracts.department_pilot import (
    BoardroomAssignmentAction,
    canonical_contract_hash,
)
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.department_context_assembler import (
    DepartmentContextAssembler,
)
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    approve_assignment_package,
    create_assignment_package,
    create_boardroom_handback,
    create_execution_receipt,
    create_context_reference,
    create_provenance,
)
from backend.modules.aion_business.runtime.department_pilot_repository import (
    DepartmentPilotConcurrencyError,
    DepartmentPilotRepository,
)
from backend.modules.aion_business.runtime.department_pilot_runtime import DepartmentPilotRuntime


def _package():
    provenance = create_provenance(
        created_by="boardroom",
        created_at="2026-07-16T21:00:00+00:00",
        source_system="aion_boardroom",
    )
    package = create_assignment_package(
        package_id="package-restart-test",
        workspace_id="home-fixed",
        business_id="home-fixed",
        boardroom_session_id="board-session-restart",
        boardroom_decision_id="board-decision-restart",
        title="Finance management summary",
        objective="Prepare a source-grounded Finance summary.",
        department_id="finance",
        actions=[
            BoardroomAssignmentAction(
                action_id="action-restart",
                title="Prepare Finance summary",
                objective="Summarise accepted Finance evidence for the Board.",
                department_id="finance",
                capability="kpi.dashboard",
                acceptance_criteria=["Identify evidence status for every material figure"],
            )
        ],
        provenance=provenance,
    )
    return (
        approve_assignment_package(
            package,
            approval_id="package-approval-restart",
            approved_by="kevin",
            approved_at="2026-07-16T21:01:00+00:00",
        ),
        provenance,
    )


def test_task_survives_runtime_restart_and_completes_with_stored_receipt(tmp_path):
    package, provenance = _package()
    first_runtime = DepartmentPilotRuntime(DepartmentPilotRepository(tmp_path))
    created = first_runtime.enqueue_approved_action(
        package=package,
        action_id="action-restart",
        task_id="finance-task-restart",
        pilot_id="finance_pilot",
        assigned_at="2026-07-16T21:02:00+00:00",
        provenance=provenance,
        created_event_id="event-created",
    )
    first_runtime.transition(
        workspace_id="home-fixed",
        department_id="finance",
        task_id=created.task.task_id,
        to_status="claimed",
        occurred_at="2026-07-16T21:03:00+00:00",
        actor_id="finance_pilot",
        event_id="event-claimed",
    )

    # A fresh runtime instance represents an application/backend restart.
    restarted_repository = DepartmentPilotRepository(tmp_path)
    restarted_runtime = DepartmentPilotRuntime(restarted_repository)
    restored = restarted_repository.load("home-fixed", "finance", "finance-task-restart")
    assert restored.task.status == "claimed"
    assert restored.package.package_hash == package.package_hash

    running = restarted_runtime.transition(
        workspace_id="home-fixed",
        department_id="finance",
        task_id="finance-task-restart",
        to_status="running",
        occurred_at="2026-07-16T21:04:00+00:00",
        actor_id="finance_pilot",
        event_id="event-running",
        progress_percent=10,
    )
    with_turn = restarted_runtime.append_conversation_turn(
        workspace_id="home-fixed",
        department_id="finance",
        task_id="finance-task-restart",
        turn_id="turn-restart",
        role="assistant",
        content="I am preparing the source-grounded Finance summary.",
        created_at="2026-07-16T21:05:00+00:00",
        actor_id="finance_pilot",
    )
    assert len(with_turn.conversation) == 1

    receipt = create_execution_receipt(
        receipt_id="receipt-restart",
        task_id="finance-task-restart",
        department_id="finance",
        outcome="succeeded",
        started_at=running.task.started_at,
        completed_at="2026-07-16T21:10:00+00:00",
        artifact_ids=[],
        evidence_hashes=[],
        approval_ids=[],
    )
    handback = create_boardroom_handback(
        handback_id="handback-restart",
        package_id=package.package_id,
        task_id="finance-task-restart",
        department_id="finance",
        status="ready_for_boardroom",
        outcome="succeeded",
        executive_summary="Finance summary completed from accepted evidence.",
        completed_actions=["Prepared Finance summary"],
        receipt_ids=[receipt.receipt_id],
        created_at="2026-07-16T21:10:00+00:00",
        created_by="finance_pilot",
    )
    completed = restarted_runtime.complete(
        workspace_id="home-fixed",
        department_id="finance",
        task_id="finance-task-restart",
        completed_at="2026-07-16T21:10:00+00:00",
        actor_id="finance_pilot",
        event_id="event-completed",
        receipt=receipt,
        handback=handback,
    )

    third_repository = DepartmentPilotRepository(tmp_path)
    final = third_repository.load("home-fixed", "finance", "finance-task-restart")
    assert completed.envelope_hash == final.envelope_hash
    assert final.task.status == "completed"
    assert final.receipts[0].receipt_id == "receipt-restart"
    assert final.handback.status == "ready_for_boardroom"
    assert [item.task.task_id for item in third_repository.list_for_department(
        "home-fixed", "finance", statuses=["completed"]
    )] == ["finance-task-restart"]

    audit_lines = third_repository.audit_path("home-fixed", "finance").read_text().splitlines()
    audit = [json.loads(line) for line in audit_lines]
    assert audit[0]["operation"] == "created"
    assert audit[-1]["receipt_count"] == 1
    assert len(audit) == 5


def test_repository_rejects_stale_concurrent_writer(tmp_path):
    package, provenance = _package()
    repository = DepartmentPilotRepository(tmp_path)
    runtime = DepartmentPilotRuntime(repository)
    stale = runtime.enqueue_approved_action(
        package=package,
        action_id="action-restart",
        task_id="finance-task-concurrency",
        pilot_id="finance_pilot",
        assigned_at="2026-07-16T21:02:00+00:00",
        provenance=provenance,
        created_event_id="event-concurrency-created",
    )
    runtime.transition(
        workspace_id="home-fixed",
        department_id="finance",
        task_id="finance-task-concurrency",
        to_status="claimed",
        occurred_at="2026-07-16T21:03:00+00:00",
        actor_id="finance_pilot",
        event_id="event-concurrency-claimed",
    )
    with pytest.raises(DepartmentPilotConcurrencyError, match="stale_write"):
        repository.save(stale, expected_previous_hash=stale.envelope_hash)


def test_context_retrieval_is_selective_hash_bound_and_persisted(tmp_path):
    container_repository = BusinessContainerRepository(tmp_path / "containers")
    financial_model = {
        "id": "home-fixed.business_financial_model",
        "workspace_id": "home-fixed",
        "kind": "business_financial_model",
        "model_status": "accepted",
        "currency": "EUR",
        "period_basis": "annual",
        "metrics": {"revenue": 378750, "gross_profit": 235016},
        "assumptions": [{"field": "growth", "value": 0.05}],
        "missing_information": ["current supplier ageing"],
        "evidence_refs": [{"source": "management_accounts_2025.xlsx"}],
        "external_data": {"raw_xero_payload": "must not enter the agent prompt wholesale"},
        "revision": 4,
    }
    container_repository.save_dict(
        "home-fixed", "business_financial_model", financial_model
    )
    reference = create_context_reference(
        reference_id="finance-model-exact-r4",
        workspace_id="home-fixed",
        container_kind="business_financial_model",
        container_id="home-fixed.business_financial_model",
        revision=4,
        content_hash=canonical_contract_hash(financial_model),
        verification_state="source_backed",
    )
    provenance = create_provenance(
        created_by="boardroom",
        created_at="2026-07-16T22:00:00+00:00",
    )
    package = create_assignment_package(
        package_id="package-context",
        workspace_id="home-fixed",
        business_id="home-fixed",
        boardroom_session_id="session-context",
        boardroom_decision_id="decision-context",
        title="Finance context test",
        objective="Use exact approved Finance context.",
        department_id="finance",
        actions=[
            BoardroomAssignmentAction(
                action_id="action-context",
                title="Summarise Finance context",
                objective="Summarise exact accepted figures.",
                department_id="finance",
                capability="kpi.dashboard",
            )
        ],
        context_refs=[reference],
        provenance=provenance,
    )
    package = approve_assignment_package(
        package,
        approval_id="approval-context",
        approved_by="kevin",
        approved_at="2026-07-16T22:01:00+00:00",
    )
    runtime_repository = DepartmentPilotRepository(tmp_path / "runtime")
    runtime = DepartmentPilotRuntime(runtime_repository)
    envelope = runtime.enqueue_approved_action(
        package=package,
        action_id="action-context",
        task_id="task-context",
        pilot_id="finance_pilot",
        assigned_at="2026-07-16T22:02:00+00:00",
        provenance=provenance,
        created_event_id="event-context",
    )

    assembler = DepartmentContextAssembler(container_repository)
    evidence = assembler.retrieve_for_task(
        envelope.task,
        retrieved_at="2026-07-16T22:03:00+00:00",
        retrieved_by="finance_pilot",
    )
    assert evidence[0].retrieval_status == "retrieved"
    assert evidence[0].data["metrics"]["revenue"] == 378750
    assert "external_data" not in evidence[0].data
    runtime.attach_retrieved_evidence(
        workspace_id="home-fixed",
        department_id="finance",
        task_id="task-context",
        evidence=evidence,
    )
    restored = DepartmentPilotRepository(tmp_path / "runtime").load(
        "home-fixed", "finance", "task-context"
    )
    assert restored.retrieved_evidence[0].retrieval_hash == evidence[0].retrieval_hash

    changed = {**financial_model, "revision": 5}
    container_repository.save_dict(
        "home-fixed", "business_financial_model", changed
    )
    stale = assembler.retrieve_for_task(
        envelope.task,
        retrieved_at="2026-07-16T22:04:00+00:00",
        retrieved_by="finance_pilot",
    )
    assert stale[0].retrieval_status == "hash_mismatch"
    assert stale[0].verification_state == "stale"
    assert stale[0].issue == "business_container_changed_since_boardroom_approval"
