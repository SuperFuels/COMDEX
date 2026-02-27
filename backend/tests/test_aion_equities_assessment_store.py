from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.assessment_store import AssessmentStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_latest_assessment(tmp_path):
    store = AssessmentStore(tmp_path)

    payload = store.save_assessment(
        entity_id="company/AHT.L",
        entity_type="company",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        source_event_ids=["company/AHT.L/quarter/2026-Q1"],
        risk_notes="bootstrap",
        has_active_catalyst=False,
        catalyst_count=0,
        validate=True,
    )

    latest = store.load_latest_assessment("company/AHT.L")
    assert latest["assessment_id"] == payload["assessment_id"]
    assert latest["entity_id"] == "company/AHT.L"
    assert latest["risk"]["notes"] == "bootstrap"


def test_assessment_history_and_lookup(tmp_path):
    store = AssessmentStore(tmp_path)

    p1 = store.save_assessment(
        entity_id="company/AHT.L",
        entity_type="company",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        source_event_ids=["company/AHT.L/quarter/2026-Q1"],
        risk_notes="bootstrap-1",
        has_active_catalyst=False,
        catalyst_count=0,
        validate=True,
    )

    p2 = store.save_assessment(
        entity_id="company/AHT.L",
        entity_type="company",
        as_of=_dt(2026, 5, 22, 22, 0, 0),
        source_event_ids=["company/AHT.L/quarter/2026-Q2"],
        risk_notes="bootstrap-2",
        has_active_catalyst=True,
        catalyst_count=1,
        validate=True,
    )

    ids = store.list_assessments("company/AHT.L")
    assert len(ids) == 2
    assert store.assessment_exists("company/AHT.L", p1["assessment_id"])
    assert store.assessment_exists("company/AHT.L", p2["assessment_id"])

    loaded = store.load_assessment("company/AHT.L", p1["assessment_id"])
    assert loaded["assessment_id"] == p1["assessment_id"]


def test_save_assessment_writes_interpretation_event(tmp_path):
    store = AssessmentStore(tmp_path)

    payload = store.save_assessment(
        entity_id="company/AHT.L",
        entity_type="company",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        source_event_ids=["company/AHT.L/quarter/2026-Q1"],
        risk_notes="bootstrap",
        has_active_catalyst=False,
        catalyst_count=0,
        validate=True,
    )

    events = store.load_write_events("company/AHT.L", stage="interpretation")
    assert len(events) == 1
    env = events[0]

    assert env["stage"] == "interpretation"
    assert env["payload"]["schema_id"] == "assessment"
    assert env["payload"]["data"]["assessment_id"] == payload["assessment_id"]