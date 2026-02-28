from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.country_ambassador_store import CountryAmbassadorStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_country_ambassador(tmp_path):
    store = CountryAmbassadorStore(tmp_path)

    payload = store.save_country_ambassador(
        country_code="GB",
        country_name="United Kingdom",
        as_of_date=_dt(2026, 2, 22, 8, 0, 0),
        generated_by="pytest",
        country_outlook_patch={
            "score": 62.0,
            "confidence": 78.0,
            "regime": "neutral",
            "summary": "BOE hold with moderate refinancing pressure",
            "risk_flags": ["gilts_refinancing_watch"],
        },
        central_bank_patch={
            "policy_rate": 4.5,
            "policy_bias": "on_hold",
            "balance_sheet_direction": "shrinking",
        },
        sovereign_risk_patch={
            "debt_to_gdp_pct": 97.0,
            "fiscal_deficit_pct_gdp": 4.2,
            "refinancing_wall_pressure": "high",
        },
        monetary_conditions_patch={
            "money_supply_regime": "stable",
            "m2_yoy_pct": 2.1,
            "real_rate_regime": "positive_rising",
        },
        energy_profile_patch={
            "import_dependency_regime": "medium",
            "industrial_energy_cost_regime": "elevated",
        },
        credit_rating_patch={
            "composite": "AA",
            "outlook": "stable",
            "sp": "AA",
            "moodys": "Aa3",
            "fitch": "AA-",
        },
        capital_flows_patch={
            "currency_pressure": "balanced",
            "equity_flow_regime": "mixed",
            "bond_flow_regime": "outflows",
        },
        validate=True,
    )

    loaded = store.load_country_ambassador("GB")

    assert payload["country_ambassador_id"] == "country/GB"
    assert loaded["country_code"] == "GB"
    assert loaded["country_name"] == "United Kingdom"
    assert loaded["credit_rating"]["composite"] == "AA"
    assert loaded["central_bank"]["policy_rate"] == 4.5


def test_list_country_ambassadors(tmp_path):
    store = CountryAmbassadorStore(tmp_path)

    store.save_country_ambassador(
        country_code="GB",
        country_name="United Kingdom",
        as_of_date="2026-02-22",
        validate=True,
    )
    store.save_country_ambassador(
        country_code="US",
        country_name="United States",
        as_of_date="2026-02-22",
        validate=True,
    )

    ids = store.list_country_ambassadors()
    assert ids == ["GB", "US"]


def test_country_ambassador_exists(tmp_path):
    store = CountryAmbassadorStore(tmp_path)

    assert store.country_ambassador_exists("JP") is False

    store.save_country_ambassador(
        country_code="JP",
        country_name="Japan",
        as_of_date="2026-02-22",
        generated_by="pytest",
        central_bank_patch={
            "policy_rate": 0.5,
            "policy_bias": "tightening",
        },
        validate=True,
    )

    assert store.country_ambassador_exists("JP") is True