from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.kg_edge_store import KGEdgeStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_kg_edge(tmp_path):
    store = KGEdgeStore(tmp_path)

    edge_id = "edge/exposure/company/AHT.L->sector/industrial_equipment_rental/2026-02-22T22:00:00Z"

    payload = store.save_kg_edge(
        edge_id=edge_id,
        src="company/AHT.L",
        dst="sector/industrial_equipment_rental",
        link_type="exposure",
        created_at=_dt(2026, 2, 22, 22, 0, 0),
        confidence=77.0,
        active=True,
        weight=0.84,
        source_event_ids=["company/AHT.L/quarter/2026-Q1"],
        validate=True,
    )

    assert payload["edge_id"] == edge_id
    assert payload["src"] == "company/AHT.L"
    assert payload["dst"] == "sector/industrial_equipment_rental"

    loaded = store.load_latest_kg_edge(edge_id)
    assert loaded["link_type"] == "exposure"
    assert loaded["active"] is True


def test_kg_edge_history_and_write_event(tmp_path):
    store = KGEdgeStore(tmp_path)

    edge_id = "edge/supports_thesis/company/AHT.L->thesis/AHT.L/long/2026Q2_pre_earnings/2026-02-22T22:00:00Z"

    p1 = store.save_kg_edge(
        edge_id=edge_id,
        src="company/AHT.L",
        dst="thesis/AHT.L/long/2026Q2_pre_earnings",
        link_type="supports_thesis",
        created_at=_dt(2026, 2, 22, 22, 0, 0),
        confidence=81.0,
        active=True,
        source_event_ids=["assessment/company_AHT.L/2026-02-22T22:00:00Z"],
        validate=True,
    )

    p2 = store.update_kg_edge(
        edge_id=edge_id,
        patch={"confidence": 88.0, "weight": 0.91},
        updated_at=_dt(2026, 3, 1, 9, 15, 0),
        validate=True,
    )

    history = store.list_kg_edge_history(edge_id)
    assert len(history) == 2

    latest = store.load_latest_kg_edge(edge_id)
    assert latest["confidence"] == 88.0
    assert latest["weight"] == 0.91
    assert latest["created_at"] == p1["created_at"]
    assert latest["updated_at"] == p2["updated_at"]

    write_events = store.load_write_events(edge_id, stage="interpretation")
    assert len(write_events) == 2
    assert write_events[0]["entity_type"] == "kg_edge"
    assert write_events[1]["operation"] == "update"


def test_kg_edge_exists_false_when_missing(tmp_path):
    store = KGEdgeStore(tmp_path)
    assert store.kg_edge_exists("edge/unknown") is False