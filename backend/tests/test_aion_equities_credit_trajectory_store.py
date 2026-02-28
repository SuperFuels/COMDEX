from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.credit_trajectory_store import CreditTrajectoryStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_credit_trajectory(tmp_path):
    store = CreditTrajectoryStore(tmp_path)

    payload = store.save_credit_trajectory(
        entity_ref="company/ULVR.L",
        entity_type="company",
        as_of_date=_dt(2026, 2, 28, 9, 0, 0),
        generated_by="pytest",
        official_rating_patch={
            "composite": "A",
            "outlook": "stable",
            "sp": "A",
            "moodys": "A2",
            "fitch": "A",
        },
        shadow_rating_patch={
            "composite": "BBB+",
            "confidence": 78.0,
            "direction": "deteriorating",
            "notes": "spread widening ahead of official action",
        },
        trajectory_patch={
            "state": "downgrade_candidate",
            "downgrade_risk": 72.0,
            "upgrade_potential": 8.0,
            "watch_window_days": 90,
        },
        signals_patch={
            "leverage_signal": "neutral",
            "coverage_signal": "negative",
            "liquidity_signal": "supportive",
            "spread_signal": "widening",
            "refinancing_signal": "manageable",
        },
        linked_refs_patch={
            "assessment_refs": ["assessment/company_ULVR.L/2026-02-28T09:00:00Z"],
            "thesis_refs": ["thesis/ULVR.L/long/2026Q2_pre_earnings"],
        },
        validate=True,
    )

    assert payload["entity_ref"] == "company/ULVR.L"
    assert payload["as_of_date"] == "2026-02-28"

    loaded = store.load_credit_trajectory(
        "company/ULVR.L",
        as_of_date="2026-02-28",
    )

    assert loaded["credit_trajectory_id"] == payload["credit_trajectory_id"]
    assert loaded["trajectory"]["state"] == "downgrade_candidate"
    assert loaded["signals"]["spread_signal"] == "widening"


def test_list_credit_trajectories(tmp_path):
    store = CreditTrajectoryStore(tmp_path)

    store.save_credit_trajectory(
        entity_ref="country/GB",
        entity_type="country",
        as_of_date="2026-02-22",
        generated_by="pytest",
        validate=True,
    )

    store.save_credit_trajectory(
        entity_ref="country/GB",
        entity_type="country",
        as_of_date="2026-03-31",
        generated_by="pytest",
        validate=True,
    )

    ids = store.list_credit_trajectories("country/GB")
    assert ids == ["2026-02-22", "2026-03-31"]


def test_credit_trajectory_exists(tmp_path):
    store = CreditTrajectoryStore(tmp_path)

    assert not store.credit_trajectory_exists(
        "company/AHT.L",
        as_of_date="2026-02-28",
    )

    store.save_profile(
        entity_ref="company/AHT.L",
        entity_type="company",
        as_of_date="2026-02-28",
        generated_by="pytest",
        validate=True,
    )

    assert store.profile_exists(
        "company/AHT.L",
        as_of_date="2026-02-28",
    )