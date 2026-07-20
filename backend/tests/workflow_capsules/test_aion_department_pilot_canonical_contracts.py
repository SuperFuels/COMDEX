from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.modules.aion_business.contracts.department_pilot import (
    BoardroomAssignmentAction,
    BoardroomAssignmentPackage,
    DepartmentPilotWorkEnvelope,
    ProposedToolCall,
    canonical_contract_hash,
)
from backend.modules.aion_business.runtime.department_pilot_contracts import (
    adapt_legacy_capability_receipt,
    adapt_legacy_department_queue_item,
    approve_assignment_package,
    create_approval_record,
    create_assignment_package,
    create_boardroom_handback,
    create_context_reference,
    create_conversation_turn,
    create_department_artifact,
    create_execution_receipt,
    create_intelligence_patch,
    create_provenance,
    create_task_event,
    create_task_from_package,
    create_work_envelope,
    propose_tool_call,
    transition_department_task,
)
from backend.services.aion_mission_mode.capability_receipts import create_capability_receipt
from backend.services.aion_mission_mode.department_execution_queue import (
    create_department_queue_item,
)


NOW = "2026-07-16T20:00:00+00:00"


def _approved_finance_package():
    provenance = create_provenance(
        created_by="boardroom",
        created_at=NOW,
        source_system="aion_boardroom",
        source_record_id="decision-001",
        correlation_id="session-001",
    )
    context = create_context_reference(
        reference_id="finance-model-r4",
        workspace_id="home-fixed",
        container_kind="business_financial_model",
        container_id="home-fixed.business_financial_model",
        revision=4,
        content_hash=canonical_contract_hash({"revision": 4, "currency": "EUR"}),
        verification_state="source_backed",
        summary="Accepted 2025 management accounts and read-only Xero evidence.",
        evidence_refs=["file-cabinet://finance/management-accounts.xlsx"],
    )
    action = BoardroomAssignmentAction(
        action_id="finance-action-001",
        title="Prepare a 13-week cash forecast",
        objective="Model the next 13 weeks of cash using accepted Finance evidence.",
        department_id="finance",
        capability="cashflow.model",
        priority="high",
        acceptance_criteria=[
            "Show opening and closing cash by week",
            "Separate evidence, assumptions and recommendations",
        ],
        requested_artifact_types=["spreadsheet", "boardroom_summary"],
    )
    package = create_assignment_package(
        package_id="board-package-001",
        workspace_id="home-fixed",
        business_id="home-fixed",
        boardroom_session_id="session-001",
        boardroom_decision_id="decision-001",
        title="Finance cash visibility package",
        objective="Give the Board reliable forward cash visibility.",
        department_id="finance",
        actions=[action],
        context_refs=[context],
        constraints=["Read-only Xero access", "No payments or ledger writes"],
        provenance=provenance,
    )
    return approve_assignment_package(
        package,
        approval_id="package-approval-001",
        approved_by="kevin",
        approved_at="2026-07-16T20:01:00+00:00",
    ), provenance


def _completed_task(package, provenance):
    task = create_task_from_package(
        package,
        action_id="finance-action-001",
        task_id="finance-task-001",
        pilot_id="finance_pilot",
        assigned_at="2026-07-16T20:02:00+00:00",
        provenance=provenance,
    )
    task = transition_department_task(
        task, to_status="claimed", occurred_at="2026-07-16T20:03:00+00:00"
    )
    task = transition_department_task(
        task, to_status="running", occurred_at="2026-07-16T20:04:00+00:00"
    )
    return transition_department_task(
        task, to_status="completed", occurred_at="2026-07-16T20:10:00+00:00"
    )


def test_one_schema_family_covers_approved_action_through_boardroom_handback():
    package, provenance = _approved_finance_package()
    task = _completed_task(package, provenance)

    events = [
        create_task_event(
            event_id="event-001",
            task_id=task.task_id,
            department_id="finance",
            event_type="created",
            occurred_at="2026-07-16T20:02:00+00:00",
            actor_id="central_pilot",
            to_status="queued",
            progress_percent=0,
        ),
        create_task_event(
            event_id="event-002",
            task_id=task.task_id,
            department_id="finance",
            event_type="completed",
            occurred_at="2026-07-16T20:10:00+00:00",
            actor_id="finance_pilot",
            from_status="running",
            to_status="completed",
            progress_percent=100,
        ),
    ]
    turn = create_conversation_turn(
        turn_id="turn-001",
        task_id=task.task_id,
        department_id="finance",
        role="assistant",
        content="I have prepared the cash forecast for Boardroom review.",
        created_at="2026-07-16T20:09:00+00:00",
        actor_id="finance_pilot",
        context_refs=task.context_refs,
    )
    tool_call = propose_tool_call(
        tool_call_id="tool-call-001",
        task_id=task.task_id,
        department_id="finance",
        capability="file.write",
        tool_name="finance.file_cabinet.store",
        provider="local_business_container",
        tool_mode="approved_live_external",
        payload={
            "path": "Finance/Reports/13-week-cash-forecast.xlsx",
            "content_hash": canonical_contract_hash({"forecast": "v1"}),
        },
        rationale="Store the accepted report in the Finance file cabinet.",
        external_side_effect=True,
        approval_required=True,
        proposed_at="2026-07-16T20:07:00+00:00",
        proposed_by="finance_pilot",
    )
    approval = create_approval_record(
        approval_id="tool-approval-001",
        task_id=task.task_id,
        tool_call_id=tool_call.tool_call_id,
        department_id="finance",
        status="approved",
        requested_payload_hash=tool_call.payload_hash,
        decided_payload_hash=tool_call.payload_hash,
        requested_by="finance_pilot",
        requested_at="2026-07-16T20:07:00+00:00",
        decided_by="kevin",
        decided_at="2026-07-16T20:08:00+00:00",
        expires_at="2026-07-16T21:08:00+00:00",
    )
    artifact = create_department_artifact(
        artifact_id="artifact-001",
        task_id=task.task_id,
        department_id="finance",
        artifact_type="spreadsheet",
        title="13-week cash forecast",
        status="accepted",
        business_container_path=(
            "business_containers/home-fixed/finance/artifacts/13-week-cash-forecast.xlsx"
        ),
        file_cabinet_path="Finance/Reports/13-week-cash-forecast.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content_hash=canonical_contract_hash({"forecast": "v1"}),
        evidence_refs=["finance-model-r4"],
        created_at="2026-07-16T20:09:00+00:00",
        created_by="finance_pilot",
        provenance=provenance,
    )
    receipt = create_execution_receipt(
        receipt_id="receipt-001",
        task_id=task.task_id,
        department_id="finance",
        outcome="succeeded",
        started_at="2026-07-16T20:04:00+00:00",
        completed_at="2026-07-16T20:10:00+00:00",
        requested_payload_hash=tool_call.payload_hash,
        executed_payload_hash=tool_call.payload_hash,
        before_state_hash=canonical_contract_hash({"artifact": None}),
        after_state_hash=artifact.content_hash,
        artifact_ids=[artifact.artifact_id],
        evidence_hashes=[task.context_refs[0].content_hash],
        approval_ids=[approval.approval_id],
    )
    patch = create_intelligence_patch(
        patch_id="patch-001",
        task_id=task.task_id,
        department_id="finance",
        base_revision=4,
        operations=[
            {
                "op": "add",
                "path": "/departments/finance/latest_cash_forecast",
                "value": {"artifact_id": artifact.artifact_id, "weeks": 13},
            }
        ],
        evidence_refs=[receipt.receipt_id],
        verification_state="source_backed",
        created_at="2026-07-16T20:10:00+00:00",
        created_by="finance_pilot",
    )
    handback = create_boardroom_handback(
        handback_id="handback-001",
        package_id=package.package_id,
        task_id=task.task_id,
        department_id="finance",
        status="ready_for_boardroom",
        outcome="succeeded",
        executive_summary="The 13-week cash forecast is complete and source-linked.",
        completed_actions=["Prepared weekly cash forecast"],
        unresolved_items=["Confirm two supplier payment dates"],
        decisions_requested=["Approve the minimum cash reserve target"],
        metric_changes={"forecast_weeks": 13},
        artifact_ids=[artifact.artifact_id],
        receipt_ids=[receipt.receipt_id],
        intelligence_patch_ids=[patch.patch_id],
        evidence_refs=[task.context_refs[0].reference_id],
        created_at="2026-07-16T20:11:00+00:00",
        created_by="finance_pilot",
    )

    envelope = create_work_envelope(
        package=package,
        task=task,
        events=events,
        conversation=[turn],
        proposed_tool_calls=[tool_call],
        approvals=[approval],
        artifacts=[artifact],
        receipts=[receipt],
        intelligence_patches=[patch],
        handback=handback,
    )

    reloaded = DepartmentPilotWorkEnvelope.model_validate_json(envelope.model_dump_json())
    assert reloaded.schema_version == "aion.department_pilot.work_envelope.v1"
    assert reloaded.package.approval.approved_package_hash == reloaded.package.package_hash
    assert reloaded.task.pilot_id == "finance_pilot"
    assert reloaded.handback.status == "ready_for_boardroom"
    assert reloaded.receipts[0].artifact_ids == ["artifact-001"]


def test_hashes_are_deterministic_and_package_edits_invalidate_approval():
    first, _ = _approved_finance_package()
    second, _ = _approved_finance_package()
    assert first.package_hash == second.package_hash
    assert first.approval.approval_hash == second.approval.approval_hash

    changed = first.model_dump(mode="json")
    changed["objective"] = "A materially different objective"
    with pytest.raises(ValidationError, match="hash_mismatch"):
        BoardroomAssignmentPackage(**changed)


def test_live_tool_payload_cannot_change_after_exact_approval():
    package, provenance = _approved_finance_package()
    task = _completed_task(package, provenance)
    tool_call = propose_tool_call(
        tool_call_id="tool-call-live",
        task_id=task.task_id,
        department_id="finance",
        capability="gmail.send",
        tool_name="gmail.send",
        provider="google",
        tool_mode="approved_live_external",
        payload={"to": "owner@example.com", "subject": "Cash report"},
        rationale="Send the approved report.",
        external_side_effect=True,
        approval_required=True,
        proposed_at=NOW,
        proposed_by="finance_pilot",
    )
    changed = tool_call.model_dump(mode="json")
    changed["payload"]["to"] = "different@example.com"
    with pytest.raises(ValidationError, match="payload_hash_mismatch"):
        ProposedToolCall(**changed)


def test_invalid_task_state_transition_is_blocked():
    package, provenance = _approved_finance_package()
    task = create_task_from_package(
        package,
        action_id="finance-action-001",
        task_id="finance-task-state",
        pilot_id="finance_pilot",
        assigned_at=NOW,
        provenance=provenance,
    )
    with pytest.raises(ValueError, match="queued->completed"):
        transition_department_task(task, to_status="completed", occurred_at=NOW)


def test_existing_mission_queue_and_receipt_are_adapted_not_duplicated():
    package, _ = _approved_finance_package()
    legacy_item = create_department_queue_item(
        business_id="home-fixed",
        mission_id="mission-001",
        mission_run_id="run-001",
        department_id="finance",
        capability="cashflow.model",
        title="Prepare a 13-week cash forecast",
        task_type="boardroom_assignment",
    )
    task = adapt_legacy_department_queue_item(
        package=package,
        queue_item=legacy_item,
        assigned_at=NOW,
    )
    assert task.task_id == legacy_item["task_id"]
    assert task.provenance.source_system == "aion_mission_mode"
    assert task.provenance.correlation_id == "run-001"

    legacy_receipt = create_capability_receipt(
        mission_id="mission-001",
        mission_run_id="run-001",
        business_id="home-fixed",
        step_id=legacy_item["task_id"],
        tool_name="spreadsheet.create",
        provider="local",
        action_type="cashflow.model",
        requested_payload_hash=canonical_contract_hash({"weeks": 13}),
        executed_payload_hash=canonical_contract_hash({"weeks": 13}),
        before_state_hash=canonical_contract_hash({"forecast": None}),
        after_state_hash=canonical_contract_hash({"forecast": "created"}),
    )
    receipt = adapt_legacy_capability_receipt(
        task=task,
        legacy_receipt=legacy_receipt,
        receipt_id="canonical-receipt-001",
        completed_at=NOW,
    )
    assert receipt.legacy_receipt_hash == legacy_receipt["receipt_hash"]
    assert receipt.schema_version == "aion.department_pilot.execution_receipt.v1"


def test_hr_is_a_first_class_specialist_department_in_new_contracts():
    action = BoardroomAssignmentAction(
        action_id="hr-001",
        title="Review role accountability",
        objective="Map responsibility and capacity gaps.",
        department_id="hr",
        capability="workforce.role_map",
    )
    assert action.department_id == "hr"
