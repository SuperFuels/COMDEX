# /workspaces/COMDEX/backend/tests/test_aion_equities_quarter_event_store.py
from __future__ import annotations

from backend.modules.aion_equities.quarter_event_store import QuarterEventStore


def test_quarter_event_store_save_load_and_list(tmp_path):
    store = QuarterEventStore(base_dir=tmp_path)

    saved = store.save_quarter_event(
        company_ref="company/AHT.L",
        document_ref="document/AHT.L/2026-Q1",
        thesis_ref="thesis/AHT.L/long/2026Q2_pre_earnings",
        quarter_event={
            "fiscal_period": "2026-Q1",
            "published_at": "2026-06-18",
            "headline": "Q1 update",
            "summary": "Trading in line",
            "key_numbers": {"revenue_growth_pct": 8.2},
            "source_document_ref": "document/AHT.L/2026-Q1",
        },
    )

    assert saved["quarter_event_id"] == "quarter_event/company/AHT.L/2026-Q1"
    assert saved["company_ref"] == "company/AHT.L"
    assert saved["fiscal_period"] == "2026-Q1"

    loaded = store.load_quarter_event("quarter_event/company/AHT.L/2026-Q1")
    assert loaded["headline"] == "Q1 update"
    assert loaded["key_numbers"]["revenue_growth_pct"] == 8.2

    listed = store.list_quarter_events()
    assert "quarter_event/company/AHT.L/2026-Q1" in listed


def test_quarter_event_store_accepts_payload_alias(tmp_path):
    store = QuarterEventStore(base_dir=tmp_path)

    saved = store.save_quarter_event(
        company_ref="company/TSCO.L",
        payload={
            "document_ref": "document/TSCO.L/2026-Q1",
            "fiscal_period": "2026-Q1",
            "headline": "Stable quarter",
            "summary": "Defensive trading held up",
            "key_numbers": {"like_for_like_sales_pct": 3.1},
        },
    )

    assert saved["quarter_event_id"] == "quarter_event/company/TSCO.L/2026-Q1"
    assert saved["payload"]["headline"] == "Stable quarter"