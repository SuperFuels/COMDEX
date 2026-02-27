from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.company_store import (
    build_company_payload,
    company_storage_path,
    load_company_payload,
    save_company_payload,
    upsert_company,
)
from backend.modules.aion_equities.schema_validate import validate_payload


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_build_company_payload_validates():
    payload = build_company_payload(
        ticker="AHT.L",
        name="Ashtead Group plc",
        exchange="LSE",
        currency="GBP",
        sector_ref="sector/industrial_equipment_rental",
        created_by="pytest",
        status="watchlist",
        acs_band="high",
        sector_confidence_tier="tier_1",
        latest_assessment_ref="assessment/AHT.L/2026-02-22T22:00:00Z",
        active_thesis_refs=["thesis/AHT.L/long/2026Q2_pre_earnings"],
        created_at=_dt(2026, 2, 22, 22, 0, 0),
        updated_at=_dt(2026, 2, 22, 22, 0, 0),
        validate=True,
    )
    validate_payload("company", payload, version="v0_1")
    assert payload["company_id"] == "company/AHT.L"
    assert payload["ticker"] == "AHT.L"


def test_save_and_load_company_payload_roundtrip(tmp_path):
    payload = build_company_payload(
        ticker="AHT.L",
        name="Ashtead Group plc",
        exchange="LSE",
        currency="GBP",
        sector_ref="sector/industrial_equipment_rental",
        created_by="pytest",
        latest_assessment_ref="",
        active_thesis_refs=[],
        created_at=_dt(2026, 2, 22, 22, 0, 0),
        updated_at=_dt(2026, 2, 22, 22, 0, 0),
        validate=True,
    )

    path = save_company_payload(payload, base_dir=tmp_path, validate=True)
    assert path == company_storage_path("AHT.L", base_dir=tmp_path)

    loaded = load_company_payload("AHT.L", base_dir=tmp_path, validate=True)
    assert loaded["company_id"] == "company/AHT.L"
    assert loaded["name"] == "Ashtead Group plc"


def test_upsert_company_creates_then_updates(tmp_path):
    created = upsert_company(
        ticker="AHT.L",
        name="Ashtead Group plc",
        exchange="LSE",
        currency="GBP",
        sector_ref="sector/industrial_equipment_rental",
        created_by="pytest",
        base_dir=tmp_path,
        latest_assessment_ref="assessment/AHT.L/2026-02-22T22:00:00Z",
        active_thesis_refs=[],
        acs_band="high",
        sector_confidence_tier="tier_1",
        validate=True,
    )

    updated = upsert_company(
        ticker="AHT.L",
        name="Ashtead Group plc",
        exchange="LSE",
        currency="GBP",
        sector_ref="sector/industrial_equipment_rental",
        updated_by="pytest_update",
        base_dir=tmp_path,
        latest_assessment_ref="assessment/AHT.L/2026-03-01T22:00:00Z",
        active_thesis_refs=["thesis/AHT.L/long/2026Q2_pre_earnings"],
        acs_band="high",
        sector_confidence_tier="tier_1",
        validate=True,
    )

    assert created["audit"]["created_by"] == "pytest"
    assert updated["audit"]["created_by"] == "pytest"
    assert updated["intelligence_state"]["latest_assessment_ref"] == "assessment/AHT.L/2026-03-01T22:00:00Z"
    assert updated["intelligence_state"]["active_thesis_refs"] == [
        "thesis/AHT.L/long/2026Q2_pre_earnings"
    ]