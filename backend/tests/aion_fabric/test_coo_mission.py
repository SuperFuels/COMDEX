from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from backend.modules.pilot_unified.workspace_gateway import AionBoardroomWorkspaceProvider
from backend.services.aion_mission_mode.coo_mission import CooMissionService


def connected_service(request_kind_answer: str = "Grounded COO answer") -> CooMissionService:
    return CooMissionService(
        public_provider_loader=lambda: {"providers": [
            {"id": "openai", "connected": True, "model": "test-model"},
        ]},
        local_model_loader=lambda: {"models": []},
        model_invoker=lambda provider, prompt: {
            "content": json.dumps({
                "answer": request_kind_answer,
                "department_consultations": [{
                    "department": "operations", "finding": "One queued job", "source_ids": ["operations-ledger"],
                }],
                "sources": ["operations-ledger"], "draft": None,
                "action_proposal": {"action_type": "send_message", "proposed_payload": {"to": "customer", "body": "Draft"}},
            })
        },
    )


def facts(department: str) -> dict:
    return {"retrieval_state": "retrieved", "source_ids": [f"{department}-ledger"], "data": {"count": 1}}


def test_coo_prepares_bounded_cross_business_fact_pack_with_sources():
    mission = connected_service().prepare(workspace_id="home-fixed", question="What needs attention?", fact_loader=facts)
    assert set(mission["verified_business_facts"]) == {"finance", "sales", "marketing", "operations", "support", "people", "products_services"}
    assert mission["verified_business_facts"]["support"]["source_ids"] == ["support-ledger"]
    assert mission["external_writes_allowed"] is False


def test_coo_fetches_only_departments_relevant_to_a_factual_question():
    called = []
    mission = connected_service().prepare(
        workspace_id="home-fixed", question="Have we made any sales today?",
        fact_loader=lambda department: called.append(department) or facts(department),
    )
    assert called == ["finance", "sales", "operations"]
    assert mission["verified_business_facts"]["support"]["retrieval_state"] == "not_requested"


def test_coo_capability_selection_understands_people_support_and_meeting_language():
    service = connected_service()
    assert service._relevant_departments("How many staff are off on holiday today?") == {"people", "operations"}
    assert service._relevant_departments("How many tickets are open?") == {"support", "operations"}
    assert service._relevant_departments("Brief me on what was discussed in today's meeting") == {"operations"}


def test_coo_uses_connected_vault_selection_and_validates_generic_proposal():
    result = connected_service().run(
        workspace_id="home-fixed", question="What should I focus on?", workspace_state={}, fact_loader=facts,
    )
    assert result["status"] == "proposal_ready"
    assert result["model_selection"]["provider"] == "openai"
    assert result["proposal"]["answer"] == "Grounded COO answer"
    assert result["proposal"]["model_may_execute"] is False


def test_coo_rejects_non_selectable_explicit_local_model():
    service = CooMissionService(
        public_provider_loader=lambda: {"providers": [{"id": "openai", "connected": True}]},
        local_model_loader=lambda: {"models": [{
            "model_id": "qwen-q2", "selection_status": "visible_not_selectable", "reason": "acceptance_failed",
        }]},
    )
    selection = service.resolve_model({"coo_model_selection": {
        "provider": "local_model", "model": "qwen-q2", "source": "local_model_vault",
    }})
    assert selection["status"] == "unavailable"
    assert selection["reason"] == "acceptance_failed"


def test_coo_local_selection_projects_vault_runtime_adapter_without_model_name_coupling():
    service = CooMissionService(
        public_provider_loader=lambda: {"providers": []},
        local_model_loader=lambda: {"models": [{
            "model_id": "owner-selected-local-model", "selection_status": "selectable",
            "release_status": "accepted", "installations": [{
                "selectable": True, "model_sha256": "a" * 64,
                "runtime_profile": {
                    "endpoint": "http://127.0.0.1:9911",
                    "finance_arithmetic": "verified_tessaris_tools_required",
                    "max_output_tokens": 256,
                },
            }],
            "runtime_profile": {"adapter": "openai_compatible_bounded_chat.v1"},
        }]},
    )
    selection = service.resolve_model({"coo_model_selection": {
        "provider": "local_model", "model": "owner-selected-local-model",
        "source": "local_model_vault",
    }})
    assert selection["status"] == "selected"
    assert selection["model"] == "owner-selected-local-model"
    assert selection["runtime_adapter"] == "openai_compatible_bounded_chat.v1"


def test_coo_creates_source_required_research_job_without_claiming_research_ran():
    result = connected_service().run(
        workspace_id="home-fixed", question="Research local competitors and cost per click",
        workspace_state={}, fact_loader=facts,
    )
    assert result["mission"]["research_policy"] == "source_required"
    assert result["research_job"]["status"] == "prepared"
    assert result["research_job"]["source_requirements"] == "independent_sources_required"
    assert result["external_writes_performed"] is False


def test_coo_external_action_stays_in_exact_payload_approval_state():
    result = connected_service().run(
        workspace_id="home-fixed", question="Send the customer an update",
        workspace_state={}, fact_loader=facts,
    )
    approval = result["required_approval"]
    assert approval["approval_state"] == "waiting_exact_payload_approval"
    assert approval["expected_payload_hash"].startswith("sha256:")
    assert approval["execution_allowed"] is False
    assert approval["external_side_effect_executed"] is False


def test_coo_validates_model_selected_department_tasks_and_builds_guarded_queue():
    service = CooMissionService(
        public_provider_loader=lambda: {"providers": [{"id": "openai", "connected": True}]},
        local_model_loader=lambda: {"models": []},
        model_invoker=lambda provider, prompt: {"content": json.dumps({
            "answer": "Finance will prepare collections and reminders will wait for approval.",
            "department_consultations": [], "sources": ["finance-ledger"], "draft": None,
            "action_proposal": None,
            "department_tasks": [
                {"department": "finance", "capability": "invoice.collection.prepare",
                 "title": "Prepare invoice collections", "objective": "Prepare every outstanding invoice for chasing today."},
                {"department": "finance", "capability": "invoice.reminder.send",
                 "title": "Send invoice reminders", "objective": "Send the approved reminders today."},
            ],
        })},
    )
    result = service.run(
        workspace_id="home-fixed", question="Make sure all outstanding invoices are chased today",
        workspace_state={}, fact_loader=facts,
    )
    assert result["status"] == "proposal_ready"
    assert [item["status"] for item in result["delegation_queue"]["items"]] == ["ready", "waiting_approval"]
    assert result["proposal"]["answer"].startswith("Prepared 2 governed task(s) for Finance")
    assert result["proposal"]["answer"].endswith("No live external action has run.")
    assert result["required_approval"]["action_type"] == "department_live_actions"
    assert result["required_approval"]["proposed_payload"]["department_tasks"][0]["capability"] == "invoice.reminder.send"


def test_coo_rejects_model_task_outside_registered_department_capabilities():
    service = connected_service()
    try:
        service._validate_proposal({
            "answer": "Attempted route", "department_tasks": [{
                "department": "finance", "capability": "bank.transfer.execute",
            }],
        })
    except ValueError as exc:
        assert "unsupported_department_task" in str(exc)
    else:
        raise AssertionError("unregistered capability must be rejected")


def test_local_model_prompt_compacts_large_department_records():
    service = connected_service()
    mission = service.prepare(
        workspace_id="home-fixed", question="How many support tickets are open?",
        department_facts={
            "support": {"source_ids": ["support-ledger"], "data": {
                "cases": [{"id": index, "content": "x" * 2_000} for index in range(80)],
            }},
            "operations": facts("operations"),
        },
    )
    prompt = service._prompt(mission)
    assert len(prompt) < 5_000
    assert prompt.count('"content"') <= 4


def test_coo_binds_only_verified_fact_sources_when_model_omits_or_invents_them():
    service = connected_service()
    service.model_invoker = lambda provider, prompt: {"content": json.dumps({
        "answer": "Grounded", "department_consultations": [], "sources": ["invented-source"],
        "draft": None, "action_proposal": None, "department_tasks": [],
    })}
    result = service.run(
        workspace_id="home-fixed", question="How many support tickets are open?",
        workspace_state={}, fact_loader=facts,
    )
    assert result["proposal"]["sources"] == ["operations-ledger", "support-ledger"]


class Containers:
    def __init__(self):
        self.state = {"operational_runtime_summary": {}}

    def load_optional_dict(self, workspace_ref, kind):
        return self.state.get(kind, {})

    def save_dict(self, workspace_ref, kind, value):
        self.state[kind] = value


class Departments:
    def list_for_workspace(self, workspace_ref):
        return []


class Workspaces:
    def list_ids(self):
        return ["home-fixed"]


class FakeMission:
    def __init__(self, *, research=False):
        self.research = research

    def run(self, **kwargs):
        receipt = {
            "schema_version": "aion.coo.mission_receipt.v1", "status": "proposal_ready",
            "mission": {"mission_id": "mission-1"},
            "model_selection": {"provider": "openai", "model": "test-model"},
            "proposal": {"answer": "Prioritise the queued delivery.", "sources": ["operations-ledger"]},
            "external_writes_performed": False, "approval_gated": True,
        }
        if self.research:
            receipt["research_job"] = {"job_id": "research-1", "status": "prepared"}
        return receipt


class FakeInvoices:
    def list_invoices(self, workspace_ref):
        return [{
            "invoice_number": "INV-001", "currency": "EUR", "amount_due": 242.0,
            "due_date": "2026-08-23", "status": "verified_in_xero",
        }]


def test_coo_answers_outstanding_invoices_from_ledger_without_calling_model():
    containers = Containers()
    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), containers, Departments(), finance_sales_service=FakeInvoices(),
        coo_mission_service=FakeMission(),
    )

    response = adapter.conversation_turn(
        "home-fixed", "operations", "Do we have any outstanding invoices?", persona_id="persona-founder",
    )

    assert "1 outstanding invoice(s), totalling €242.00" in response["turn"]["content"]
    assert "1 of them are overdue" in response["turn"]["content"]
    assert response["provider"]["provider"] == "coo_invoice_ledger"
    assert "mission_receipt" not in response


def test_coo_invoice_action_routes_to_mission_and_persists_department_queue():
    class ActionMission(FakeMission):
        def run(self, **kwargs):
            result = super().run(**kwargs)
            result["proposal"]["answer"] = "Prepared Finance collections work."
            result["delegation_queue"] = {
                "schema_version": "aion.coo.delegation_queue.v1", "mission_id": "mission-1",
                "status": "prepared", "items": [{"department_id": "finance", "status": "ready"}],
                "ready_count": 1, "waiting_approval_count": 0, "external_side_effect_executed": False,
            }
            return result

    containers = Containers()
    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), containers, Departments(), finance_sales_service=FakeInvoices(),
        coo_mission_service=ActionMission(),
    )
    response = adapter.conversation_turn(
        "home-fixed", "operations", "Make sure all outstanding invoices are chased today",
        persona_id="persona-founder",
    )
    assert response["turn"]["content"] == "Prepared Finance collections work."
    assert response["delegation_queue"]["items"][0]["department_id"] == "finance"
    assert containers.state["operational_runtime_summary"]["coo_delegation_queues"][-1]["mission_id"] == "mission-1"


def test_coo_answers_tomorrows_appointments_from_private_calendar_without_model():
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    event_start = datetime.combine(tomorrow, datetime.min.time(), timezone.utc).replace(hour=9)
    containers = Containers()
    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), containers, Departments(), coo_mission_service=FakeMission(),
        calendar_snapshot_loader=lambda persona_id: {
            "connected": True, "time_zone": "UTC",
            "events": [{"start": event_start.isoformat(), "title": "Supplier review", "status": "confirmed"}],
        },
    )

    response = adapter.conversation_turn(
        "home-fixed", "operations", "Do I have any appointments tomorrow?", persona_id="persona-founder",
    )

    assert "1 appointment(s)" in response["turn"]["content"]
    assert "09:00 — Supplier review" in response["turn"]["content"]
    assert response["provider"]["provider"] == "coo_private_calendar"


def test_coo_does_not_claim_an_empty_calendar_when_none_is_connected():
    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), Containers(), Departments(), coo_mission_service=FakeMission(),
    )

    response = adapter.conversation_turn(
        "home-fixed", "operations", "Do I have any appointments tomorrow?", persona_id="desktop_user",
    )

    assert "no private calendar is connected" in response["turn"]["content"]
    assert response["reliability"] == "calendar_unavailable"


def test_retrospective_meeting_question_uses_boardroom_facts_not_personal_calendar():
    class MeetingContainers(Containers):
        def load_optional_dict(self, workspace_ref, kind):
            if kind == "boardroom_snapshot":
                return {"boardroom": {"runtime": {
                    "meeting_history": [{
                        "session_id": "today", "session_type": "daily_review", "status": "published",
                        "published_at": datetime.now(timezone.utc).isoformat(),
                        "summary": "Reviewed support capacity and agreed today's delivery plan.",
                    }],
                    "department_actions": [{
                        "action_id": "support-1", "title": "Clear urgent cases", "department_id": "support",
                        "status": "delegated", "due_at": datetime.now(timezone.utc).date().isoformat(),
                    }],
                }}}
            return super().load_optional_dict(workspace_ref, kind)

    class CapturingMission(FakeMission):
        def run(self, **kwargs):
            operations = kwargs["fact_loader"]("operations")["data"]
            assert operations["meeting_history"][0]["summary"].startswith("Reviewed support capacity")
            assert operations["department_actions"][0]["title"] == "Clear urgent cases"
            return super().run(**kwargs)

    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), MeetingContainers(), Departments(), coo_mission_service=CapturingMission(),
        calendar_snapshot_loader=lambda persona_id: (_ for _ in ()).throw(AssertionError("personal calendar must not be read")),
    )

    response = adapter.conversation_turn(
        "home-fixed", "operations", "From today's meeting give me a brief overview of what was discussed and today's plan",
        persona_id="persona-founder",
    )
    assert response["turn"]["content"] == "Prioritise the queued delivery."


def test_people_projection_exposes_operational_availability_without_sensitive_hr_fields():
    today = datetime.now(timezone.utc).date().isoformat()

    class PeopleAuthority:
        def get(self, workspace_ref):
            return {
                "departments": [], "roles": [], "assets": [],
                "people": [{"id": "person-1", "name": "Alex", "status": "active"}],
                "people_operations": {"leave_requests": [{
                    "id": "leave-1", "person_id": "person-1", "status": "approved",
                    "start_date": today, "end_date": today, "private_reason": "must not project",
                }]},
            }

    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), Containers(), Departments(), organization_authority_service=PeopleAuthority(),
    )
    data = adapter._mobile_people_directory("home-fixed")
    assert data["people_availability"]["off_today_count"] == 1
    assert data["people_availability"]["off_today"][0]["person_name"] == "Alex"
    assert "private_reason" not in data["people_availability"]["leave_records"][0]


def test_coo_provider_persists_receipt_and_shared_history_in_sequence():
    containers = Containers()
    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), containers, Departments(), coo_mission_service=FakeMission(),
    )
    response = adapter.conversation_turn(
        "home-fixed", "operations", "What should I do next?", persona_id="persona-founder",
    )
    assert response["turn"]["content"] == "Prioritise the queued delivery."
    turns = response["history"]["turns"]
    assert [turn["sequence"] for turn in turns] == [0, 1]
    assert [turn["role"] for turn in turns] == ["user", "assistant"]
    assert turns[1]["mission_receipt"]["mission"]["mission_id"] == "mission-1"
    assert containers.state["operational_runtime_summary"]["coo_mission_receipts"][-1]["status"] == "proposal_ready"


def test_explicit_coo_people_delegation_bypasses_unavailable_model_and_separates_streams():
    class UnavailableMission(FakeMission):
        def resolve_model(self, state):
            return {"status": "unavailable", "reason": "rate_limited"}

        def run(self, **kwargs):
            raise AssertionError("explicit delegation must not call the COO model")

    class PeopleAuthority:
        def __init__(self):
            self.model = {
                "workspace_id": "home-fixed", "revision": 1,
                "people": [{"id": "persona-founder", "name": "Founder", "status": "active",
                            "employment_type": "owner", "role_ids": ["role.owner_director"]}],
                "departments": [],
                "people_operations": {"leave_requests": [], "appraisals": [], "escalations": []},
            }

        def get(self, workspace_ref):
            return deepcopy(self.model)

        def save(self, workspace_ref, payload, *, expected_revision=None, changed_by="current_user"):
            self.model = deepcopy(payload)
            self.model["revision"] = expected_revision + 1
            return deepcopy(self.model)

        def access_decision(self, *args, **kwargs):
            return {"allowed": True}

    containers = Containers()
    authority = PeopleAuthority()
    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), containers, Departments(), organization_authority_service=authority,
        coo_mission_service=UnavailableMission(),
    )
    response = adapter.conversation_turn(
        "home-fixed", "operations",
        "speak to people and notify them to create a new employee Barry Jenkins",
        persona_id="persona-founder",
    )

    assert "I delegated this to the People Pilot" in response["turn"]["content"]
    assert authority.model["people"][-1]["name"] == "Barry Jenkins"
    direct = containers.state["operational_runtime_summary"]["shared_conversations"]["turns"]
    assert {item["department_id"] for item in direct} == {"operations"}
    executive = containers.state["operational_runtime_summary"]["executive_channel_conversations"]["turns"]
    assert [item["message_type"] for item in executive] == [
        "delegated_people_action", "delegated_people_response",
    ]


def test_coo_verifies_people_record_without_calling_a_language_model():
    class NoModelMission(FakeMission):
        def run(self, **kwargs):
            raise AssertionError("an authoritative People lookup must not call a model")

    class PeopleAuthority:
        def get(self, workspace_ref):
            return {
                "people": [
                    {"id": "person.kevin", "name": "Kevin Robinson", "status": "active"},
                    {"id": "person.peter", "name": "Peter Rabbit", "status": "active",
                     "employment_type": "self_employed", "position_title": "Roofer",
                     "manager_id": "person.kevin", "department_ids": []},
                ],
                "departments": [],
            }

    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), Containers(), Departments(),
        organization_authority_service=PeopleAuthority(),
        coo_mission_service=NoModelMission(),
    )
    response = adapter.conversation_turn(
        "home-fixed", "operations",
        "check that Peter Rabbit was added as a self employed person",
        persona_id="persona-founder",
    )

    assert "Peter Rabbit is recorded" in response["turn"]["content"]
    assert "relationship: self employed" in response["turn"]["content"]
    assert "job title: Roofer" in response["turn"]["content"]
    assert "reports to: Kevin Robinson" in response["turn"]["content"]
    assert response["provider"]["provider"] == "coo_people_directory"


def test_coo_provider_persists_prepared_research_job():
    containers = Containers()
    adapter = AionBoardroomWorkspaceProvider(
        Workspaces(), containers, Departments(), coo_mission_service=FakeMission(research=True),
    )
    adapter.conversation_turn(
        "home-fixed", "operations", "Research local competitors", persona_id="persona-founder",
    )
    jobs = containers.state["operational_runtime_summary"]["coo_research_jobs"]
    assert jobs == [{"job_id": "research-1", "status": "prepared"}]
