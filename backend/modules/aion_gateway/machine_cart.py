from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from backend.modules.aion_gateway.parallel_catalog import (
    PARALLEL_CATALOG_PROTOCOL_VERSION,
    build_home_fixed_parallel_catalog_preview,
)


MACHINE_CART_PROTOCOL_VERSION = "aion.machine_cart.v0.1"
QUOTE_STATUS_PREVIEW = "quote_preview"
SETTLEMENT_MODE_FIAT_FIRST = "fiat_first"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _stable_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


@dataclass
class MachineCartLineItem:
    service_key: str
    quantity: int = 1
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MachineCartConstraint:
    location_town: str
    requested_window: Optional[str] = None
    max_fiat_price_minor: Optional[int] = None
    currency: str = "EUR"
    required_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MachineCartRequest:
    business_id: str
    line_items: List[MachineCartLineItem]
    constraints: MachineCartConstraint
    consumer_agent_id: Optional[str] = None
    created_at_ms: int = field(default_factory=_now_ms)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "protocol_version": MACHINE_CART_PROTOCOL_VERSION,
            "business_id": self.business_id,
            "line_items": [item.to_dict() for item in self.line_items],
            "constraints": self.constraints.to_dict(),
            "consumer_agent_id": self.consumer_agent_id,
            "created_at_ms": int(self.created_at_ms),
            "metadata": dict(self.metadata),
        }

    def to_dict(self) -> Dict[str, Any]:
        payload = self.to_payload()
        payload["cart_hash"] = _stable_hash(payload)
        return payload


def _catalog_service(catalog: Dict[str, Any], service_key: str) -> Optional[Dict[str, Any]]:
    services = catalog.get("services") or {}
    if not isinstance(services, dict):
        return None
    service = services.get(service_key)
    return service if isinstance(service, dict) else None


def _supported_towns(catalog: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for area in catalog.get("service_areas") or []:
        if isinstance(area, dict):
            for town in area.get("towns") or []:
                out.append(str(town).lower())
    return out


def _service_required_evidence(service: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for item in service.get("evidence_requirements") or []:
        if not isinstance(item, dict):
            continue
        if item.get("required") is True:
            ev = str(item.get("evidence_type") or "").strip()
            if ev:
                out.append(ev)
    return out


def preview_machine_cart_quote(
    *,
    cart_request: MachineCartRequest,
    catalog: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    catalog = dict(catalog or build_home_fixed_parallel_catalog_preview())
    cart = cart_request.to_dict()

    blocked_reasons: List[str] = []
    warnings: List[str] = []

    if cart_request.business_id != catalog.get("business_id"):
        blocked_reasons.append("business_id_not_found")

    if not cart_request.line_items:
        blocked_reasons.append("missing_line_items")

    town = str(cart_request.constraints.location_town or "").strip().lower()
    if town and town not in _supported_towns(catalog):
        blocked_reasons.append("unsupported_location")
    if not town:
        blocked_reasons.append("missing_location")

    quote_lines: List[Dict[str, Any]] = []
    evidence_required: List[str] = []

    for line in cart_request.line_items:
        service = _catalog_service(catalog, line.service_key)
        if not service:
            blocked_reasons.append(f"unsupported_service:{line.service_key}")
            continue

        pricing = service.get("pricing") or {}
        required = _service_required_evidence(service)
        evidence_required.extend(required)

        quote_lines.append(
            {
                "service_key": line.service_key,
                "title": service.get("title"),
                "quantity": int(line.quantity),
                "pricing_unit": pricing.get("pricing_unit"),
                "currency": pricing.get("currency", "EUR"),
                "base_price_minor": int(pricing.get("base_price_minor") or 0),
                "quote_required": str(pricing.get("pricing_unit") or "").endswith("quote_required"),
            }
        )

    provided_evidence = set(str(x) for x in cart_request.constraints.required_evidence)
    missing_evidence = sorted(set(evidence_required) - provided_evidence)
    if missing_evidence:
        warnings.append("missing_required_evidence_for_final_execution")

    quote_payload = {
        "protocol_version": MACHINE_CART_PROTOCOL_VERSION,
        "catalog_protocol_version": PARALLEL_CATALOG_PROTOCOL_VERSION,
        "business_id": cart_request.business_id,
        "cart_hash": cart["cart_hash"],
        "catalog_hash": catalog.get("catalog_hash"),
        "quote_status": QUOTE_STATUS_PREVIEW,
        "quote_lines": quote_lines,
        "currency": cart_request.constraints.currency,
        "max_fiat_price_minor": cart_request.constraints.max_fiat_price_minor,
        "evidence_required": sorted(set(evidence_required)),
        "missing_evidence": missing_evidence,
        "settlement_mode": SETTLEMENT_MODE_FIAT_FIRST,
        "human_review_required": True,
        "expires_at_ms": int(_now_ms() + 30 * 60 * 1000),
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "safety": {
            "would_create_booking": False,
            "would_create_payment": False,
            "would_create_escrow": False,
            "would_execute_goal_engine": False,
            "would_expose_public_route": False,
            "would_move_money": False,
        },
    }

    quote_hash = _stable_hash(quote_payload)

    return {
        "ok": len(blocked_reasons) == 0,
        "status": "preview_ready" if len(blocked_reasons) == 0 else "blocked",
        "cart_request": cart,
        "quote_preview": {
            **quote_payload,
            "quote_hash": quote_hash,
        },
        "fulfilment_job_preview_link": {
            "would_create_fulfilment_job": False,
            "business_id": cart_request.business_id,
            "service_keys": [item.service_key for item in cart_request.line_items],
            "cart_hash": cart["cart_hash"],
            "quote_hash": quote_hash,
        },
        "settlement_readiness_preview": {
            "settlement_mode": SETTLEMENT_MODE_FIAT_FIRST,
            "payment_ready": False,
            "would_move_money": False,
        },
        "proof_commitment_preview": {
            "would_commit_proof": False,
            "proof_required": bool(catalog.get("proof_required") is True),
            "quote_hash": quote_hash,
        },
        "blocked_reasons": blocked_reasons,
    }


def build_home_fixed_machine_cart_quote_preview(
    *,
    service_key: str = "roof_leak_repair",
    location_town: str = "Arboleas",
    max_fiat_price_minor: Optional[int] = None,
    required_evidence: Optional[List[str]] = None,
) -> Dict[str, Any]:
    req = MachineCartRequest(
        business_id="home_fixed",
        line_items=[MachineCartLineItem(service_key=service_key)],
        constraints=MachineCartConstraint(
            location_town=location_town,
            max_fiat_price_minor=max_fiat_price_minor,
            required_evidence=list(required_evidence or []),
        ),
        metadata={"testbed": "home_fixed"},
    )
    return preview_machine_cart_quote(cart_request=req)
