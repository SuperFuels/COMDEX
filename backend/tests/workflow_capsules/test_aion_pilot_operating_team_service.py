from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.modules.aion_business.runtime.pilot_operating_team_service import (
    PilotOperatingTeamService,
)
from backend.services.aion_mission_mode.department_execution_queue import (
    create_department_queue_item,
)


def service(tmp_path):
    return PilotOperatingTeamService(base_dir=tmp_path)


def service_with_workflow(tmp_path, *, node_count=2):
    graph = {
        "workflow_id": "workflow-lead-to-cash",
        "name": "Lead to cash",
        "nodes": [{"id": f"node-{index}"} for index in range(node_count)],
        "edges": [],
    }
    tree = {
        "folders": [{
            "id": "workflows",
            "type": "folder",
            "children": [{
                "id": graph["workflow_id"],
                "workflow_id": graph["workflow_id"],
                "type": "workflow",
                "name": graph["name"],
                "graph": graph,
            }],
        }],
    }
    return PilotOperatingTeamService(base_dir=tmp_path, workflow_cabinet_loader=lambda _workspace: tree)


def test_bootstrap_creates_isolated_department_capsules_and_vault_model_contract(tmp_path):
    runtime = service(tmp_path)
    result = runtime.bootstrap_workspace("acme", departments=["coo", "finance", "support"])
    assert result["model_selection"] == "vault_selected"
    assert {item["department_id"] for item in result["capsules"]} == {"coo", "finance", "support"}
    assert len({item["browser_profile_id"] for item in result["capsules"]}) == 3
    assert all(item["network_policy"] == "deny_unregistered_destinations" for item in result["capsules"])
    assert all(item["external_writes_require_exact_approval"] for item in result["capsules"])


def test_human_takeover_and_return_to_department_pilot_are_audited(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["finance"])
    takeover = runtime.transfer_control(
        "acme", "finance", control_state="human", controller_id="person:founder",
        reason="Complete bank two-factor authentication",
    )
    assert takeover["control_state"] == "human"
    returned = runtime.transfer_control(
        "acme", "finance", control_state="pilot", controller_id="department_pilot:finance",
        reason="Authentication complete",
    )
    assert returned["previous_controller_id"] == "person:founder"
    assert runtime.verify_audit("acme")["ok"] is True


def test_demonstration_redacts_secrets_and_requires_validation_before_publish(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["finance"])
    skill = runtime.create_demonstrated_skill(
        "acme",
        name="Prepare overdue invoice reminders",
        department_id="finance",
        outcome="Create review-ready reminders for overdue invoices",
        created_by="person:founder",
        observed_steps=[
            {"type": "click", "role": "button", "label": "Invoices"},
            {"type": "fill", "label": "Password", "password": "never-store-me"},
            {
                "type": "approval_checkpoint",
                "label": "Send reminders",
                "requires_approval": True,
                "safety": "approval_required",
            },
        ],
    )
    assert skill["status"] == "draft"
    assert skill["approval_boundaries"] == ["step_003"]
    assert "never-store-me" not in str(skill)
    with pytest.raises(ValueError, match="skill_cannot_publish"):
        runtime.validate_skill(
            "acme", skill["skill_id"], validated_by="person:founder",
            checks={"safe_inputs": True}, publish=True,
        )
    published = runtime.validate_skill(
        "acme",
        skill["skill_id"],
        validated_by="person:founder",
        checks={
            "safe_inputs": True,
            "selectors_resolved": True,
            "outputs_verified": True,
            "approval_stops_verified": True,
        },
        publish=True,
    )
    assert published["status"] == "published"


def test_taught_process_details_can_be_edited_and_process_can_be_archived(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["operations"])
    skill = runtime.create_demonstrated_skill(
        "acme",
        name="Original title",
        department_id="operations",
        outcome="Original description",
        created_by="person:founder",
        observed_steps=[{"type": "click", "label": "Continue", "selector": "#continue"}],
    )
    published = runtime.validate_skill(
        "acme",
        skill["skill_id"],
        validated_by="person:founder",
        checks={
            "safe_inputs": True,
            "selectors_resolved": True,
            "outputs_verified": True,
            "approval_stops_verified": True,
        },
        publish=True,
    )
    updated = runtime.update_demonstrated_skill(
        "acme",
        skill["skill_id"],
        name="Updated title",
        outcome="Updated description",
        updated_by="person:founder",
    )
    assert updated["name"] == "Updated title"
    assert updated["outcome"] == "Updated description"
    assert updated["steps"] == published["steps"]
    assert published["skill_hash"] in updated["accepted_skill_hashes"]
    node = runtime.workflow_skill_nodes("acme")["nodes"][0]
    assert node["label"] == "Updated title"
    assert node["description"] == "Updated description"
    queued = runtime.queue_workflow_skill_run(
        "acme",
        skill_id=skill["skill_id"],
        skill_hash=published["skill_hash"],
        workflow_id="existing-workflow",
        workflow_node_id="existing-node",
        inputs={},
        idempotency_key="existing-node:1",
        requested_by="person:founder",
    )
    assert queued["waiting"] is True

    archived = runtime.archive_demonstrated_skill(
        "acme", skill["skill_id"], deleted_by="person:founder",
    )
    assert archived["status"] == "archived"
    assert runtime.workspace("acme")["skills"] == []
    assert runtime.workspace("acme")["archived_skill_count"] == 1
    assert runtime.workflow_skill_nodes("acme")["count"] == 0
    assert runtime.verify_audit("acme")["ok"] is True


def test_saved_workflow_can_be_scheduled_or_event_triggered_as_a_routine(tmp_path):
    runtime = service_with_workflow(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["coo"])
    routine = runtime.create_routine(
        "acme",
        title="Lead handling autopilot",
        department_id="coo",
        owner_id="workflow_scheduler",
        workflow_id="workflow-lead-to-cash",
        schedule={"interval_minutes": 1, "interval_value": 1, "interval_unit": "minute"},
        input_source="saved_workflow:workflow-lead-to-cash",
        expected_result="Execute Lead to cash and produce governed receipts",
        access_contract={"mode": "vault_grants_only", "required_sources": ["crm"]},
        output_contract={"type": "spreadsheet_xlsx", "destination": "file_cabinet", "completion_receipt": True},
    )
    assert routine["workflow_target"]["node_count"] == 2
    assert routine["workflow_target"]["target_kind"] == "complete_workflow"
    assert routine["access_contract"]["mode"] == "vault_grants_only"
    assert routine["output_contract"]["type"] == "spreadsheet_xlsx"
    tested = runtime.test_routine(
        "acme",
        routine["routine_id"],
        tested_by="person:founder",
        checks={
            "current_inputs_selected": True,
            "output_format_valid": True,
            "audit_trail_complete": True,
            "approval_stop_verified": True,
            "failure_states_explicit": True,
        },
    )
    assert tested["test_state"] == "passed"
    enabled = runtime.set_routine_enabled(
        "acme", routine["routine_id"], enabled=True, changed_by="person:founder",
    )
    due = datetime.fromisoformat(enabled["next_run_at"])
    result = runtime.run_due_routines("acme", now=due)
    assert result["queued"][0]["status"] == "workflow_queued"
    assert result["queued"][0]["workflow_id"] == "workflow-lead-to-cash"
    assert result["queued"][0]["execution_policy"] == "governed_gateway_with_exact_external_write_approval"
    assert result["queued"][0]["access_contract"]["mode"] == "vault_grants_only"
    assert result["queued"][0]["output_contract"]["destination"] == "file_cabinet"

    event_routine = runtime.create_routine(
        "acme",
        title="New lead workflow",
        department_id="coo",
        owner_id="workflow_scheduler",
        workflow_id="workflow-lead-to-cash",
        event_trigger={"event_type": "sales.lead_received"},
        input_source="saved_workflow:workflow-lead-to-cash",
        expected_result="Execute Lead to cash and produce governed receipts",
    )
    runtime.test_routine(
        "acme", event_routine["routine_id"], tested_by="person:founder",
        checks={
            "current_inputs_selected": True,
            "output_format_valid": True,
            "audit_trail_complete": True,
            "approval_stop_verified": True,
            "failure_states_explicit": True,
        },
    )
    runtime.set_routine_enabled(
        "acme", event_routine["routine_id"], enabled=True, changed_by="person:founder",
    )
    dispatched = runtime.dispatch_event(
        "acme",
        event={"event_type": "sales.lead_received", "lead_id": "lead-1"},
        trigger_instance_id="lead-1",
    )
    assert dispatched["queued"][0]["status"] == "workflow_queued"


def test_autosaved_workflow_tab_snapshot_can_be_scheduled_before_cabinet_sync(tmp_path):
    runtime = PilotOperatingTeamService(base_dir=tmp_path, workflow_cabinet_loader=lambda _workspace: {"folders": []})
    runtime.bootstrap_workspace("acme", departments=["coo"])
    graph = {"workflow_id": "tab-workflow", "name": "One taught node", "nodes": [{"id": "taught-1"}], "edges": []}
    routine = runtime.create_routine(
        "acme",
        title="One-node autopilot",
        department_id="coo",
        owner_id="workflow_scheduler",
        workflow_id="tab-workflow",
        workflow_name="One taught node",
        workflow_graph=graph,
        schedule={"interval_minutes": 60},
        input_source="saved_workflow:tab-workflow",
        expected_result="Run the taught process",
    )
    assert routine["workflow_target"]["target_kind"] == "single_node_workflow"
    assert routine["workflow_target"]["graph"] == graph


def test_routine_requires_one_trigger_and_published_skill(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["support"])
    draft = runtime.create_demonstrated_skill(
        "acme",
        name="Summarize complaint queue",
        department_id="support",
        outcome="Prepare complaint summary",
        created_by="person:founder",
        observed_steps=[{"type": "click", "label": "Open tickets"}],
    )
    with pytest.raises(ValueError, match="published_skill"):
        runtime.create_routine(
            "acme", title="Daily complaints", department_id="support",
            owner_id="department_pilot:support", skill_id=draft["skill_id"],
            schedule={"time": "08:00", "timezone": "Europe/Madrid"},
            input_source="support.ticket_ledger", expected_result="Complaint summary",
        )


def test_routine_rejects_an_unregistered_output_contract(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["operations"])
    with pytest.raises(ValueError, match="unsupported_routine_output_type"):
        runtime.create_routine(
            "acme",
            title="Unsafe arbitrary output",
            department_id="operations",
            owner_id="department_pilot:operations",
            schedule={"interval_minutes": 60},
            input_source="vault_grants:operations",
            expected_result="Invent an output",
            access_contract={"mode": "anything_goes"},
            output_contract={"type": "arbitrary_executable"},
        )


def test_tested_event_routine_dispatches_once_to_a_department_mission(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["coo", "support"])
    routine = runtime.create_routine(
        "acme",
        title="Prepare new complaint brief",
        department_id="support",
        owner_id="department_pilot:support",
        event_trigger={"event_type": "support.complaint_opened", "match": {"severity": "high"}},
        input_source="support.case_ledger",
        expected_result="Prepare an evidence-backed complaint brief",
    )
    with pytest.raises(ValueError, match="cannot_enable_before_test"):
        runtime.set_routine_enabled("acme", routine["routine_id"], enabled=True, changed_by="person:founder")
    tested = runtime.test_routine(
        "acme",
        routine["routine_id"],
        tested_by="person:founder",
        checks={
            "current_inputs_selected": True,
            "output_format_valid": True,
            "audit_trail_complete": True,
            "approval_stop_verified": True,
            "failure_states_explicit": True,
        },
    )
    assert tested["test_state"] == "passed"
    runtime.set_routine_enabled("acme", routine["routine_id"], enabled=True, changed_by="person:founder")
    event = {"event_type": "support.complaint_opened", "severity": "high", "case_id": "case-1"}
    first = runtime.dispatch_event("acme", event=event, trigger_instance_id="case-1:opened")
    second = runtime.dispatch_event("acme", event=event, trigger_instance_id="case-1:opened")
    assert len(first["queued"]) == 1
    assert first["queued"][0]["status"] == "mission_queued"
    assert len(second["ignored"]) == 1
    assert runtime.workspace("acme")["missions"][-1]["assignments"][0]["department_id"] == "support"


def test_due_schedule_queues_a_mission_and_advances_next_run(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["coo", "finance"])
    routine = runtime.create_routine(
        "acme",
        title="Daily cash review",
        department_id="finance",
        owner_id="department_pilot:finance",
        schedule={"interval_minutes": 60, "timezone": "Europe/Madrid"},
        input_source="finance.canonical_ledger",
        expected_result="Prepare the current cash and overdue debt briefing",
    )
    runtime.test_routine(
        "acme",
        routine["routine_id"],
        tested_by="person:founder",
        checks={
            "current_inputs_selected": True,
            "output_format_valid": True,
            "audit_trail_complete": True,
            "approval_stop_verified": True,
            "failure_states_explicit": True,
        },
    )
    enabled = runtime.set_routine_enabled(
        "acme", routine["routine_id"], enabled=True, changed_by="person:founder"
    )
    due = datetime.fromisoformat(enabled["next_run_at"]) + timedelta(seconds=1)
    result = runtime.run_due_routines("acme", now=due.astimezone(UTC))
    assert len(result["queued"]) == 1
    updated = next(
        item for item in runtime.workspace("acme")["routines"]
        if item["routine_id"] == routine["routine_id"]
    )
    assert datetime.fromisoformat(updated["next_run_at"]) > due


def test_coo_mission_can_delegate_redirect_pause_and_resume(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["coo", "finance", "support"])
    mission = runtime.create_mission(
        "acme",
        outcome="Improve cash collection without contacting disputed accounts",
        requested_by="person:founder",
        constraints=["No customer contact before exact approval"],
    )
    assignment = runtime.delegate(
        "acme", mission["mission_id"], department_id="finance",
        outcome="Identify collectible overdue invoices", delegated_by="coo",
    )
    assert assignment["state"] == "queued"
    redirected = runtime.control_mission(
        "acme", mission["mission_id"], command="redirect", actor_id="person:founder",
        instruction="Exclude every account with an unresolved Support complaint.",
    )
    assert redirected["state"] == "running"
    assert redirected["timeline"][-1]["instruction"].startswith("Exclude")
    assert runtime.control_mission(
        "acme", mission["mission_id"], command="pause", actor_id="person:founder"
    )["state"] == "paused"
    assert runtime.control_mission(
        "acme", mission["mission_id"], command="resume", actor_id="person:founder"
    )["state"] == "running"


def test_launch_mission_routes_dispatches_and_binds_gateway_to_department_computer(tmp_path):
    class Planner:
        def run(self, **kwargs):
            item = create_department_queue_item(
                business_id=kwargs["workspace_id"],
                mission_id="planner-mission",
                mission_run_id="run-1",
                department_id="finance",
                capability="invoice.collection.prepare",
                title="Prepare overdue invoice chase list",
                task_type="coo_delegation",
                objective="Identify collectible overdue invoices with evidence",
            )
            return {
                "status": "proposal_ready",
                "model_selection": {
                    "provider": "local_model",
                    "model": "user-selected-model",
                    "selection_status": "selectable",
                },
                "proposal": {
                    "answer": "Finance should prepare the evidence-backed chase list.",
                    "department_tasks": [{
                        "department": "finance",
                        "capability": "invoice.collection.prepare",
                    }],
                },
                "delegation_queue": {"items": [item]},
            }

    runtime = PilotOperatingTeamService(base_dir=tmp_path, coo_mission_service=Planner())
    runtime.bootstrap_workspace("acme", departments=["coo", "finance"])
    mission = runtime.launch_mission(
        "acme",
        outcome="Prepare an overdue invoice chase list",
        requested_by="person:founder",
    )
    assert mission["state"] == "running"
    assert mission["planner_status"] == "proposal_ready"
    assert mission["model_selection"]["model"] == "user-selected-model"
    assert mission["assignments"][0]["department_id"] == "finance"
    assert mission["assignments"][0]["gateway"]["adapted"] is True
    assert mission["external_side_effect_executed"] is False
    finance = next(item for item in runtime.workspace("acme")["capsules"] if item["department_id"] == "finance")
    assert finance["active_mission_id"] == mission["mission_id"]
    assert finance["current_objective"] == "Identify collectible overdue invoices with evidence"
    task_file = tmp_path / "acme" / "pilot" / "operating_team" / "department_workspaces" / "finance" / "tasks" / "finance_invoice_collection_prepare_00.json"
    assert task_file.exists()


def test_completion_pack_separates_evidence_actions_and_approvals(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["coo"])
    mission = runtime.create_mission("acme", outcome="Morning briefing", requested_by="person:founder")
    pack = runtime.completion_pack(
        "acme",
        mission["mission_id"],
        facts=[{"claim": "Three invoices are overdue", "source": "finance.invoice_ledger"}],
        assumptions=["Disputed invoices should remain excluded"],
        actions_completed=[{"action": "prepared_reminders", "count": 3}],
        approvals_waiting=[{"action": "send", "count": 3}],
        unresolved_questions=["Should the reminders mention late fees?"],
        artifacts=[{"kind": "draft_bundle", "id": "bundle-1"}],
        prepared_by="coo",
    )
    assert pack["facts"][0]["source"] == "finance.invoice_ledger"
    assert pack["approvals_waiting"][0]["action"] == "send"
    assert pack["pack_hash"]


def test_memory_and_action_gateway_preserve_authority_boundaries(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["finance"])
    with pytest.raises(PermissionError, match="requires_source_authority"):
        runtime.remember(
            "acme", department_id="finance", scope="authoritative_fact",
            key="cash", value=100, actor_id="model:selected",
        )
    fact = runtime.remember(
        "acme", department_id="finance", scope="authoritative_fact",
        key="cash", value=100, actor_id="finance_ledger",
        authority_source="finance.canonical_ledger",
    )
    assert fact["model_may_mutate"] is False
    denied = runtime.preflight_action(
        "acme",
        department_id="finance",
        initiator={"kind": "routine", "id": "daily-cash"},
        action_type="send",
        target={"customer_id": "customer-1"},
        payload={"body": "Reminder", "api_key": "do-not-store"},
        registered_capability=False,
    )
    assert denied["allowed"] is False
    assert denied["approval_required"] is True
    assert denied["payload"]["api_key"] == "[REDACTED]"


def test_worker_nodes_and_templates_never_bypass_approvals_or_copy_credentials(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["finance"])
    node = runtime.register_worker_node(
        "acme", node_id="office-mac", label="Office Mac",
        registered_by="person:founder", capabilities=["browser.read", "files.prepare"],
    )
    assert node["ownership"] == "user_owned"
    assert node["can_bypass_approvals"] is False
    heartbeat = runtime.heartbeat_worker_node(
        "acme", "office-mac", reported_by="worker:office-mac",
        observed_capabilities=["browser.read"],
    )
    assert heartbeat["status"] == "online"
    with pytest.raises(PermissionError, match="self_grant"):
        runtime.heartbeat_worker_node(
            "acme", "office-mac", reported_by="worker:office-mac",
            observed_capabilities=["browser.read", "email.send"],
        )
    routine = runtime.create_routine(
        "acme", title="Daily cash review", department_id="finance",
        owner_id="department_pilot:finance", schedule={"interval_minutes": 1440},
        input_source="finance.canonical_ledger", expected_result="Prepare cash briefing",
    )
    template = runtime.save_template(
        "acme", name="Daily cash review", template_type="routine",
        source_id=routine["routine_id"], created_by="person:founder",
    )
    assert template["copies_credentials"] is False
    assert template["source_status"] == "resolved"
    copy = runtime.instantiate_template(
        "acme", template["template_id"], created_by="person:founder",
        name="Weekday cash review",
    )
    assert copy["title"] == "Weekday cash review"
    assert copy["enabled"] is False
    assert copy["test_state"] == "not_tested"
    with pytest.raises(PermissionError, match="cannot_include_sensitive"):
        runtime.save_template(
            "acme", name="Unsafe", template_type="pilot", source_id="pilot-1",
            created_by="person:founder", include_sensitive_configuration=True,
        )


def test_published_demonstration_becomes_idempotent_workflow_node_and_waits_for_evidence(tmp_path):
    runtime = service(tmp_path)
    runtime.bootstrap_workspace("acme", departments=["sales"])
    skill = runtime.create_demonstrated_skill(
        "acme",
        name="Enter website lead into CRM",
        department_id="sales",
        outcome="Create a CRM lead from mapped workflow input",
        created_by="person:founder",
        observed_steps=[{"type": "click", "label": "New contact", "selector": "#new-contact"}],
    )
    assert runtime.workflow_skill_nodes("acme")["count"] == 0
    published = runtime.validate_skill(
        "acme",
        skill["skill_id"],
        validated_by="person:founder",
        checks={
            "safe_inputs": True,
            "selectors_resolved": True,
            "outputs_verified": True,
            "approval_stops_verified": True,
        },
        publish=True,
    )
    node = runtime.workflow_skill_nodes("acme")["nodes"][0]
    assert node["skill_id"] == skill["skill_id"]
    assert node["kind"] == "capability"
    assert node["skill_hash"] == published["skill_hash"]

    queued = runtime.queue_workflow_skill_run(
        "acme",
        skill_id=skill["skill_id"],
        skill_hash=published["skill_hash"],
        workflow_id="lead-to-cash",
        workflow_node_id="crm-entry",
        inputs={"email": "lead@example.com"},
        idempotency_key="lead-123:crm-entry",
        requested_by="person:founder",
    )
    assert queued["waiting"] is True
    duplicate = runtime.queue_workflow_skill_run(
        "acme",
        skill_id=skill["skill_id"],
        skill_hash=published["skill_hash"],
        workflow_id="lead-to-cash",
        workflow_node_id="crm-entry",
        inputs={"email": "lead@example.com"},
        idempotency_key="lead-123:crm-entry",
        requested_by="person:founder",
    )
    assert duplicate["workflow_skill_run_id"] == queued["workflow_skill_run_id"]
    assert len(runtime.workspace("acme")["skill_runs"]) == 1

    completed = runtime.complete_workflow_skill_run(
        "acme",
        queued["workflow_skill_run_id"],
        completed_by="department_pilot:sales",
        succeeded=True,
        output={"crm_contact_id": "contact-123"},
        evidence=[{"kind": "target_state", "contact_id": "contact-123"}],
    )
    assert completed["state"] == "completed"
    resumed = runtime.queue_workflow_skill_run(
        "acme",
        skill_id=skill["skill_id"],
        skill_hash=published["skill_hash"],
        workflow_id="lead-to-cash",
        workflow_node_id="crm-entry",
        inputs={"email": "lead@example.com"},
        idempotency_key="lead-123:crm-entry",
        requested_by="person:founder",
    )
    assert resumed["verified"] is True
    assert resumed["output"]["crm_contact_id"] == "contact-123"
