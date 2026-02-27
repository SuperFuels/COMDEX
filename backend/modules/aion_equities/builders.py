# backend/modules/aion_equities/builders.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.modules.aion_equities.constants import (
    ALLOWED_THESIS_MODES,
    PAYLOAD_VERSION,
    SCHEMA_PACK_VERSION,
)
from backend.modules.aion_equities.schema_validate import validate_payload


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------
def _iso_z(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _date_only(value: Any) -> str:
    if isinstance(value, str):
        return value[:10]
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    raise ValueError(f"Unsupported date value: {value!r}")


def _assessment_id_from_entity(entity_id: str, as_of: str) -> str:
    # schema wants:
    # assessment/<entity-token>/<YYYY-MM-DDT...>
    entity_token = entity_id.replace("/", "_")
    return f"assessment/{entity_token}/{as_of}"


def _default_scored_component(value: float, confidence: float, note: str | None = None) -> Dict[str, Any]:
    obj: Dict[str, Any] = {
        "value": float(value),
        "confidence": float(confidence),
    }
    if note:
        obj["note"] = note
    return obj


def _default_assessment_blocks(
    *,
    risk_notes: str = "bootstrap",
    has_active_catalyst: bool = False,
    catalyst_count: int = 0,
    next_catalyst_date: Optional[str] = None,
    catalyst_types: Optional[List[str]] = None,
    timing_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    bqs = {
        "score": 72.0,
        "scale": "0-100",
        "components": {
            "revenue_trajectory_quality": _default_scored_component(72.0, 70.0),
            "margin_direction_resilience": _default_scored_component(68.0, 67.0),
            "fcf_generation_quality": _default_scored_component(70.0, 66.0),
            "balance_sheet_strength": _default_scored_component(74.0, 71.0),
            "debt_maturity_refinancing_risk": {
                **_default_scored_component(28.0, 64.0),
                "interpretation": "higher_value_means_higher_risk",
            },
            "interest_coverage_quality": _default_scored_component(76.0, 70.0),
            "moat_durability": _default_scored_component(69.0, 63.0),
            "management_credibility_guidance_accuracy": _default_scored_component(67.0, 64.0),
            "capital_allocation_discipline": _default_scored_component(66.0, 62.0),
        },
        "summary": "Bootstrap BQS payload.",
    }

    acs = {
        "score": 75.0,
        "scale": "0-100",
        "components": {
            "public_data_clarity": _default_scored_component(82.0, 75.0),
            "reporting_consistency": _default_scored_component(79.0, 73.0),
            "earnings_predictability": _default_scored_component(71.0, 68.0),
            "commodity_input_opacity": {
                **_default_scored_component(24.0, 60.0),
                "interpretation": "higher_value_means_higher_risk",
            },
            "hedging_book_opacity": {
                **_default_scored_component(18.0, 58.0),
                "interpretation": "higher_value_means_higher_risk",
            },
            "regulatory_complexity": {
                **_default_scored_component(21.0, 59.0),
                "interpretation": "higher_value_means_higher_risk",
            },
            "segment_complexity": {
                **_default_scored_component(34.0, 61.0),
                "interpretation": "higher_value_means_higher_risk",
            },
            "narrative_coherence": _default_scored_component(78.0, 72.0),
            "historical_model_error_stability": _default_scored_component(73.0, 69.0),
        },
        "summary": "Bootstrap ACS payload.",
    }

    aot = {
        "automation_beneficiary_score": 58.0,
        "automation_threat_score": 31.0,
        "signals": {
            "estimated_automatable_cost_base_pct": 22.0,
            "capex_ability_to_automate": _default_scored_component(55.0, 60.0),
            "management_execution_credibility": _default_scored_component(55.0, 58.0),
            "debt_blocks_transition": {
                **_default_scored_component(20.0, 63.0),
                "interpretation": "higher_value_means_higher_risk",
            },
            "customer_substitution_risk": {
                **_default_scored_component(25.0, 61.0),
                "interpretation": "higher_value_means_higher_risk",
            },
            "sector_ai_adoption_pace": _default_scored_component(50.0, 57.0),
        },
        "summary": "Bootstrap AOT payload.",
    }

    catalyst: Dict[str, Any] = {
        "has_active_catalyst": bool(has_active_catalyst),
        "catalyst_count": int(catalyst_count),
    }
    if next_catalyst_date is not None:
        catalyst["next_catalyst_date"] = next_catalyst_date
    if catalyst_types:
        catalyst["catalyst_types"] = list(catalyst_types)
    if timing_confidence is not None:
        catalyst["timing_confidence"] = float(timing_confidence)

    risk = {
        "analytical_confidence_gate_pass": True,
        "short_requires_catalyst": True,
        "borrow_cost_estimate_annualized_pct": 0.0,
        "position_risk_flags": [],
        "notes": str(risk_notes),
    }

    return {
        "bqs": bqs,
        "acs": acs,
        "aot": aot,
        "risk": risk,
        "catalyst": catalyst,
    }


# ---------------------------------------------------------------------
# public builders
# ---------------------------------------------------------------------
def build_assessment_payload(
    *,
    entity_id: str,
    entity_type: str,
    as_of: Any,
    source_event_ids: List[str],
    risk_notes: str = "bootstrap",
    has_active_catalyst: bool = False,
    catalyst_count: int = 0,
    next_catalyst_date: Optional[str] = None,
    catalyst_types: Optional[List[str]] = None,
    timing_confidence: Optional[float] = None,
    source_hashes: Optional[List[str]] = None,
    generated_by: str = "aion_equities.builders",
    validate: bool = True,
) -> Dict[str, Any]:
    as_of_s = _iso_z(as_of)

    blocks = _default_assessment_blocks(
        risk_notes=risk_notes,
        has_active_catalyst=has_active_catalyst,
        catalyst_count=catalyst_count,
        next_catalyst_date=next_catalyst_date,
        catalyst_types=catalyst_types,
        timing_confidence=timing_confidence,
    )

    payload: Dict[str, Any] = {
        "assessment_id": _assessment_id_from_entity(entity_id, as_of_s),
        "entity_id": entity_id,
        "entity_type": entity_type,
        "as_of": as_of_s,
        "version": PAYLOAD_VERSION,
        "bqs": blocks["bqs"],
        "acs": blocks["acs"],
        "aot": blocks["aot"],
        "risk": blocks["risk"],
        "catalyst": blocks["catalyst"],
        "provenance": {
            "source_event_ids": list(source_event_ids),
            "source_hashes": list(source_hashes or []),
            "generated_by": generated_by,
            "generated_at": as_of_s,
        },
    }

    if validate:
        validate_payload("assessment", payload, version=SCHEMA_PACK_VERSION)
    return payload


def build_thesis_state_payload_minimal(
    *,
    thesis_id: str,
    ticker: str,
    mode: str,
    window: str,
    as_of: Any,
    assessment_refs: List[str],
    generated_by: str = "aion_equities.builders",
    validate: bool = True,
) -> Dict[str, Any]:
    if mode not in ALLOWED_THESIS_MODES:
        raise ValueError(f"Invalid thesis mode: {mode!r}")

    as_of_s = _iso_z(as_of)

    payload: Dict[str, Any] = {
        "thesis_id": thesis_id,
        "ticker": ticker,
        "mode": mode,
        "window": window,
        "status": "candidate",
        "as_of": as_of_s,
        "superposition": [
            {
                "candidate_id": "long_base",
                "label": "long" if mode in {"long", "catalyst_long"} else ("short" if mode in {"short", "swing_short"} else "neutral"),
                "probability_mass_hint": 0.5,
                "expected_move_direction": "up" if mode in {"long", "catalyst_long"} else ("down" if mode in {"short", "swing_short"} else "flat"),
                "note": "Bootstrap thesis candidate",
            },
            {
                "candidate_id": "neutral_wait",
                "label": "neutral",
                "probability_mass_hint": 0.5,
                "expected_move_direction": "flat",
                "note": "Fallback neutral candidate",
            },
        ],
        "selected_candidate_id": "long_base" if mode in {"long", "catalyst_long"} else ("neutral_wait" if mode == "neutral_watch" else "long_base"),
        "assessment_refs": list(assessment_refs),
        "evidence_links": [],
        "catalyst": {
            "required": mode in {"short", "swing_short", "catalyst_long"},
            "present": False,
            "timing_confidence": 0.0,
        },
        "borrow": {
            "required": mode in {"short", "swing_short"},
            "borrow_cost_estimate_annualized_pct": 0.0,
            "locate_status": "unknown",
        },
        "sizing_proposal": {
            "unit_type": "capital_pct",
            "proposed_size": 0.0,
            "max_size": 0.0,
            "stop_logic": "bootstrap_placeholder",
            "target_logic": "bootstrap_placeholder",
        },
        "sqi": {
            "coherence_score": 50.0,
            "drift_score": 10.0,
            "contradiction_pressure": 5.0,
            "stability_score": 50.0,
            "collapse_readiness_score": 0.0,
            "trace_ids": [],
        },
        "policy_gate": {
            "bqs_pass": False,
            "acs_pass": False,
            "sqi_coherence_pass": False,
            "drift_pass": True,
            "contradiction_pass": True,
            "catalyst_pass": mode not in {"short", "swing_short", "catalyst_long"},
            "risk_invariants_pass": True,
            "ready_for_action": False,
            "reasons": ["bootstrap_placeholder"],
        },
        "risk_invariants": {
            "version": PAYLOAD_VERSION,
        },
        "invalidation_conditions": [
            {
                "id": "time_window_expired",
                "condition_type": "time",
                "rule": "Thesis invalidates when review window expires without confirmation.",
                "severity": "warn",
            }
        ],
        "collapse": {
            "collapsed": False,
        },
        "audit": {
            "created_at": as_of_s,
            "updated_at": as_of_s,
            "created_by": generated_by,
            "updated_by": generated_by,
            "write_stage_refs": [],
        },
    }

    if validate:
        validate_payload("thesis_state", payload, version=SCHEMA_PACK_VERSION)
    return payload


def build_kg_edge_payload(
    *,
    edge_id: str,
    src: str,
    dst: str,
    link_type: str,
    created_at: Any,
    confidence: float,
    active: bool,
    source_event_ids: List[str],
    weight: Optional[float] = None,
    source_hashes: Optional[List[str]] = None,
    generated_by: str = "aion_equities.builders",
    validate: bool = True,
) -> Dict[str, Any]:
    created_at_s = _iso_z(created_at)

    payload: Dict[str, Any] = {
        "edge_id": edge_id,
        "src": src,
        "dst": dst,
        "link_type": link_type,
        "created_at": created_at_s,
        "confidence": float(confidence),
        "active": bool(active),
        "provenance": {
            "source_event_ids": list(source_event_ids),
            "source_hashes": list(source_hashes or []),
            "generated_by": generated_by,
        },
    }

    if weight is not None:
        payload["weight"] = float(weight)

    if validate:
        validate_payload("kg_edge", payload, version=SCHEMA_PACK_VERSION)
    return payload


def build_write_event_envelope(
    *,
    event_id: str,
    stage: str,
    timestamp: Any,
    entity_id: str,
    entity_type: str,
    operation: str,
    payload_schema_id: str,
    payload_data: Dict[str, Any],
    source_kind: str,
    source_refs: List[str],
    generated_by: str,
    correlation_id: str,
    source_hashes: Optional[List[str]] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    timestamp_s = _iso_z(timestamp)

    payload: Dict[str, Any] = {
        "event_id": event_id,
        "stage": stage,
        "timestamp": timestamp_s,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "operation": operation,
        "payload": {
            "schema_id": payload_schema_id,
            "data": payload_data,
        },
        "provenance": {
            "source_kind": source_kind,
            "source_refs": list(source_refs),
            "source_hashes": list(source_hashes or []),
            "generated_by": generated_by,
        },
        "trace": {
            "correlation_id": correlation_id,
        },
    }

    if validate:
        validate_payload("write_event_envelope", payload, version=SCHEMA_PACK_VERSION)
    return payload