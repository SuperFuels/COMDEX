# backend/tests/test_aion_equities_builders.py
from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities import validate_payload
from backend.modules.aion_equities.builders import (
    build_assessment_payload,
    build_thesis_state_payload_minimal,
    build_kg_edge_payload,
    build_write_event_envelope,
)


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_build_assessment_payload_validates():
    payload = build_assessment_payload(
        entity_id="company/AHT.L",
        entity_type="company",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        source_event_ids=["company/AHT.L/quarter/2026-Q1"],
        risk_notes="bootstrap",
        has_active_catalyst=False,
        catalyst_count=0,
        validate=True,
    )
    validate_payload("assessment", payload, version="v0_1")


def test_build_thesis_state_payload_validates_minimal_long():
    thesis = build_thesis_state_payload_minimal(
        thesis_id="thesis/AHT.L/long/2026Q2_pre_earnings",
        ticker="AHT.L",
        mode="long",
        window="2026Q2_pre_earnings",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        assessment_refs=["assessment/company_AHT.L/2026-02-22T22:00:00Z"],
        validate=True,
    )
    validate_payload("thesis_state", thesis, version="v0_1")


def test_build_kg_edge_payload_validates():
    payload = build_kg_edge_payload(
        edge_id="edge/exposure/company/AHT.L->sector/industrial_equipment_rental/2026-02-22T22:00:00Z",
        src="company/AHT.L",
        dst="sector/industrial_equipment_rental",
        link_type="exposure",
        created_at=_dt(2026, 2, 22, 22, 0, 0),
        confidence=77.0,
        active=True,
        source_event_ids=["company/AHT.L/quarter/2026-Q1"],
        validate=True,
    )
    validate_payload("kg_edge", payload, version="v0_1")


def test_build_write_event_envelope_validates():
    assessment = build_assessment_payload(
        entity_id="company/AHT.L",
        entity_type="company",
        as_of=_dt(2026, 2, 22, 22, 0, 0),
        source_event_ids=["company/AHT.L/quarter/2026-Q1"],
        risk_notes="bootstrap",
        validate=True,
    )

    env = build_write_event_envelope(
        event_id="write_event/company/AHT.L/interpretation/2026-02-22T22:00:00Z",
        stage="interpretation",
        timestamp=_dt(2026, 2, 22, 22, 0, 0),
        entity_id="company/AHT.L",
        entity_type="company",
        operation="upsert",
        payload_schema_id="assessment",
        payload_data=assessment,
        source_kind="manual",
        source_refs=["upload:Q1_report.pdf"],
        generated_by="pytest",
        correlation_id="corr_test_1",
        validate=True,
    )
    validate_payload("write_event_envelope", env, version="v0_1")