from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.company_structural_profile_store import (
    CompanyStructuralProfileStore,
)


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_company_structural_profile(tmp_path):
    store = CompanyStructuralProfileStore(tmp_path)

    payload = store.save_company_structural_profile(
        company_ref="company/ULVR.L",
        as_of_date=_dt(2026, 2, 28, 9, 0, 0),
        generated_by="pytest",
        labour_cost_ratio_pct=18.5,
        energy_cost_ratio_pct=4.2,
        debt_service_ratio_pct=2.1,
        fixed_cost_ratio_pct=41.0,
        variable_cost_ratio_pct=59.0,
        commodity_exposures=[
            {
                "commodity": "palm_oil",
                "exposure_direction": "input_cost",
                "materiality_pct": 32.0,
                "hedging_regime": "partial",
            }
        ],
        geographic_exposures=[
            {
                "region": "north_america",
                "revenue_share_pct": 22.0,
                "cost_share_pct": 18.0,
                "currency": "USD",
            }
        ],
        acquisition_history=[
            {
                "date": "2025-09-01",
                "target": "Dr Squatch",
                "deal_type": "acquisition",
                "capital_allocation_assessment": "disciplined",
            }
        ],
        key_people_events=[
            {
                "date": "2026-01-15",
                "person": "New CFO",
                "event_type": "hire",
                "seniority": "c_suite",
                "signal": "capital_discipline",
            }
        ],
        competitor_pressure={
            "market_share_pressure": "moderate",
            "pricing_pressure": "contained",
            "notes": "Latin America still competitive",
        },
        linked_refs={
            "company_refs": ["company/ULVR.L"],
            "quarter_event_refs": ["company/ULVR.L/quarter/2025-Q4"],
        },
        validate=True,
    )

    assert payload["company_ref"] == "company/ULVR.L"
    assert payload["as_of_date"] == "2026-02-28"

    loaded = store.load_company_structural_profile(
        "company/ULVR.L",
        as_of_date="2026-02-28",
    )

    assert loaded["company_structural_profile_id"] == payload["company_structural_profile_id"]
    assert loaded["cost_structure"]["labour_cost_ratio_pct"] == 18.5
    assert loaded["commodity_exposures"][0]["commodity"] == "palm_oil"
    assert loaded["geographic_exposures"][0]["currency"] == "USD"


def test_list_profiles(tmp_path):
    store = CompanyStructuralProfileStore(tmp_path)

    store.save_company_structural_profile(
        company_ref="company/AHT.L",
        as_of_date="2026-02-22",
        generated_by="pytest",
        payload_patch={
            "cost_structure": {
                "labour_cost_ratio_pct": 24.0,
            }
        },
        validate=True,
    )

    store.save_company_structural_profile(
        company_ref="company/AHT.L",
        as_of_date="2026-03-31",
        generated_by="pytest",
        payload_patch={
            "cost_structure": {
                "labour_cost_ratio_pct": 25.0,
            }
        },
        validate=True,
    )

    ids = store.list_profiles("company/AHT.L")
    assert ids == ["2026-02-22", "2026-03-31"]


def test_structural_profile_exists(tmp_path):
    store = CompanyStructuralProfileStore(tmp_path)

    assert not store.structural_profile_exists(
        "company/ULVR.L",
        as_of_date="2026-02-28",
    )

    store.save_profile(
        company_ref="company/ULVR.L",
        as_of_date="2026-02-28",
        generated_by="pytest",
        payload_patch={
            "cost_structure": {
                "energy_cost_ratio_pct": 3.9,
            }
        },
        validate=True,
    )

    assert store.structural_profile_exists(
        "company/ULVR.L",
        as_of_date="2026-02-28",
    )