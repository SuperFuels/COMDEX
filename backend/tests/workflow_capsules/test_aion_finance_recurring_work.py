from __future__ import annotations

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_recurring_work_service import FinanceRecurringWorkService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


def _service(tmp_path, monkeypatch):
    root = tmp_path / "runtime"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", root)
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", root / "business_containers")
    repository = BusinessContainerRepository(root / "business_containers")
    repository.save_dict("home-fixed", "business_financial_model", {
        "id": "home-fixed.business_financial_model", "workspace_id": "home-fixed",
        "kind": "business_financial_model", "currency": "EUR",
        "metrics": {"revenue": 378750, "gross_profit": 235016,
                    "operating_profit": 152346, "ending_cash": 159011},
        "missing_information": [], "revision": 5,
    })
    repository.save_dict("home-fixed", "department_intelligence", {
        "id": "home-fixed.department_intelligence", "workspace_id": "home-fixed",
        "kind": "department_intelligence", "departments": {"finance": {"department": "finance"}},
        "revision": 1,
    })
    repository.save_dict("home-fixed", "boardroom_snapshot", {
        "id": "home-fixed.boardroom_snapshot", "workspace_id": "home-fixed",
        "kind": "boardroom_snapshot", "boardroom": {"runtime": {}}, "revision": 1,
    })
    return FinanceRecurringWorkService(repository), repository


def test_all_finance_recurring_jobs_persist_runs_failures_and_boardroom_projection(tmp_path, monkeypatch):
    service, repository = _service(tmp_path, monkeypatch)
    definitions = (
        ("weekly-cash", "weekly_cash_update", "weekly"),
        ("monthly-report", "monthly_management_report", "monthly"),
        ("period-close", "period_close_check", "monthly"),
        ("cash-alert", "exception_cash_buffer_alert", "daily"),
    )
    for schedule_id, kind, cadence in definitions:
        service.create("home-fixed", schedule_id=schedule_id, kind=kind, cadence=cadence,
                       next_run_at="2026-07-21T08:00:00+00:00", created_by="founder:kevin",
                       minimum_cash_reserve=200000 if kind == "exception_cash_buffer_alert" else 0)
    results = service.run_due("home-fixed", now="2026-07-21T09:00:00+00:00")
    assert len(results) == 4
    assert all(item["ok"] for item in results)
    assert next(item for item in results if item["schedule_id"] == "cash-alert")["run"]["result"]["alert"] is True
    assert all(item["run"]["external_action_performed"] is False for item in results)
    assert all(item["file_cabinet_pointer"]["target"]["run_hash"].startswith("sha256:") for item in results)
    assert all(item["last_run_status"] == "completed" for item in service.list("home-fixed"))

    intelligence = repository.load_dict("home-fixed", "department_intelligence")
    assert set(intelligence["departments"]["finance"]["recurring_work"]) == {
        "weekly-cash", "monthly-report", "period-close", "cash-alert"
    }
    snapshot = repository.load_dict("home-fixed", "boardroom_snapshot")
    assert snapshot["boardroom"]["runtime"]["latest_finance_recurring_run"]["status"] == "completed"
    cabinet = WorkflowFileCabinetRepository.load("home-fixed")
    finance = next(item for item in cabinet["folders"] if item["name"] == "Finance")
    recurring = next(item for item in finance["children"] if item["name"] == "Recurring")
    assert len(recurring["children"]) == 4


def test_schedule_failure_state_survives_restart_and_can_be_paused(tmp_path, monkeypatch):
    service, repository = _service(tmp_path, monkeypatch)
    service.create("home-fixed", schedule_id="weekly-cash", kind="weekly_cash_update", cadence="weekly",
                   next_run_at="2026-07-21T08:00:00+00:00", created_by="founder:kevin")
    model_path = repository.base_dir / "home-fixed" / "business_financial_model.json"
    model_path.unlink()
    try:
        service.run("home-fixed", "weekly-cash", run_at="2026-07-21T09:00:00+00:00")
        raise AssertionError("expected missing financial model")
    except FileNotFoundError:
        pass
    restarted = FinanceRecurringWorkService(repository)
    schedule = restarted.list("home-fixed")[0]
    assert schedule["last_run_status"] == "failed"
    assert schedule["failure_count"] == 1
    assert "business_financial_model" in schedule["last_error"]
    runs = list((AIONBusinessPaths.BUSINESS_CONTAINERS / "home-fixed" / "finance" / "recurring" / "weekly-cash" / "runs").glob("*.json"))
    assert len(runs) == 1
    assert '"status": "failed"' in runs[0].read_text()
    assert restarted.set_enabled("home-fixed", "weekly-cash", False)["enabled"] is False
