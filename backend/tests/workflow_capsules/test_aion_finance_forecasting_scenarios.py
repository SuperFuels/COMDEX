from __future__ import annotations

import json
from pathlib import Path

from backend.modules.aion_business.api import department_pilot_api as api
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_forecasting_service import FinanceForecastingService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _configure(monkeypatch, tmp_path: Path) -> BusinessContainerRepository:
    root = tmp_path / "AION_BUSINESS"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", root / "business_containers")
    monkeypatch.setattr(AIONBusinessPaths, "WORKSPACES", root / "workspaces")
    return BusinessContainerRepository(root / "business_containers")


def _seed(repository: BusinessContainerRepository, workspace_id: str = "home-fixed") -> None:
    repository.save_dict(workspace_id, "business_financial_model", {
        "id": f"{workspace_id}.business_financial_model",
        "workspace_id": workspace_id,
        "kind": "business_financial_model",
        "meta": {"workspace_id": workspace_id, "container_key": "business_financial_model", "source": "accepted_management_accounts"},
        "currency": "EUR",
        "period_basis": "annual",
        "reporting_period": {"label": "Year ended 31 December 2025", "from": "2025-01-01", "to": "2025-12-31", "basis": "annual"},
        "metrics": {"revenue": 120000, "direct_costs": 48000, "overheads": 24000, "ending_cash": 30000},
        "evidence_refs": [{"source": "management_accounts", "accepted_at": "2026-07-19T12:00:00+00:00", "verification_status": "accepted_from_source_document"}],
        "revision": 3,
    })
    repository.save_dict(workspace_id, "department_intelligence", {
        "id": f"{workspace_id}.department_intelligence",
        "workspace_id": workspace_id,
        "kind": "department_intelligence",
        "meta": {"workspace_id": workspace_id, "container_key": "department_intelligence", "source": "test"},
        "departments": {},
        "revision": 1,
    })
    repository.save_dict(workspace_id, "boardroom_snapshot", {
        "id": f"{workspace_id}.boardroom_snapshot",
        "workspace_id": workspace_id,
        "kind": "boardroom_snapshot",
        "meta": {"workspace_id": workspace_id, "container_key": "boardroom_snapshot", "source": "test"},
        "topology": {},
        "boardroom": {},
    })


def test_forecast_builds_expected_upside_downside_and_preserves_historical_truth(monkeypatch, tmp_path: Path) -> None:
    repository = _configure(monkeypatch, tmp_path)
    _seed(repository)
    before = repository.load_dict("home-fixed", "business_financial_model")
    service = FinanceForecastingService(repository)

    scenario, pointer = service.run("home-fixed", {
        "scenario_id": "growth-and-hire",
        "forecast_months": 3,
        "revenue_change_percent": 10,
        "direct_cost_change_percent": 5,
        "monthly_hiring_cost": 1000,
        "one_off_stock_purchase": 5000,
        "stock_purchase_month": 2,
        "minimum_cash_reserve": 25000,
        "sensitivity_percent": 10,
    }, scenario_name="Growth and hire", created_at="2026-07-20T12:00:00+00:00")

    assert scenario["status"] == "modelled_not_actual"
    assert scenario["historical_finance_mutated"] is False
    assert scenario["monthly_baseline"] == {
        "revenue": 10000.0,
        "direct_costs": 4000.0,
        "overheads": 2000.0,
        "opening_cash": 30000.0,
        "source_period_months": 12.0,
    }
    assert scenario["variants"]["expected"]["months"][0]["operating_profit"] == 3800
    assert scenario["variants"]["expected"]["months"][1]["stock_purchase"] == 5000
    assert scenario["variants"]["upside"]["summary"]["closing_cash"] > scenario["variants"]["expected"]["summary"]["closing_cash"]
    assert scenario["variants"]["downside"]["summary"]["closing_cash"] < scenario["variants"]["expected"]["summary"]["closing_cash"]
    assert repository.load_dict("home-fixed", "business_financial_model") == before
    assert pointer["target"]["scenario_hash"] == scenario["scenario_hash"]


def test_scenario_is_indexed_in_intelligence_boardroom_and_file_cabinet(monkeypatch, tmp_path: Path) -> None:
    repository = _configure(monkeypatch, tmp_path)
    _seed(repository)
    scenario, _pointer = FinanceForecastingService(repository).run(
        "home-fixed",
        {"scenario_id": "cash-protection", "forecast_months": 2, "minimum_cash_reserve": 32000},
        scenario_name="Cash protection",
        created_at="2026-07-20T12:00:00+00:00",
    )
    intelligence = repository.load_dict("home-fixed", "department_intelligence")
    assert intelligence["departments"]["finance"]["latest_scenario"]["scenario_id"] == "cash-protection"
    boardroom = repository.load_dict("home-fixed", "boardroom_snapshot")
    assert boardroom["boardroom"]["runtime"]["latest_finance_scenario"]["scenario_hash"] == scenario["scenario_hash"]
    cabinet = json.loads((AIONBusinessPaths.ROOT / "workflow_file_cabinets/home-fixed/tree.json").read_text())
    assert "Scenarios" in json.dumps(cabinet)
    assert "Cash protection" in json.dumps(cabinet)


def test_scenario_api_runs_and_lists_separate_hash_bound_records(monkeypatch, tmp_path: Path) -> None:
    repository = _configure(monkeypatch, tmp_path)
    _seed(repository)
    monkeypatch.setattr(api, "get_business_container_repository", lambda: repository)
    response = api.run_finance_scenario("Home Fixed", api.FinanceScenarioRequest(
        scenario_id="api-case",
        scenario_name="API case",
        forecast_months=4,
        price_change_percent=5,
    ))
    assert response["ok"] is True
    assert response["scenario"]["scenario_id"] == "api-case"
    listed = api.list_finance_scenarios("Home Fixed")
    assert listed["latest_scenario"]["scenario_id"] == "api-case"
    assert listed["scenarios"][0]["scenario_hash"]


def test_scenario_refuses_to_invent_a_missing_baseline(monkeypatch, tmp_path: Path) -> None:
    repository = _configure(monkeypatch, tmp_path)
    _seed(repository)
    model = repository.load_dict("home-fixed", "business_financial_model")
    del model["metrics"]["overheads"]
    repository.save_dict("home-fixed", "business_financial_model", model)
    try:
        FinanceForecastingService(repository).run("home-fixed", {"forecast_months": 12})
    except ValueError as exc:
        assert str(exc) == "scenario_baseline_missing:overheads"
    else:
        raise AssertionError("Scenario should refuse an incomplete evidence baseline")


def test_scenario_retrieval_rejects_a_tampered_record(monkeypatch, tmp_path: Path) -> None:
    repository = _configure(monkeypatch, tmp_path)
    _seed(repository)
    service = FinanceForecastingService(repository)
    service.run("home-fixed", {"scenario_id": "tamper-check", "forecast_months": 2})
    path = AIONBusinessPaths.business_container_dir("home-fixed") / "finance/scenarios/tamper-check.json"
    record = json.loads(path.read_text())
    record["variants"]["expected"]["summary"]["closing_cash"] = 999999999
    path.write_text(json.dumps(record))
    try:
        service.list("home-fixed")
    except ValueError as exc:
        assert str(exc) == "finance_scenario_integrity_failed:tamper-check.json"
    else:
        raise AssertionError("A tampered scenario must not be returned to Finance or the Boardroom")
