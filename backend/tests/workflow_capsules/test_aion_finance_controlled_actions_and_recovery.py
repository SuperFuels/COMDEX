from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import department_pilot_api as api
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.department_pilot_repository import DepartmentPilotRepository
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _client(tmp_path, monkeypatch):
    root = tmp_path / "runtime"
    monkeypatch.setattr(AIONBusinessPaths, "ROOT", root)
    monkeypatch.setattr(AIONBusinessPaths, "DEPARTMENT_PILOT_RUNTIME", root / "department_pilots")
    monkeypatch.setattr(AIONBusinessPaths, "BUSINESS_CONTAINERS", root / "business_containers")
    tasks = DepartmentPilotRepository(root / "department_pilots")
    containers = BusinessContainerRepository(root / "business_containers")
    monkeypatch.setattr(api, "get_department_pilot_repository", lambda: tasks)
    monkeypatch.setattr(api, "get_business_container_repository", lambda: containers)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app), tasks


def _route(client: TestClient) -> str:
    response = client.post(
        "/api/aion/business/department-pilots/approve-boardroom-action",
        json={
            "workspace_id": "home-fixed", "business_id": "home-fixed",
            "boardroom_session_id": "session-controlled", "boardroom_decision_id": "decision-controlled",
            "package_id": "package-controlled", "title": "Prepare debtor follow-up",
            "objective": "Prepare a draft reminder without sending it.", "department_id": "finance",
            "actions": [{"action_id": "action-controlled", "title": "Draft reminder",
                         "objective": "Prepare a draft debtor reminder.", "department_id": "finance",
                         "capability": "finance.controlled_draft"}],
            "approval_id": "board-approval-controlled", "approved_by": "founder:kevin",
            "approved_at": "2026-07-21T09:00:00+00:00",
        },
    )
    assert response.status_code == 200
    return response.json()["tasks"][0]["task"]["task_id"]


def test_exact_payload_approval_never_enables_unconfigured_live_write(tmp_path, monkeypatch):
    client, tasks = _client(tmp_path, monkeypatch)
    task_id = _route(client)
    proposed = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/proposals",
        json={"tool_call_id": "draft-1", "tool_name": "finance.credit_control.draft",
              "provider": "xero", "payload": {"contact_id": "C-10", "amount": 1250, "currency": "EUR"},
              "rationale": "Prepare a reviewable debtor reminder."},
    )
    assert proposed.status_code == 200
    envelope = proposed.json()["envelope"]
    payload_hash = envelope["proposed_tool_calls"][0]["payload_hash"]
    assert envelope["task"]["status"] == "waiting_approval"
    assert proposed.json()["external_action_performed"] is False

    duplicate = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/proposals",
        json={"tool_call_id": "draft-1", "tool_name": "finance.credit_control.draft",
              "provider": "xero", "payload": {"contact_id": "C-10"}, "rationale": "Duplicate"},
    )
    assert duplicate.status_code == 409
    assert len(tasks.load("home-fixed", "finance", task_id).proposed_tool_calls) == 1

    mismatch = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/proposals/draft-1/decision",
        json={"approval_id": "approval-wrong", "approved": True, "decided_by": "founder:kevin",
              "decided_payload_hash": "sha256:" + "0" * 64},
    )
    assert mismatch.status_code == 409
    assert tasks.load("home-fixed", "finance", task_id).task.status == "waiting_approval"

    approved = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/proposals/draft-1/decision",
        json={"approval_id": "approval-exact", "approved": True, "decided_by": "founder:kevin",
              "decided_payload_hash": payload_hash},
    )
    assert approved.status_code == 200
    readiness = client.get(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/proposals/draft-1/readiness"
    )
    assert readiness.json() == {
        "ready": False, "code": "live_connector_permission_not_enabled",
        "external_action_performed": False, "tool_call_id": "draft-1", "payload_hash": payload_hash,
    }
    repeated = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/proposals/draft-1/decision",
        json={"approval_id": "approval-repeat", "approved": True, "decided_by": "founder:kevin",
              "decided_payload_hash": payload_hash},
    )
    assert repeated.status_code == 409


def test_unlisted_finance_tool_is_rejected_before_task_is_claimed(tmp_path, monkeypatch):
    client, tasks = _client(tmp_path, monkeypatch)
    task_id = _route(client)
    response = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/proposals",
        json={"tool_call_id": "unsafe-1", "tool_name": "xero.payment.create",
              "provider": "xero", "payload": {"amount": 5000}, "rationale": "Attempt live payment"},
    )
    assert response.status_code == 403
    envelope = tasks.load("home-fixed", "finance", task_id)
    assert envelope.task.status == "queued"
    assert envelope.proposed_tool_calls == []


def test_failed_task_has_diagnostics_retry_recovery_and_cancellation(tmp_path, monkeypatch):
    client, tasks = _client(tmp_path, monkeypatch)
    task_id = _route(client)
    runtime = api.DepartmentPilotRuntime(tasks)
    for status, event in (("claimed", "claimed"), ("running", "running"), ("failed", "failed")):
        runtime.transition(workspace_id="home-fixed", department_id="finance", task_id=task_id,
                           to_status=status, occurred_at="2026-07-21T09:01:00+00:00",
                           actor_id="finance_pilot", event_id=f"{task_id}-{event}",
                           message="Synthetic failure" if status == "failed" else status,
                           data={"error_code": "test_failure"} if status == "failed" else {})
    diagnostic = client.get(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/diagnostics"
    ).json()
    assert diagnostic["status"] == "failed"
    assert diagnostic["retry_available"] is True
    assert diagnostic["latest_failure"]["data"]["error_code"] == "test_failure"

    retried = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/retry",
        json={"actor_id": "founder:kevin", "reason": "Evidence source restored"},
    )
    assert retried.status_code == 200
    assert retried.json()["envelope"]["task"]["status"] == "queued"
    assert retried.json()["envelope"]["task"]["retry_count"] == 1

    cancelled = client.post(
        f"/api/aion/business/department-pilots/home-fixed/finance/{task_id}/cancel",
        json={"actor_id": "founder:kevin", "reason": "No longer required"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["envelope"]["task"]["status"] == "cancelled"


def test_cross_business_task_lookup_cannot_reach_other_business(tmp_path, monkeypatch):
    client, _tasks = _client(tmp_path, monkeypatch)
    task_id = _route(client)
    response = client.get(
        f"/api/aion/business/department-pilots/another-business/finance/{task_id}/diagnostics"
    )
    assert response.status_code == 404


def test_finance_sensitive_data_and_permission_matrix_is_explicit_and_deny_by_default(tmp_path, monkeypatch):
    client, _tasks = _client(tmp_path, monkeypatch)
    response = client.get(
        "/api/aion/business/department-pilots/home-fixed/finance/security-policy"
    )
    assert response.status_code == 200
    policy = response.json()["policy"]
    assert policy["default_posture"] == "deny_external_write"
    assert policy["credential_material_allowed_in_business_container"] is False
    assert policy["data_classes"]["credentials_and_tokens"]["boardroom_projection"] == "never"
    assert policy["data_classes"]["payroll_and_tax_sensitive"]["boardroom_projection"] == "aggregates_only"
    assert policy["capability_matrix"]["read_accounting_data"]["enabled"] is True
    assert policy["capability_matrix"]["match_individual_transactions"]["enabled"] is True
    assert policy["capability_matrix"]["accept_transaction_match_draft"]["enabled"] is True
    assert policy["capability_matrix"]["post_reconciliation_or_journal"]["enabled"] is False
    assert policy["capability_matrix"]["create_payment_or_transfer_funds"]["mode"] == "prohibited"


def test_finance_recurring_route_is_not_shadowed_by_generic_department_queue(tmp_path, monkeypatch):
    client, _tasks = _client(tmp_path, monkeypatch)
    response = client.get(
        "/api/aion/business/department-pilots/finance-recurring",
        params={"workspace_id": "home-fixed"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "workspace_id": "home-fixed", "schedules": []}

    scenarios = client.get(
        "/api/aion/business/department-pilots/finance-scenarios",
        params={"workspace_id": "home-fixed"},
    )
    reconciliations = client.get(
        "/api/aion/business/department-pilots/finance-reconciliations",
        params={"workspace_id": "home-fixed"},
    )
    assert scenarios.status_code == 200
    assert scenarios.json()["scenarios"] == []
    assert reconciliations.status_code == 200
    assert reconciliations.json()["reconciliations"] == []

    ledger = client.get(
        "/api/aion/business/department-pilots/finance-ledger",
        params={"workspace_id": "home-fixed"},
    )
    transaction_reconciliation = client.get(
        "/api/aion/business/department-pilots/finance-transaction-reconciliation",
        params={"workspace_id": "home-fixed"},
    )
    director = client.get(
        "/api/aion/business/department-pilots/finance-director",
        params={"workspace_id": "home-fixed"},
    )
    assert ledger.status_code == 200
    assert ledger.json()["ledger"] is None
    assert transaction_reconciliation.status_code == 200
    assert transaction_reconciliation.json()["latest_transaction_reconciliation"] is None
    assert director.status_code == 200
    assert director.json()["finance_director"] is None
