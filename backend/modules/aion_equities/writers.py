# backend/modules/aion_equities/writers.py

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone

try:
    from backend.modules.aion_equities import validate_payload
except Exception:  # pragma: no cover
    validate_payload = None  # type: ignore

from .investing_ids import (
    company_id,
    company_quarter_id,
    company_catalyst_id,
)


__all__ = [
    "utc_now_iso",
    "build_company_record",
    "build_quarter_event_record",
    "build_catalyst_event_record",
    "build_thesis_state_record",
    "build_kg_edge_record",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _merge(base: Dict[str, Any], extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = dict(base)
    if isinstance(extra, dict):
        out.update(extra)
    return out


def build_company_record(
    *,
    ticker: str,
    name: str,
    primary_listing_exchange: Optional[str] = None,
    country: Optional[str] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    currency: Optional[str] = None,
    as_of: Optional[str] = None,
    schema_version: str = "v0.1.0",
    extra: Optional[Dict[str, Any]] = None,
    validate: bool = False,
) -> Dict[str, Any]:
    """
    Minimal canonical company payload.
    Extra fields can be supplied as schema evolves.
    """
    payload: Dict[str, Any] = {
        "schema_version": schema_version,
        "company_id": company_id(ticker),
        "ticker": ticker,
        "name": name,
        "as_of": as_of or utc_now_iso(),
    }

    optional_fields = {
        "primary_listing_exchange": primary_listing_exchange,
        "country": country,
        "sector": sector,
        "industry": industry,
        "currency": currency,
    }
    for k, v in optional_fields.items():
        if v is not None:
            payload[k] = v

    payload = _merge(payload, extra)

    if validate and callable(validate_payload):
        validate_payload("company", payload)

    return payload


def build_quarter_event_record(
    *,
    ticker: str,
    year: int,
    quarter: int,
    event_date: str,
    filing_kind: str = "quarterly_results",
    as_of: Optional[str] = None,
    schema_version: str = "v0.1.0",
    extra: Optional[Dict[str, Any]] = None,
    validate: bool = False,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema_version": schema_version,
        "quarter_event_id": company_quarter_id(ticker, year, quarter),
        "entity_id": company_id(ticker),
        "ticker": ticker,
        "year": int(year),
        "quarter": int(quarter),
        "event_date": event_date,
        "filing_kind": filing_kind,
        "as_of": as_of or utc_now_iso(),
    }

    payload = _merge(payload, extra)

    if validate and callable(validate_payload):
        validate_payload("quarter_event", payload)

    return payload


def build_catalyst_event_record(
    *,
    ticker: str,
    catalyst_key: str,
    catalyst_type: str,
    event_date: str,
    timing_confidence: Optional[float] = None,
    as_of: Optional[str] = None,
    schema_version: str = "v0.1.0",
    extra: Optional[Dict[str, Any]] = None,
    validate: bool = False,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema_version": schema_version,
        "catalyst_event_id": company_catalyst_id(ticker, catalyst_key),
        "entity_id": company_id(ticker),
        "ticker": ticker,
        "catalyst_type": catalyst_type,
        "event_date": event_date,
        "as_of": as_of or utc_now_iso(),
    }

    if timing_confidence is not None:
        payload["timing_confidence"] = float(timing_confidence)

    payload = _merge(payload, extra)

    if validate and callable(validate_payload):
        validate_payload("catalyst_event", payload)

    return payload


def build_thesis_state_record(
    *,
    thesis_id: str,
    entity_id: str,
    mode: str,
    window: str,
    as_of: str,
    superposition_candidates: Optional[list[dict]] = None,
    collapse_readiness: Optional[dict] = None,
    sqi: Optional[dict] = None,
    schema_version: str = "v0.1.0",
    extra: Optional[Dict[str, Any]] = None,
    validate: bool = False,
) -> Dict[str, Any]:
    """
    Thin thesis payload builder. Keep it permissive in v0.1 to match evolving schema.
    """
    payload: Dict[str, Any] = {
        "schema_version": schema_version,
        "thesis_id": thesis_id,
        "entity_id": entity_id,
        "mode": mode,
        "window": window,
        "as_of": as_of,
        "superposition_candidates": superposition_candidates or [],
    }

    if collapse_readiness is not None:
        payload["collapse_readiness"] = collapse_readiness
    if sqi is not None:
        payload["sqi"] = sqi

    payload = _merge(payload, extra)

    if validate and callable(validate_payload):
        validate_payload("thesis_state", payload)

    return payload


def build_kg_edge_record(
    *,
    src_id: str,
    dst_id: str,
    edge_type: str,
    confidence: Optional[float] = None,
    weight: Optional[float] = None,
    as_of: Optional[str] = None,
    schema_version: str = "v0.1.0",
    edge_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    validate: bool = False,
) -> Dict[str, Any]:
    """
    Thin KG edge builder aligned with explicit edge typing.
    """
    if not edge_id:
        # deterministic-enough readable edge id for early-stage use
        safe_src = src_id.replace("/", "|")
        safe_dst = dst_id.replace("/", "|")
        edge_id = f"kge/{edge_type}/{safe_src}->{safe_dst}"

    payload: Dict[str, Any] = {
        "schema_version": schema_version,
        "edge_id": edge_id,
        "src_id": src_id,
        "dst_id": dst_id,
        "edge_type": edge_type,
        "as_of": as_of or utc_now_iso(),
    }

    if confidence is not None:
        payload["confidence"] = float(confidence)
    if weight is not None:
        payload["weight"] = float(weight)

    payload = _merge(payload, extra)

    if validate and callable(validate_payload):
        validate_payload("kg_edge", payload)

    return payload