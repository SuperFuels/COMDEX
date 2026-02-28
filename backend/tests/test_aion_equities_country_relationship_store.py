from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.country_relationship_store import CountryRelationshipStore
from backend.modules.aion_equities.schema_validate import validate_payload


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_country_relationship(tmp_path):
    store = CountryRelationshipStore(tmp_path)

    payload = store.save_country_relationship(
        lhs_country_code="US",
        rhs_country_code="DE",
        as_of_date=_dt(2026, 2, 22, 8, 0, 0),
        generated_by="pytest",
        relationship_score_patch={
            "score": 42.0,
            "confidence": 78.0,
            "regime": "fragile",
            "summary": "Tariff and rates divergence pressure.",
        },
        relationship_drift_patch={
            "direction": "deteriorating",
            "velocity": "moderate",
        },
        trade_policy_patch={
            "tariff_regime": "friction",
            "trade_alignment": "strained",
            "export_dependency_regime": "high",
        },
        geopolitics_patch={
            "alignment_regime": "mixed",
            "policy_coordination": "limited",
        },
        yield_differential_patch={
            "front_end_bps": 125.0,
            "long_end_bps": 95.0,
            "carry_regime": "lhs_supportive",
        },
        capital_flows_patch={
            "pair_flow_regime": "lhs_inflow",
            "funding_stress_regime": "watch",
        },
        risk_flags=["tariff_risk", "yield_gap_wide"],
        validate=True,
    )

    validate_payload("country_relationship", payload, version="v0_1")

    loaded = store.load_country_relationship("US", "DE")
    assert loaded["country_relationship_id"] == "country_relationship/US-DE"
    assert loaded["lhs_country_ref"] == "country/US"
    assert loaded["rhs_country_ref"] == "country/DE"
    assert loaded["relationship_score"]["regime"] == "fragile"
    assert loaded["yield_differential"]["carry_regime"] == "lhs_supportive"


def test_list_country_relationships(tmp_path):
    store = CountryRelationshipStore(tmp_path)

    store.save_country_relationship(
        lhs_country_code="US",
        rhs_country_code="DE",
        as_of_date="2026-02-22",
        validate=True,
    )
    store.save_country_relationship(
        lhs_country_code="US",
        rhs_country_code="JP",
        as_of_date="2026-02-22",
        validate=True,
    )

    ids = store.list_country_relationships()
    assert "country_relationship_US-DE" in ids
    assert "country_relationship_US-JP" in ids


def test_country_relationship_exists(tmp_path):
    store = CountryRelationshipStore(tmp_path)

    assert not store.country_relationship_exists("US", "GB")

    store.save_country_relationship(
        lhs_country_code="US",
        rhs_country_code="GB",
        as_of_date="2026-02-22",
        validate=True,
    )

    assert store.country_relationship_exists("US", "GB")