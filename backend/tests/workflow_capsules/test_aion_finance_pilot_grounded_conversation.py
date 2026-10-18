from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import department_pilot_api as api
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.finance_pilot_conversation_service import (
    FinancePilotConversationRepository,
    FinancePilotConversationService,
)


class FakeProvider:
    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            ok=self.ok,
            content=(
                "Revenue is EUR 378,750 and gross profit is EUR 235,016. "
                "The records do not yet prove a period comparison. [Financial Model]"
                if self.ok
                else ""
            ),
            provider="test_finance_model",
            model="grounded-test",
            latency_ms=4,
            fallback_used=False,
            error_code=None if self.ok else "provider_unavailable",
        )


def _seed(containers: BusinessContainerRepository) -> dict:
    model = {
        "id": "home-fixed.business_financial_model",
        "workspace_id": "home-fixed",
        "kind": "business_financial_model",
        "currency": "EUR",
        "reporting_period": {"basis": "annual", "label": "FY2025"},
        "metrics": {
            "revenue": 378750,
            "gross_profit": 235016,
            "operating_profit": 152346,
            "ending_cash": 159011,
        },
        "missing_information": ["prior-period comparison"],
        "evidence_refs": [
            {
                "source": "finance_artifact",
                "artifact_id": "management-accounts-2025",
                "verification_status": "accepted",
            }
        ],
        "revision": 8,
    }
    containers.save_dict("home-fixed", "business_financial_model", model)
    containers.save_dict(
        "home-fixed",
        "business_operating_model",
        {
            "id": "home-fixed.business_operating_model",
            "workspace_id": "home-fixed",
            "kind": "business_operating_model",
            "offerings": [{"name": "Home repairs"}],
            "revision": 3,
        },
    )
    containers.save_dict(
        "home-fixed",
        "department_intelligence",
        {
            "id": "home-fixed.department_intelligence",
            "workspace_id": "home-fixed",
            "kind": "department_intelligence",
            "departments": {"finance": {"status": "active"}},
            "revision": 4,
        },
    )
    return model


def test_grounded_finance_conversation_is_separate_persistent_and_source_labelled(tmp_path):
    containers = BusinessContainerRepository(tmp_path / "business_containers")
    original_model = _seed(containers)
    conversations = FinancePilotConversationRepository(tmp_path / "department_runtime")
    provider = FakeProvider()
    service = FinancePilotConversationService(
        container_repository=containers,
        conversation_repository=conversations,
        provider_router=provider,  # type: ignore[arg-type]
    )

    result = service.answer(
        "home-fixed",
        "What are revenue and gross profit, and can you compare them with last year?",
        created_at="2026-07-20T14:00:00+00:00",
    )

    assert result["external_writes_performed"] is False
    assert result["turn"]["reliability"] == "source_backed"
    assert "[Financial Model]" in result["turn"]["content"]
    assert result["turn"]["sources"][0]["content_hash"].startswith("sha256:")
    assert provider.calls[0]["capability"] == "drafting"
    assert provider.calls[0]["role_type"] == "FINANCE"
    assert provider.calls[0]["metadata"]["read_only"] is True

    restored = FinancePilotConversationService(
        container_repository=containers,
        conversation_repository=FinancePilotConversationRepository(
            tmp_path / "department_runtime"
        ),
        provider_router=provider,  # type: ignore[arg-type]
    ).get_session("home-fixed")
    assert [turn["role"] for turn in restored["turns"]] == ["user", "assistant"]
    assert restored["turns"][1]["previous_turn_hash"] == restored["turns"][0][
        "turn_hash"
    ]
    assert containers.load_dict("home-fixed", "business_financial_model") == original_model


def test_finance_conversation_has_grounded_fallback_when_provider_is_unavailable(tmp_path):
    containers = BusinessContainerRepository(tmp_path / "business_containers")
    _seed(containers)
    service = FinancePilotConversationService(
        container_repository=containers,
        conversation_repository=FinancePilotConversationRepository(
            tmp_path / "department_runtime"
        ),
        provider_router=FakeProvider(ok=False),  # type: ignore[arg-type]
    )

    result = service.answer("home-fixed", "Give me the Finance update")

    assert "€378,750.00" in result["turn"]["content"]
    assert "no external action was taken" in result["turn"]["content"]
    assert result["turn"]["provider"]["provider"] == "deterministic_finance_fallback"


def test_turnover_is_a_direct_period_labelled_fact_not_a_generic_briefing(tmp_path):
    containers = BusinessContainerRepository(tmp_path / "business_containers")
    _seed(containers)
    provider = FakeProvider(ok=False)
    service = FinancePilotConversationService(
        container_repository=containers,
        conversation_repository=FinancePilotConversationRepository(tmp_path / "department_runtime"),
        provider_router=provider,  # type: ignore[arg-type]
    )

    result = service.answer("home-fixed", "What is the turnover of the business?")

    assert result["turn"]["content"].startswith("Turnover for FY2025 is €378,750.00.")
    assert "Gross Profit" not in result["turn"]["content"]
    assert result["turn"]["provider"]["provider"] == "deterministic_finance_fact"
    assert provider.calls == []


def test_finance_conversation_api_returns_and_restores_the_durable_session(
    tmp_path, monkeypatch
):
    containers = BusinessContainerRepository(tmp_path / "business_containers")
    _seed(containers)
    service = FinancePilotConversationService(
        container_repository=containers,
        conversation_repository=FinancePilotConversationRepository(
            tmp_path / "department_runtime"
        ),
        provider_router=FakeProvider(),  # type: ignore[arg-type]
    )
    monkeypatch.setattr(api, "get_finance_pilot_conversation_service", lambda: service)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)

    turn = client.post(
        "/api/aion/business/department-pilots/home-fixed/finance/conversation/turn",
        json={
            "user_text": "What is our revenue?",
            "created_at": "2026-07-20T14:05:00+00:00",
        },
    )
    assert turn.status_code == 200
    assert turn.json()["turn"]["role"] == "assistant"

    session = client.get(
        "/api/aion/business/department-pilots/home-fixed/finance/conversation/session"
    )
    assert session.status_code == 200
    assert len(session.json()["session"]["turns"]) == 2
    assert session.json()["session"]["session_hash"].startswith("sha256:")
