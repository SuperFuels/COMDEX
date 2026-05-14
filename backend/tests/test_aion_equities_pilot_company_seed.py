from __future__ import annotations

from backend.modules.aion_equities.pilot_company_seed import (
    PilotCompanySeedStore,
    build_pilot_company_seed_payload,
)


def test_build_pilot_company_seed_payload_defaults():
    payload = build_pilot_company_seed_payload(generated_by="pytest")

    assert payload["pilot_seed_id"] == "pilot_company_seed/default"
    assert len(payload["companies"]) >= 10
    assert payload["audit"]["created_by"] == "pytest"

    tickers = {c["ticker"] for c in payload["companies"]}
    assert "ULVR.L" in tickers
    assert "AHT.L" in tickers
    assert "PAGE.L" in tickers

    page = next(c for c in payload["companies"] if c["ticker"] == "PAGE.L")
    assert page["sector_template_ref"] == "sector_template/staffing_recruitment"
    assert page["default_trigger_profile"] == "staffing_employment_confidence"
    assert "country/FR" in page["country_context_refs"]


def test_save_and_load_pilot_company_seed(tmp_path):
    store = PilotCompanySeedStore(tmp_path)

    saved = store.save_seed(generated_by="pytest")
    assert store.exists()

    loaded = store.load_seed()
    assert loaded["pilot_seed_id"] == saved["pilot_seed_id"]
    assert len(loaded["companies"]) == len(saved["companies"])

    tickers = store.tickers()
    assert "ULVR.L" in tickers
    assert "PSN.L" in tickers
    assert "PAGE.L" in tickers


def test_get_company_returns_expected_hooks(tmp_path):
    store = PilotCompanySeedStore(tmp_path)
    store.save_seed(generated_by="pytest")

    company = store.get_company("AHT.L")

    assert company["ticker"] == "AHT.L"
    assert company["sector_name"] == "industrial_equipment_rental"
    assert company["fingerprint_ref"] == "company/AHT.L/fingerprint/latest"
    assert company["credit_ref"] == "company/AHT.L/credit/latest"
    assert company["next_expected_report_window"] == "2026Q2_pre_earnings"


def test_save_seed_allows_company_override(tmp_path):
    store = PilotCompanySeedStore(tmp_path)

    store.save_seed(
        generated_by="pytest",
        companies_patch=[
            {
                "ticker": "TEST.L",
                "name": "Test Plc",
                "exchange": "LSE",
                "currency": "GBP",
                "sector_name": "test_sector",
                "industry": "Test Industry",
                "country": "GB",
                "company_status": "active",
                "acs_band": "high",
                "sector_confidence_tier": "tier_1",
                "pilot_priority": 1,
                "pilot_bucket": "test_bucket",
                "sector_template_ref": "sector_template/test_sector",
                "fingerprint_ref": "company/TEST.L/fingerprint/latest",
                "credit_ref": "company/TEST.L/credit/latest",
                "pair_context_refs": [],
                "country_context_refs": ["country/GB"],
                "default_trigger_profile": "test_profile",
                "next_expected_report_window": "2026Q2_pre_earnings",
                "notes": "test",
            }
        ],
    )

    tickers = store.tickers()
    assert tickers == ["TEST.L"]

    company = store.get_company("TEST.L")
    assert company["default_trigger_profile"] == "test_profile"