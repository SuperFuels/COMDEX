# backend/tests/test_aion_equities_quarter_event_store.py
from __future__ import annotations

from backend.modules.aion_equities.quarter_event_store import QuarterEventStore


def test_save_and_load_quarter_event(tmp_path):
    store = QuarterEventStore(tmp_path)

    payload = store.save_quarter_event(
        ticker="AHT.L",
        year=2026,
        quarter=1,
        filing_date="2026-02-22",
        period_end_date="2026-01-31",
        company_ref="company/AHT.L",
        source_document_refs=["doc/aht_q1_2026.pdf"],
        extracted_table_refs=["table/aht_q1_2026_income"],
        narrative_ref="narrative/aht_q1_2026",
        assessment_ref="assessment/company_AHT.L/2026-02-22T22:00:00Z",
        validate=True,
    )

    loaded = store.load_quarter_event(payload["quarter_event_id"])
    assert loaded["quarter_event_id"] == payload["quarter_event_id"]
    assert loaded["company_ref"] == "company/AHT.L"
    assert loaded["company_ref"] == "company/AHT.L"
    assert loaded["quarter_event_id"] == "company/AHT.L/quarter/2026-Q1"


def test_list_quarter_events_for_company(tmp_path):
    store = QuarterEventStore(tmp_path)

    p1 = store.save_quarter_event(
        ticker="AHT.L",
        year=2026,
        quarter=1,
        filing_date="2026-02-22",
        period_end_date="2026-01-31",
        company_ref="company/AHT.L",
        validate=True,
    )
    p2 = store.save_quarter_event(
        ticker="AHT.L",
        year=2026,
        quarter=2,
        filing_date="2026-05-22",
        period_end_date="2026-04-30",
        company_ref="company/AHT.L",
        validate=True,
    )

    ids = store.list_quarter_events("company/AHT.L")
    assert p1["quarter_event_id"] in ids
    assert p2["quarter_event_id"] in ids
    assert len(ids) == 2


def test_quarter_event_exists(tmp_path):
    store = QuarterEventStore(tmp_path)

    payload = store.save_quarter_event(
        ticker="AHT.L",
        year=2026,
        quarter=1,
        filing_date="2026-02-22",
        period_end_date="2026-01-31",
        company_ref="company/AHT.L",
        validate=True,
    )

    assert store.quarter_event_exists(payload["quarter_event_id"]) is True