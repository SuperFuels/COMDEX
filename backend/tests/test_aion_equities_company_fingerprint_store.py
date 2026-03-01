from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.company_fingerprint_store import (
    CompanyFingerprintStore,
)


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_company_fingerprint(tmp_path):
    store = CompanyFingerprintStore(tmp_path)

    payload = store.save_company_fingerprint(
        company_ref="company/ULVR.L",
        as_of_date=_dt(2026, 2, 28, 9, 0, 0),
        generated_by="pytest",
        recurring_business_drivers=[
            {"name": "fx_translation", "importance": "primary"},
            {"name": "commodity_costs", "importance": "primary"},
            {"name": "brand_investment", "importance": "secondary"},
        ],
        management_guidance_events=[
            {
                "date": "2026-02-12",
                "event": "fy_results",
                "signal": "cautious_but_credible",
            }
        ],
        lag_structure_patch={
            "default_lag_days": 45,
            "driver_lags": [
                {"driver": "fx_translation", "lag_days": 30},
                {"driver": "commodity_costs", "lag_days": 60},
            ],
        },
        sensitivity_patch={
            "sensitivity_coefficients": [
                {"driver": "fx_translation", "coefficient": 0.8},
                {"driver": "commodity_costs", "coefficient": -0.6},
            ]
        },
        guidance_profile_patch={
            "guidance_style": "conservative",
            "credibility": "high",
            "bias_direction": "slightly_underpromise",
        },
        fingerprint_summary_patch={
            "analytical_confidence": 78.0,
            "predictability_regime": "medium_high",
            "key_watch_items": ["latin_america_volume", "eur_em_fx"],
            "summary": "Stable consumer staples fingerprint with material FX sensitivity.",
        },
        linked_refs_patch={
            "sector_template_refs": ["sector/consumer_staples/template/core"],
            "quarter_event_refs": ["company/ULVR.L/quarter/2025-Q4"],
            "structural_profile_refs": ["company/ULVR.L/profile/2026-02-28"],
        },
        validate=True,
    )

    assert payload["company_ref"] == "company/ULVR.L"
    assert payload["as_of_date"] == "2026-02-28"

    loaded = store.load_company_fingerprint(
        "company/ULVR.L",
        as_of_date="2026-02-28",
    )

    assert loaded["company_fingerprint_id"] == payload["company_fingerprint_id"]
    assert loaded["driver_map"]["primary_drivers"] == ["fx_translation", "commodity_costs"]
    assert loaded["guidance_profile"]["credibility"] == "high"
    assert loaded["fingerprint_summary"]["analytical_confidence"] == 78.0


def test_list_fingerprints(tmp_path):
    store = CompanyFingerprintStore(tmp_path)

    store.save_company_fingerprint(
        company_ref="company/AHT.L",
        as_of_date="2026-02-22",
        generated_by="pytest",
        payload_patch={
            "fingerprint_summary": {
                "analytical_confidence": 64.0,
            }
        },
        validate=True,
    )

    store.save_company_fingerprint(
        company_ref="company/AHT.L",
        as_of_date="2026-03-31",
        generated_by="pytest",
        payload_patch={
            "fingerprint_summary": {
                "analytical_confidence": 71.0,
            }
        },
        validate=True,
    )

    ids = store.list_fingerprints("company/AHT.L")
    assert ids == ["2026-02-22", "2026-03-31"]


def test_fingerprint_exists(tmp_path):
    store = CompanyFingerprintStore(tmp_path)

    assert not store.fingerprint_exists(
        "company/ULVR.L",
        as_of_date="2026-02-28",
    )

    store.save_fingerprint(
        company_ref="company/ULVR.L",
        as_of_date="2026-02-28",
        generated_by="pytest",
        payload_patch={
            "fingerprint_summary": {
                "analytical_confidence": 80.0,
            }
        },
        validate=True,
    )

    assert store.fingerprint_exists(
        "company/ULVR.L",
        as_of_date="2026-02-28",
    )