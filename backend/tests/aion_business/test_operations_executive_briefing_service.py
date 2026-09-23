from __future__ import annotations

from copy import deepcopy

from backend.modules.aion_business.runtime.operations_executive_briefing_service import (
    OperationsExecutiveBriefingService,
)


class MemoryRepository:
    def __init__(self) -> None:
        self.runtime = {"workspace_id": "home-fixed", "kind": "operational_runtime_summary"}

    def load_optional_dict(self, workspace_id: str, kind: str):
        assert workspace_id == "home-fixed"
        assert kind == "operational_runtime_summary"
        return deepcopy(self.runtime)

    def save_dict(self, workspace_id: str, kind: str, payload: dict):
        assert workspace_id == "home-fixed"
        assert kind == "operational_runtime_summary"
        self.runtime = deepcopy(payload)
        return "memory"


class FakeModels:
    def resolve_model(self, state):
        selection = state.get("coo_model_selection") or {}
        return {
            "status": "selected", "provider": selection.get("provider", "local_model"),
            "model": selection.get("model", "vault-primary"), "source": "test_vault",
            "release_status": "accepted",
        }

    def _invoke(self, selection, prompt):
        if selection.get("model") == "vault-critic":
            return {"content": '{"departments":{"sales":{"challenge":"Check conversion evidence","decision_needed":"Confirm target"}},"executive_risks":["Pipeline and cash need alignment"]}'}
        return {"content": '{"summary":"Evidence reviewed; no execution claimed.","yesterday_results":["Recorded result"],"today_plan":["Review the queue"],"outstanding":["One recorded task"],"risks":[],"target_variance":"On evidence supplied","decisions_needed":[],"actions":["Prepare the next internal step"]}'}


class FakeProvider:
    def __init__(self) -> None:
        self.containers = MemoryRepository()
        self.coo_missions = FakeModels()
        self.organization_authority = FakeAuthority()

    def _coo_department_fact(self, workspace_id, department, *, persona_id):
        return {"retrieval_state": "retrieved", "source_ids": [f"{department}.ledger"],
                "data": {"department": department, "recorded": 1}}

    def custom_departments(self, workspace_id):
        return [{
            "id": "legal", "name": "Legal", "pilot_title": "Legal & Compliance Director",
            "mandate": "Protect legal compliance using authorised evidence.", "core": False,
        }]

    def read_surface(self, workspace_id, surface, *, persona_id):
        assert surface == "briefings"
        return {"data": {"meeting_history": [{"title": "Board priorities", "status": "published"}],
                         "department_actions": [{"department": "sales", "title": "Grow qualified pipeline"}],
                         "pulse": {"status": "measured"}}}


class FakeAuthority:
    def __init__(self) -> None:
        self.model = {
            "workspace_id": "home-fixed", "revision": 1,
            "people": [{"id": "founder", "name": "Founder", "status": "active",
                        "employment_type": "owner", "role_ids": ["role.owner_director"]}],
            "departments": [],
            "people_operations": {"leave_requests": [], "appraisals": [], "escalations": []},
        }

    def get(self, workspace_id):
        return deepcopy(self.model)

    def save(self, workspace_id, payload, *, expected_revision=None, changed_by="current_user"):
        assert expected_revision == self.model["revision"]
        self.model = deepcopy(payload)
        self.model["revision"] = expected_revision + 1
        return deepcopy(self.model)

    def access_decision(self, *args, **kwargs):
        return {"allowed": True}


def test_morning_briefing_publishes_real_and_custom_pilot_minutes_and_deduplicates():
    provider = FakeProvider()
    service = OperationsExecutiveBriefingService(provider)
    result = service.run_morning_briefing("home-fixed", person_id="founder")
    assert result["briefing"]["status"] == "minutes_published"
    assert result["briefing"]["reasoning_mode"] == "single_model_role_separated"
    turns = provider.containers.runtime["executive_channel_conversations"]["turns"]
    assert len(turns) == 7
    assert {item["department_id"] for item in turns} == {"sales", "marketing", "finance", "support", "people", "legal", "operations"}
    assert all(item["message_type"] == "morning_minutes" for item in turns if item["department_id"] != "operations")
    assert turns[-1]["message_type"] == "executive_briefing_summary"
    assert all(item["record_hash"] for item in turns)
    again = service.run_morning_briefing("home-fixed", person_id="founder")
    assert again["deduplicated"] is True
    assert len(provider.containers.runtime["executive_channel_conversations"]["turns"]) == 7


def test_channel_turn_records_coo_instruction_and_department_answer():
    provider = FakeProvider()
    service = OperationsExecutiveBriefingService(provider)
    result = service.channel_turn("home-fixed", "legal", "Check compliance risk", person_id="founder")
    assert result["history"]["department_id"] == "legal"
    assert [item["message_type"] for item in result["history"]["turns"]] == ["coo_instruction", "department_update"]
    assert result["response"]["sender"] == "Legal & Compliance Director Pilot"
    assert result["response"]["external_writes_performed"] is False


def test_people_delegation_executes_internal_action_in_separate_executive_stream():
    provider = FakeProvider()
    provider.containers.runtime["shared_conversations"] = {
        "schema_version": "workspace_conversation_v1",
        "turns": [{"id": "direct-1", "sequence": 0, "department_id": "people",
                   "role": "user", "sender": "You", "content": "Direct private People chat"}],
    }
    service = OperationsExecutiveBriefingService(provider)
    result = service.delegate_people_action(
        "home-fixed", "speak to people and notify them to create a new employee Barry Jenkins",
        person_id="founder",
    )

    assert result["handled"] is True
    assert result["status"] == "completed"
    assert provider.organization_authority.model["people"][-1]["name"] == "Barry Jenkins"
    executive = provider.containers.runtime["executive_channel_conversations"]["turns"]
    assert [item["message_type"] for item in executive] == [
        "delegated_people_action", "delegated_people_response",
    ]
    assert all(item["content"] != "Direct private People chat" for item in result["history"]["turns"])
    assert provider.containers.runtime["shared_conversations"]["turns"][0]["content"] == "Direct private People chat"


def test_direct_department_turn_uses_role_evidence_and_vault_model_without_separate_persistence():
    provider = FakeProvider()
    service = OperationsExecutiveBriefingService(provider)
    result = service.direct_department_turn(
        "home-fixed", "people", "Who is available today?", person_id="founder",
    )
    assert result["department_id"] == "people"
    assert result["role"]["title"] == "People Director"
    assert result["position"]["summary"] == "Evidence reviewed; no execution claimed."
    assert result["position"]["source_ids"] == ["people.ledger"]
    assert result["position"]["model_status"] == "answered"
    assert "shared_conversations" not in provider.containers.runtime
    assert result["external_writes_performed"] is False


def test_status_uses_actual_department_pilots_and_excludes_products_area():
    service = OperationsExecutiveBriefingService(FakeProvider())
    status = service.status("home-fixed")
    channels = {item["department_id"]: item["display_name"] for item in status["channels"]}
    assert channels == {
        "sales": "Sales", "marketing": "Marketing", "finance": "Finance",
        "support": "Support", "people": "People", "legal": "Legal",
    }


def test_explicit_distinct_critic_enables_two_model_challenge():
    provider = FakeProvider()
    provider.containers.runtime["executive_briefing_config"] = {
        "critic_model_selection": {"provider": "premium", "model": "vault-critic"}
    }
    service = OperationsExecutiveBriefingService(provider)
    result = service.run_morning_briefing("home-fixed", person_id="founder")
    assert result["briefing"]["reasoning_mode"] == "two_model_challenge"
    assert result["briefing"]["critic_review"]["departments"]["sales"]["challenge"] == "Check conversion evidence"
