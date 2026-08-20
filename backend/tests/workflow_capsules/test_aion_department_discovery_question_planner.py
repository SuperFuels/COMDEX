from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import department_pilot_api as api
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.department_discovery_planner_service import DepartmentDiscoveryPlannerService


class GeneratedQuestionProvider:
    def __init__(self, *, ok: bool = True):
        self.ok = ok
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        content = json.dumps({
            "status": "question",
            "question": "Which recorded offering currently has the least reliable direct-cost evidence?",
            "field_key": "least_reliable_offering_cost",
            "target_workspace": "products_services",
            "target_section": "jobs",
            "target_label": "Products & Services · Jobs",
            "answer_type": "money",
            "rationale": "Selling prices exist but delivery-cost evidence is incomplete.",
            "evidence_checked": ["operating_model.offerings", "operating_model.job_cost_items"],
        }) if self.ok else ""
        return SimpleNamespace(
            ok=self.ok, content=content, provider="test-agent", model="test-reasoner",
            latency_ms=2, fallback_used=False,
            error_code=None if self.ok else "provider_unavailable",
        )


class DuplicateThenRepairProvider(GeneratedQuestionProvider):
    def generate(self, **kwargs):
        self.calls.append(kwargs)
        duplicate = {
            "status": "question",
            "question": "What is Person One's daily labour cost rate?",
            "field_key": "person_one_daily_labour_cost",
            "target_workspace": "products_services",
            "target_section": "workforce",
            "target_label": "Products & Services · Workforce",
            "answer_type": "money_rate",
            "rationale": "Needed for costing.",
            "evidence_checked": ["operating_model.labour_resources"],
        }
        repaired = {
            "status": "question",
            "question": "Which offering lacks reliable material-cost evidence?",
            "field_key": "offering_material_cost_gap",
            "target_workspace": "products_services",
            "target_section": "jobs",
            "target_label": "Products & Services · Job costs",
            "answer_type": "text",
            "rationale": "Direct material costs are absent.",
            "evidence_checked": ["operating_model.job_cost_items"],
        }
        return SimpleNamespace(
            ok=True,
            content=json.dumps(duplicate if len(self.calls) == 1 else repaired),
            provider="test-agent", model="test-reasoner", latency_ms=2,
            fallback_used=False, error_code=None,
        )


def _seed(repository: BusinessContainerRepository):
    repository.save_dict("home-fixed", "business_identity", {
        "id": "home-fixed.business_identity", "workspace_id": "home-fixed",
        "kind": "business_identity", "trading_name": "Any Business",
    })
    repository.save_dict("home-fixed", "business_financial_model", {
        "id": "home-fixed.business_financial_model", "workspace_id": "home-fixed",
        "kind": "business_financial_model", "currency": "EUR",
        "missing_information": ["direct delivery cost evidence"],
    })
    repository.save_dict("home-fixed", "business_operating_model", {
        "id": "home-fixed.business_operating_model", "workspace_id": "home-fixed",
        "kind": "business_operating_model",
        "offerings": [{"name": "Arbitrary service", "price": 250}],
        "labour_resources": [{
            "person_name": "Person One", "cost_basis": "daily", "cost_rate": 120,
        }],
        "job_cost_items": [],
    })


def test_department_agent_generates_one_question_from_canonical_business_context(tmp_path):
    repository = BusinessContainerRepository(tmp_path / "containers")
    _seed(repository)
    provider = GeneratedQuestionProvider()
    service = DepartmentDiscoveryPlannerService(
        container_repository=repository,
        provider_router=provider,  # type: ignore[arg-type]
    )

    result = service.next_question("home-fixed", "finance")

    assert result["status"] == "question"
    assert result["question"].endswith("?")
    assert result["field_key"] == "least_reliable_offering_cost"
    assert result["source"] == "department_pilot_provider"
    assert result["provider"] == "test-agent"
    assert result["question_hash"].startswith("sha256:")
    prompt = provider.calls[0]
    assert prompt["role_type"] == "FINANCE"
    assert prompt["metadata"]["read_only"] is True
    assert "Arbitrary service" in prompt["prompt"]
    assert "Never use a generic fixed questionnaire" in prompt["system_prompt"]


def test_unavailable_provider_uses_only_a_recorded_gap_not_a_fixed_question(tmp_path):
    repository = BusinessContainerRepository(tmp_path / "containers")
    _seed(repository)
    service = DepartmentDiscoveryPlannerService(
        container_repository=repository,
        provider_router=GeneratedQuestionProvider(ok=False),  # type: ignore[arg-type]
    )

    result = service.next_question("home-fixed", "finance")

    assert result["source"] == "recorded_gap_fallback"
    assert "direct delivery cost evidence" in result["question"]
    assert result["provider_error"] == "provider_unavailable"


def test_question_about_an_existing_fact_is_rejected_and_repaired(tmp_path):
    repository = BusinessContainerRepository(tmp_path / "containers")
    _seed(repository)
    provider = DuplicateThenRepairProvider()
    service = DepartmentDiscoveryPlannerService(
        container_repository=repository,
        provider_router=provider,  # type: ignore[arg-type]
    )

    result = service.next_question("home-fixed", "finance")

    assert len(provider.calls) == 2
    assert provider.calls[1]["metadata"]["operation"] == "discovery_question_repair"
    assert "daily labour cost" not in result["question"].lower()
    assert result["field_key"] == "offering_material_cost_gap"


def test_discovery_planner_api_is_available_to_each_department_pilot(tmp_path, monkeypatch):
    repository = BusinessContainerRepository(tmp_path / "containers")
    _seed(repository)
    service = DepartmentDiscoveryPlannerService(
        container_repository=repository,
        provider_router=GeneratedQuestionProvider(),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(api, "get_department_discovery_planner_service", lambda: service)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)

    response = client.post(
        "/api/aion/business/department-pilots/home-fixed/finance/discovery/next-question",
        json={"resolved_field_keys": [], "skipped_field_keys": [], "recent_questions": []},
    )

    assert response.status_code == 200
    assert response.json()["department_id"] == "finance"
    assert response.json()["external_writes_performed"] is False
