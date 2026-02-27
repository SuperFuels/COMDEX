from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.thesis_store import ThesisStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_latest_thesis_state(tmp_path):
    store = ThesisStore(tmp_path)

    thesis_id = "thesis/AHT.L/long/2026Q2_pre_earnings"
    payload = store.save_thesis_state(
        thesis_id=thesis_id,
        ticker="AHT.L",
        mode="long",
        window="2026Q2_pre_earnings",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        assessment_refs=["assessment/company_AHT.L/2026-02-22T22:00:00Z"],
        validate=True,
    )

    latest = store.load_latest_thesis_state(thesis_id)
    assert latest["thesis_id"] == payload["thesis_id"]
    assert latest["ticker"] == "AHT.L"
    assert latest["mode"] == "long"


def test_thesis_history_and_write_event(tmp_path):
    store = ThesisStore(tmp_path)

    thesis_id = "thesis/AHT.L/long/2026Q2_pre_earnings"

    p1 = store.save_thesis_state(
        thesis_id=thesis_id,
        ticker="AHT.L",
        mode="long",
        window="2026Q2_pre_earnings",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        assessment_refs=["assessment/company_AHT.L/2026-02-22T22:00:00Z"],
        validate=True,
    )

    p2 = store.update_thesis_state(
        thesis_id=thesis_id,
        patch={"status": "ready"},
        as_of=_dt(2026, 3, 1, 9, 15, 0),
        validate=True,
    )

    history = store.list_thesis_history(thesis_id)
    assert len(history) == 2
    assert store.thesis_exists(thesis_id)

    latest = store.load_latest_thesis_state(thesis_id)
    assert latest["status"] == "ready"
    assert latest["thesis_id"] == p2["thesis_id"]

    events = store.load_write_events(thesis_id, stage="decision")
    assert len(events) == 2
    assert events[-1]["entity_type"] == "thesis_state"
    assert events[-1]["operation"] == "update"


def test_load_thesis_state_at_specific_time(tmp_path):
    store = ThesisStore(tmp_path)

    thesis_id = "thesis/AHT.L/long/2026Q2_pre_earnings"
    payload = store.save_thesis_state(
        thesis_id=thesis_id,
        ticker="AHT.L",
        mode="long",
        window="2026Q2_pre_earnings",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        assessment_refs=["assessment/company_AHT.L/2026-02-22T22:00:00Z"],
        validate=True,
    )

    loaded = store.load_thesis_state_at(thesis_id, payload["as_of"])
    assert loaded["thesis_id"] == thesis_id
    assert loaded["status"] == payload["status"]