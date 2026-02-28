from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.sector_template_store import SectorTemplateStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_sector_template(tmp_path):
    store = SectorTemplateStore(tmp_path)

    payload = store.save_sector_template(
        sector_ref="sector/plant_hire",
        sector_name="Plant Hire",
        as_of_date=_dt(2026, 2, 22, 8, 0, 0),
        created_by="pytest",
        variable_map_patch={
            "primary_variables": [
                {
                    "name": "construction_pmi",
                    "category": "macro",
                    "directionality": "positive",
                    "typical_lag_days": 30,
                    "notes": "Primary activity signal",
                }
            ],
            "secondary_variables": [
                {
                    "name": "weather_disruption",
                    "category": "weather",
                    "notes": "Q1 site activity sensitivity",
                }
            ],
        },
        reporting_template_patch={
            "core_metrics": ["revenue", "fleet_utilisation", "hire_rates"],
            "margin_focus": ["operating_margin"],
            "cash_flow_focus": ["free_cash_flow"],
            "balance_sheet_focus": ["net_debt", "interest_cover"],
            "management_signals": ["guidance_language"],
        },
        fingerprint_defaults_patch={
            "base_predictability": "high",
            "macro_sensitivity": "high",
        },
        validate=True,
    )

    assert payload["sector_template_id"] == "sector_template/plant_hire"

    loaded = store.load_sector_template("sector/plant_hire")
    assert loaded["sector_ref"] == "sector/plant_hire"
    assert loaded["sector_name"] == "Plant Hire"
    assert loaded["variable_map"]["primary_variables"][0]["name"] == "construction_pmi"


def test_list_sector_templates(tmp_path):
    store = SectorTemplateStore(tmp_path)

    store.save_sector_template(
        sector_ref="sector/plant_hire",
        sector_name="Plant Hire",
        as_of_date="2026-02-22",
        created_by="pytest",
        variable_map_patch={
            "primary_variables": [
                {
                    "name": "construction_pmi",
                    "category": "macro",
                    "directionality": "positive",
                    "typical_lag_days": 30,
                }
            ]
        },
        reporting_template_patch={
            "core_metrics": ["revenue"],
            "margin_focus": [],
            "cash_flow_focus": [],
            "balance_sheet_focus": [],
        },
        validate=True,
    )

    store.save_sector_template(
        sector_ref="sector/staffing",
        sector_name="Staffing",
        as_of_date="2026-02-22",
        created_by="pytest",
        variable_map_patch={
            "primary_variables": [
                {
                    "name": "employment_pmi",
                    "category": "labour",
                    "directionality": "positive",
                    "typical_lag_days": 45,
                }
            ]
        },
        reporting_template_patch={
            "core_metrics": ["gross_profit"],
            "margin_focus": [],
            "cash_flow_focus": [],
            "balance_sheet_focus": [],
        },
        validate=True,
    )

    ids = store.list_sector_templates()
    assert "sector_plant_hire" in ids
    assert "sector_staffing" in ids


def test_sector_template_exists(tmp_path):
    store = SectorTemplateStore(tmp_path)

    assert not store.sector_template_exists("sector/utilities")

    store.save_sector_template(
        sector_ref="sector/utilities",
        sector_name="Utilities",
        as_of_date="2026-02-22",
        created_by="pytest",
        variable_map_patch={
            "primary_variables": [
                {
                    "name": "real_yields",
                    "category": "rates",
                    "directionality": "negative",
                    "typical_lag_days": 10,
                }
            ]
        },
        reporting_template_patch={
            "core_metrics": ["regulated_asset_base"],
            "margin_focus": [],
            "cash_flow_focus": [],
            "balance_sheet_focus": [],
        },
        validate=True,
    )

    assert store.sector_template_exists("sector/utilities")