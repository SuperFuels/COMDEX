from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.pre_earnings_estimate_store import (
    PreEarningsEstimateStore,
)


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_pre_earnings_estimate(tmp_path):
    store = PreEarningsEstimateStore(tmp_path)

    payload = store.save_pre_earnings_estimate(
        company_ref="company/ULVR.L",
        as_of_date=_dt(2026, 4, 15, 9, 0, 0),
        next_report_date="2026-04-30",
        generated_by="pytest",
        estimate_summary_patch={
            "revenue_direction": "up",
            "margin_direction": "flat",
            "expected_quality": "beat",
            "analytical_confidence": 78.0,
            "summary": "FX improving and commodity pressure manageable.",
        },
        consensus_comparison_patch={
            "consensus_state": "above_consensus",
            "divergence_score": 66.0,
            "consensus_notes": "AION sees better reported revenue than consensus.",
        },
        driver_impacts=[
            {
                "driver": "fx_translation",
                "impact_direction": "tailwind",
                "magnitude": 82.0,
                "target_metric": "reported_numbers",
            },
            {
                "driver": "commodity_costs",
                "impact_direction": "headwind",
                "magnitude": 41.0,
                "target_metric": "gross_margin",
            },
        ],
        signal_flags=[
            "fx_tailwind",
            "consensus_gap_long",
        ],
        linked_refs_patch={
            "company_fingerprint_refs": ["company/ULVR.L/fingerprint/2026-02-28"],
            "company_profile_refs": ["company/ULVR.L/profile/2026-02-28"],
            "quarter_event_refs": ["company/ULVR.L/quarter/2025-Q4"],
            "macro_regime_refs": ["macro/regime/2026-04-15"],
        },
        validate=True,
    )

    assert payload["company_ref"] == "company/ULVR.L"
    assert payload["as_of_date"] == "2026-04-15"
    assert payload["estimate_summary"]["expected_quality"] == "beat"

    loaded = store.load_pre_earnings_estimate(
        "company/ULVR.L",
        as_of_date="2026-04-15",
    )

    assert loaded["pre_earnings_estimate_id"] == payload["pre_earnings_estimate_id"]
    assert loaded["estimate_summary"]["analytical_confidence"] == 78.0
    assert loaded["driver_impacts"][0]["driver"] == "fx_translation"
    assert loaded["consensus_state"] == "above_consensus"


def test_list_estimates(tmp_path):
    store = PreEarningsEstimateStore(tmp_path)

    store.save_pre_earnings_estimate(
        company_ref="company/AHT.L",
        as_of_date="2026-02-22",
        next_report_date="2026-03-05",
        generated_by="pytest",
        payload_patch={
            "estimate_summary": {
                "analytical_confidence": 64.0,
            }
        },
        validate=True,
    )

    store.save_pre_earnings_estimate(
        company_ref="company/AHT.L",
        as_of_date="2026-03-31",
        next_report_date="2026-04-15",
        generated_by="pytest",
        payload_patch={
            "estimate_summary": {
                "analytical_confidence": 71.0,
            }
        },
        validate=True,
    )

    ids = store.list_estimates("company/AHT.L")
    assert ids == ["2026-02-22", "2026-03-31"]


def test_estimate_exists(tmp_path):
    store = PreEarningsEstimateStore(tmp_path)

    assert not store.estimate_exists(
        "company/ULVR.L",
        as_of_date="2026-04-15",
    )

    store.save_estimate(
        company_ref="company/ULVR.L",
        as_of_date="2026-04-15",
        next_report_date="2026-04-30",
        generated_by="pytest",
        payload_patch={
            "estimate_summary": {
                "analytical_confidence": 80.0,
            }
        },
        validate=True,
    )

    assert store.estimate_exists(
        "company/ULVR.L",
        as_of_date="2026-04-15",
    )