from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.catalyst_event_store import CatalystEventStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_catalyst_event(tmp_path):
    store = CatalystEventStore(tmp_path)

    payload = store.save_catalyst_event(
        ticker="AHT.L",
        event_id="earnings_2026-06-18",
        catalyst_type="earnings",
        status="scheduled",
        expected_date="2026-06-18",
        timing_confidence=82.0,
        thesis_refs=["thesis/AHT.L/long/2026Q2_pre_earnings"],
        importance=75.0,
        details={"headline": "Q2 earnings", "description": "Expected quarterly results"},
        source_refs=["calendar:lse"],
        validate=True,
    )

    loaded = store.load_catalyst_event(payload["catalyst_event_id"])

    assert payload["catalyst_event_id"] == "company/AHT.L/catalyst/earnings_2026-06-18"
    assert loaded["company_ref"] == "company/AHT.L"
    assert loaded["catalyst_type"] == "earnings"
    assert loaded["expected_date"] == "2026-06-18"


def test_list_catalyst_events_for_company(tmp_path):
    store = CatalystEventStore(tmp_path)

    p1 = store.save_catalyst_event(
        ticker="AHT.L",
        event_id="earnings_2026-06-18",
        catalyst_type="earnings",
        status="scheduled",
        expected_date="2026-06-18",
        timing_confidence=80.0,
        thesis_refs=[],
        source_refs=["calendar:lse"],
        validate=True,
    )

    p2 = store.save_catalyst_event(
        ticker="AHT.L",
        event_id="agm_2026-07-10",
        catalyst_type="agm",
        status="monitoring",
        expected_date="2026-07-10",
        timing_confidence=65.0,
        thesis_refs=[],
        source_refs=["company:ir"],
        validate=True,
    )

    ids = store.list_catalyst_events("company/AHT.L")

    assert p1["catalyst_event_id"] in ids
    assert p2["catalyst_event_id"] in ids
    assert len(ids) == 2


def test_catalyst_event_exists(tmp_path):
    store = CatalystEventStore(tmp_path)

    payload = store.save_catalyst_event(
        ticker="AHT.L",
        event_id="debt_refi_2026-q3",
        catalyst_type="debt_refinancing",
        status="monitoring",
        expected_date="2026-09-30",
        timing_confidence=71.0,
        thesis_refs=["thesis/AHT.L/short/2026Q3_refi"],
        source_refs=["debt:note"],
        validate=True,
    )

    assert store.catalyst_event_exists(payload["catalyst_event_id"]) is True
    assert store.catalyst_event_exists("company/AHT.L/catalyst/missing") is False