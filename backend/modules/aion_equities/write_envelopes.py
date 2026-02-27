# backend/modules/aion_equities/write_envelopes.py

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import uuid

# Optional imports: keep this module usable even if package exports evolve
try:
    from backend.modules.aion_equities import validate_payload
except Exception:  # pragma: no cover
    validate_payload = None  # type: ignore


__all__ = [
    "utc_now_iso",
    "make_write_event_envelope",
    "make_ingestion_event",
    "make_interpretation_event",
    "make_decision_event",
    "make_outcome_event",
]


_ALLOWED_STAGES = {"ingestion", "interpretation", "decision", "outcome"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _deepcopyish(x: Any) -> Any:
    # For our use (dict/list/primitive payloads) this is enough and avoids importing copy.
    if isinstance(x, dict):
        return {k: _deepcopyish(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_deepcopyish(v) for v in x]
    return x


def make_write_event_envelope(
    *,
    stage: str,
    entity_kind: str,
    entity_id: str,
    payload: Dict[str, Any],
    source_type: str,
    source_ref: Optional[str] = None,
    schema_version: str = "v0.1.0",
    event_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    ts: Optional[str] = None,
    actor: str = "aion_equities",
    tags: Optional[list[str]] = None,
    validate: bool = False,
) -> Dict[str, Any]:
    """
    Canonical write-event envelope for the 4-stage write path.

    Schema intent (v0.1):
      - stage ∈ {ingestion, interpretation, decision, outcome}
      - entity_kind identifies payload class (company, assessment, thesis_state, kg_edge, etc.)
      - entity_id is canonical container/KG identifier
      - payload is the actual record body (already schema-conformant to its own schema)
      - source metadata preserves provenance
    """
    stage_n = str(stage).strip().lower()
    if stage_n not in _ALLOWED_STAGES:
        raise ValueError(f"Invalid stage '{stage}'. Allowed: {sorted(_ALLOWED_STAGES)}")

    env: Dict[str, Any] = {
        "schema_version": schema_version,
        "event_id": event_id or f"wev/{uuid.uuid4().hex}",
        "event_type": "aion_equities.write_event",
        "stage": stage_n,
        "entity_kind": str(entity_kind),
        "entity_id": str(entity_id),
        "ts": ts or utc_now_iso(),
        "actor": str(actor),
        "source": {
            "source_type": str(source_type),
        },
        "payload": _deepcopyish(payload),
    }

    if source_ref:
        env["source"]["source_ref"] = str(source_ref)
    if correlation_id:
        env["correlation_id"] = str(correlation_id)
    if causation_id:
        env["causation_id"] = str(causation_id)
    if tags:
        env["tags"] = [str(t) for t in tags]

    if validate and callable(validate_payload):
        # Validates against write_event_envelope.schema.json
        validate_payload("write_event_envelope", env)

    return env


def make_ingestion_event(
    *,
    entity_kind: str,
    entity_id: str,
    payload: Dict[str, Any],
    source_type: str = "document_ingestion",
    source_ref: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    return make_write_event_envelope(
        stage="ingestion",
        entity_kind=entity_kind,
        entity_id=entity_id,
        payload=payload,
        source_type=source_type,
        source_ref=source_ref,
        **kwargs,
    )


def make_interpretation_event(
    *,
    entity_kind: str,
    entity_id: str,
    payload: Dict[str, Any],
    source_type: str = "aion_interpretation",
    source_ref: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    return make_write_event_envelope(
        stage="interpretation",
        entity_kind=entity_kind,
        entity_id=entity_id,
        payload=payload,
        source_type=source_type,
        source_ref=source_ref,
        **kwargs,
    )


def make_decision_event(
    *,
    entity_kind: str,
    entity_id: str,
    payload: Dict[str, Any],
    source_type: str = "aion_decisioning",
    source_ref: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    return make_write_event_envelope(
        stage="decision",
        entity_kind=entity_kind,
        entity_id=entity_id,
        payload=payload,
        source_type=source_type,
        source_ref=source_ref,
        **kwargs,
    )


def make_outcome_event(
    *,
    entity_kind: str,
    entity_id: str,
    payload: Dict[str, Any],
    source_type: str = "market_outcome",
    source_ref: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    return make_write_event_envelope(
        stage="outcome",
        entity_kind=entity_kind,
        entity_id=entity_id,
        payload=payload,
        source_type=source_type,
        source_ref=source_ref,
        **kwargs,
    )