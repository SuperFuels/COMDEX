from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


DISCOVERY_PROTOCOL_VERSION = "aion.parallel_discovery.v0.1"

SUPPORTED_DISCOVERY_PROTOCOLS = [
    "aion.parallel_business.v0.1",
    "aion.machine_cart.v0.1",
    "aion.gateway.v0.1",
]


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DiscoveryEndpointPlaceholder:
    name: str
    uri: str
    method: str = "GET"
    public_route_exposed: bool = False
    requires_auth: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiscoveryAuthPolicy:
    auth_required: bool = True
    supported_modes: List[str] = field(default_factory=lambda: ["api_key_later", "signed_agent_later"])
    public_write_allowed: bool = False
    scoped_permissions_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiscoveryRateLimitPolicy:
    rate_limit_required: bool = True
    abuse_protection_required: bool = True
    default_policy: str = "tenant_scoped_rate_limit_later"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AionAgentDiscoveryDocument:
    protocol_version: str
    business_id: str
    business_name: str
    vertical_key: str
    accepted_protocol_versions: List[str]
    endpoints: Dict[str, Dict[str, Any]]
    auth_policy: Dict[str, Any]
    rate_limit_policy: Dict[str, Any]
    public_route_exposed: bool
    human_review_required: bool
    discovery_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_parallel_discovery_document(
    *,
    business_id: str,
    business_name: str = "Home Fixed",
    vertical_key: str = "home_repair",
    base_path: str = "/api/aion/a2a",
    accepted_protocol_versions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    blocked_reasons: List[str] = []

    if not str(business_id or "").strip():
        blocked_reasons.append("missing_business_id")

    business_id_clean = str(business_id or "").strip()
    base = str(base_path or "/api/aion/a2a").rstrip("/")

    endpoints = {
        "discovery": DiscoveryEndpointPlaceholder(
            name="discovery",
            uri="/.well-known/aion-agent",
            method="GET",
            public_route_exposed=False,
            description="Future public discovery document endpoint; not exposed in v0.",
        ).to_dict(),
        "ai_agent_discovery": DiscoveryEndpointPlaceholder(
            name="ai_agent_discovery",
            uri="/.well-known/ai-agent",
            method="GET",
            public_route_exposed=False,
            description="Future compatibility discovery endpoint; not exposed in v0.",
        ).to_dict(),
        "catalog": DiscoveryEndpointPlaceholder(
            name="catalog",
            uri=f"{base}/businesses/{business_id_clean}/catalog",
            method="GET",
            public_route_exposed=False,
            description="Future machine-readable business catalog endpoint.",
        ).to_dict(),
        "capabilities": DiscoveryEndpointPlaceholder(
            name="capabilities",
            uri=f"{base}/businesses/{business_id_clean}/capabilities",
            method="GET",
            public_route_exposed=False,
            description="Future business capability contract endpoint.",
        ).to_dict(),
        "quote": DiscoveryEndpointPlaceholder(
            name="quote",
            uri=f"{base}/businesses/{business_id_clean}/quote",
            method="POST",
            public_route_exposed=False,
            description="Future machine cart quote handshake endpoint.",
        ).to_dict(),
        "trace": DiscoveryEndpointPlaceholder(
            name="trace",
            uri=f"{base}/jobs/{{job_id}}/trace",
            method="GET",
            public_route_exposed=False,
            description="Future machine-readable job trace endpoint.",
        ).to_dict(),
        "proof": DiscoveryEndpointPlaceholder(
            name="proof",
            uri=f"{base}/jobs/{{job_id}}/proof",
            method="GET",
            public_route_exposed=False,
            description="Future proof receipt and verification endpoint.",
        ).to_dict(),
    }

    auth_policy = DiscoveryAuthPolicy().to_dict()
    rate_limit_policy = DiscoveryRateLimitPolicy().to_dict()

    payload = {
        "protocol_version": DISCOVERY_PROTOCOL_VERSION,
        "business_id": business_id_clean,
        "business_name": str(business_name or "").strip(),
        "vertical_key": str(vertical_key or "").strip(),
        "accepted_protocol_versions": list(accepted_protocol_versions or SUPPORTED_DISCOVERY_PROTOCOLS),
        "endpoints": endpoints,
        "auth_policy": auth_policy,
        "rate_limit_policy": rate_limit_policy,
        "public_route_exposed": False,
        "human_review_required": True,
    }

    discovery_hash = _stable_hash(payload)

    document = AionAgentDiscoveryDocument(
        **payload,
        discovery_hash=discovery_hash,
    )

    return {
        "ok": len(blocked_reasons) == 0,
        "status": "preview" if not blocked_reasons else "blocked",
        "blocked_reasons": blocked_reasons,
        "document": document.to_dict(),
        "public_route_exposed": False,
        "would_expose_well_known_route": False,
        "would_create_public_api": False,
        "would_execute_goal_engine": False,
        "would_create_booking": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_move_money": False,
    }
