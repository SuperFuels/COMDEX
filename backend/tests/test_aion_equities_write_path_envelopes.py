# backend/tests/test_aion_equities_write_path_envelopes.py

from __future__ import annotations

from backend.modules.aion_equities.investing_ids import (
    company_id,
    thesis_id,
)
from backend.modules.aion_equities.writers import (
    build_company_record,
    build_thesis_state_record,
    build_kg_edge_record,
)
from backend.modules.aion_equities.write_envelopes import (
    make_ingestion_event,
    make_interpretation_event,
    make_decision_event,
    make_outcome_event,
)


def test_write_path_envelope_builders_smoke():
    # 1) Company record (ingestion stage)
    comp = build_company_record(
        ticker="AHT.L",
        name="Ashtead Group plc",
        primary_listing_exchange="LSE",
        country="GB",
        sector="industrial_equipment_rental",
        industry="equipment_rental",
        currency="GBP",
        # validate=False for now until schema is fully aligned to exact required fields
        validate=False,
    )

    assert comp["company_id"] == "company/AHT.L"
    assert comp["ticker"] == "AHT.L"

    comp_env = make_ingestion_event(
        entity_kind="company",
        entity_id=comp["company_id"],
        payload=comp,
        source_type="manual_seed",
        source_ref="seed://ftse10/aht",
        validate=False,  # turn on once envelope schema + payload shape fully aligned
    )

    assert comp_env["stage"] == "ingestion"
    assert comp_env["entity_kind"] == "company"
    assert comp_env["entity_id"] == "company/AHT.L"
    assert comp_env["payload"]["name"] == "Ashtead Group plc"
    assert comp_env["source"]["source_type"] == "manual_seed"

    # 2) Assessment payload (interpretation stage) - using the user's sample style
    assessment = {
        "schema_version": "v0.1.0",
        "assessment_id": "assessment/AHT.L/2026Q1",
        "entity_id": company_id("AHT.L"),
        "as_of": "2026-02-22T22:00:00Z",
        "bqs": {
            "score": 0.78,
            "components": {
                "revenue_trajectory_quality": {"value": 0.75, "confidence": 0.8},
                "margin_direction_resilience": {"value": 0.72, "confidence": 0.7},
            },
        },
        "acs": {
            "score": 0.83,
            "components": {
                "narrative_coherence": {"value": 0.81, "confidence": 0.76},
                "historical_model_error_stability": {"value": 0.79, "confidence": 0.74},
                "regulatory_complexity": {"value": 0.20, "confidence": 0.6},
            },
        },
        "aot": {
            "automation_beneficiary_score": 0.66,
            "automation_threat_score": 0.28,
            "signals": {
                "management_execution_credibility": {"value": 0.77, "confidence": 0.7},
                "debt_blocks_transition": {"value": 0.15, "confidence": 0.8},
            },
        },
        "risk": {
            "analytical_confidence_gate_pass": True,
            "borrow_cost_estimate_annualized_pct": 1.25,
            "position_risk_flags": [],
        },
        "catalyst": {
            "has_active_catalyst": True,
            "next_catalyst_date": "2026-06-18",
            "timing_confidence": 0.71,
            "catalyst_types": ["earnings"],
        },
    }

    assessment_env = make_interpretation_event(
        entity_kind="assessment",
        entity_id=assessment["assessment_id"],
        payload=assessment,
        source_type="aion_assessment_builder",
        source_ref="company/AHT.L/quarter/2026-Q1",
        validate=False,
    )

    assert assessment_env["stage"] == "interpretation"
    assert assessment_env["entity_kind"] == "assessment"
    assert assessment_env["payload"]["acs"]["score"] == 0.83

    # 3) Thesis state (decision stage)
    tid = thesis_id("AHT.L", "long", "2026Q2_pre_earnings")
    thesis = build_thesis_state_record(
        thesis_id=tid,
        entity_id=company_id("AHT.L"),
        mode="long",
        window="2026Q2_pre_earnings",
        as_of="2026-02-22T22:00:00Z",
        superposition_candidates=[
            {"label": "long", "coherence": 0.74},
            {"label": "neutral_watch", "coherence": 0.21},
            {"label": "short", "coherence": 0.05},
        ],
        collapse_readiness={
            "bqs_pass": True,
            "acs_pass": True,
            "sqi_coherence_pass": True,
            "drift_pass": True,
            "contradiction_pressure_pass": True,
            "policy_gate_pass": True,
        },
        sqi={
            "coherence": 0.74,
            "drift": 0.12,
            "contradiction_pressure": 0.18,
            "stability": 0.67,
        },
        validate=False,
    )

    decision_env = make_decision_event(
        entity_kind="thesis_state",
        entity_id=thesis["thesis_id"],
        payload=thesis,
        source_type="aion_thesis_runtime",
        source_ref=assessment["assessment_id"],
        validate=False,
    )

    assert decision_env["stage"] == "decision"
    assert decision_env["entity_kind"] == "thesis_state"
    assert decision_env["payload"]["thesis_id"] == tid
    assert decision_env["payload"]["collapse_readiness"]["policy_gate_pass"] is True

    # 4) KG edge (outcome stage example, for trace linkage)
    edge = build_kg_edge_record(
        src_id=assessment["assessment_id"],
        dst_id=tid,
        edge_type="supports_thesis",
        confidence=0.84,
        weight=0.62,
        validate=False,
    )

    assert edge["edge_type"] == "supports_thesis"
    assert edge["src_id"] == assessment["assessment_id"]
    assert edge["dst_id"] == tid

    outcome_payload = {
        "schema_version": "v0.1.0",
        "outcome_id": "outcome/AHT.L/2026-06-18/post_earnings",
        "thesis_id": tid,
        "market_move_pct_1d": 4.2,
        "process_quality": "good",
        "outcome_quality": "good",
        "timing_validity": True,
        "thesis_validity": True,
        "linked_edges": [edge["edge_id"]],
    }

    outcome_env = make_outcome_event(
        entity_kind="outcome_review",
        entity_id=outcome_payload["outcome_id"],
        payload=outcome_payload,
        source_type="post_event_review",
        source_ref="company/AHT.L/earnings/2026-06-18",
        validate=False,
    )

    assert outcome_env["stage"] == "outcome"
    assert outcome_env["entity_kind"] == "outcome_review"
    assert outcome_env["payload"]["timing_validity"] is True

    # Shared envelope invariants
    for env in (comp_env, assessment_env, decision_env, outcome_env):
        assert env["event_type"] == "aion_equities.write_event"
        assert "event_id" in env and env["event_id"]
        assert "ts" in env and env["ts"].endswith("Z")
        assert "payload" in env and isinstance(env["payload"], dict)