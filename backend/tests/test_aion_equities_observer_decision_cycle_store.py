from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.observer_decision_cycle_store import (
    ObserverDecisionCycleStore,
)


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_observer_cycle(tmp_path):
    store = ObserverDecisionCycleStore(tmp_path)

    payload = store.save_cycle(
        thesis_id="thesis/AHT.L/long/2026Q2_pre_earnings",
        timestamp=_dt(2026, 2, 22, 22, 0, 0),
        process_quality_score=82.0,
        process_notes="Evidence set complete enough for pilot",
        gate_adherence=True,
        evidence_completeness=88.0,
        outcome_known=False,
        confidence_inflation_score=12.0,
        thesis_lock_in_score=18.0,
        recency_bias_score=9.0,
        catalyst_timing_error_days=0,
        collapse_timing_error_score=5.0,
        drift_warning_effective=True,
        sector_ref="sector/industrial_equipment_rental",
        false_positive_bucket=False,
        validate=True,
    )

    loaded = store.load_cycle(
        "thesis/AHT.L/long/2026Q2_pre_earnings",
        payload["observer_cycle_id"],
    )

    assert loaded["thesis_id"] == "thesis/AHT.L/long/2026Q2_pre_earnings"
    assert loaded["process_quality"]["score"] == 82.0
    assert loaded["outcome_quality"]["known"] is False
    assert loaded["bias_metrics"]["confidence_inflation_score"] == 12.0
    assert loaded["timing_metrics"]["drift_warning_effective"] is True
    assert loaded["sector_metrics"]["sector_ref"] == "sector/industrial_equipment_rental"


def test_list_cycles_for_entity(tmp_path):
    store = ObserverDecisionCycleStore(tmp_path)
    thesis_id = "thesis/AHT.L/long/2026Q2_pre_earnings"

    p1 = store.save_cycle(
        thesis_id=thesis_id,
        timestamp=_dt(2026, 2, 22, 22, 0, 0),
        process_quality_score=80.0,
        outcome_known=False,
        validate=True,
    )
    p2 = store.save_cycle(
        thesis_id=thesis_id,
        timestamp=_dt(2026, 3, 1, 9, 15, 0),
        process_quality_score=76.0,
        outcome_known=True,
        outcome_score=71.0,
        return_pct=4.2,
        timing_validity="valid",
        thesis_validity="valid",
        validate=True,
    )

    ids = store.list_cycles(thesis_id)

    assert len(ids) == 2
    assert p1["observer_cycle_id"].replace("/", "_").replace("\\", "_").replace(":", "-") in ids
    assert p2["observer_cycle_id"].replace("/", "_").replace("\\", "_").replace(":", "-") in ids


def test_cycle_exists(tmp_path):
    store = ObserverDecisionCycleStore(tmp_path)
    thesis_id = "thesis/AHT.L/long/2026Q2_pre_earnings"

    payload = store.save_cycle(
        thesis_id=thesis_id,
        timestamp=_dt(2026, 2, 22, 22, 0, 0),
        process_quality_score=79.0,
        outcome_known=False,
        validate=True,
    )

    assert store.cycle_exists(thesis_id, payload["observer_cycle_id"]) is True
    assert store.cycle_exists(thesis_id, "observer_cycle/does/not/exist") is False