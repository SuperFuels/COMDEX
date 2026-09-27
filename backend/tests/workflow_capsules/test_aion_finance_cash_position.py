from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api import department_pilot_api as api
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)


def test_cash_in_hand_is_a_persistent_non_ledger_record(tmp_path, monkeypatch):
    repository = BusinessContainerRepository(tmp_path / "business_containers")
    monkeypatch.setattr(api, "get_business_container_repository", lambda: repository)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)

    initial = client.get(
        "/api/aion/business/department-pilots/finance-cash-position",
        params={"workspace_id": "home-fixed"},
    )
    assert initial.status_code == 200
    assert initial.json()["cash_position"]["cash_in_hand"] == 0
    assert initial.json()["cash_position"]["posts_to_accounting_ledger"] is False

    saved = client.post(
        "/api/aion/business/department-pilots/finance-cash-position",
        params={"workspace_id": "home-fixed"},
        json={
            "cash_in_hand": 5000,
            "currency": "gbp",
            "as_of_date": "2026-09-24",
            "updated_by": "owner",
            "updated_at": "2026-09-24T20:50:00+00:00",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["cash_position"]["cash_in_hand"] == 5000
    assert saved.json()["cash_position"]["currency"] == "GBP"
    assert saved.json()["external_write_performed"] is False
    assert saved.json()["accounting_ledger_changed"] is False

    restored = client.get(
        "/api/aion/business/department-pilots/finance-cash-position",
        params={"workspace_id": "home-fixed"},
    )
    assert restored.status_code == 200
    assert restored.json()["cash_position"] == saved.json()["cash_position"]
