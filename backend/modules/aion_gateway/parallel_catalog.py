from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


PARALLEL_CATALOG_PROTOCOL_VERSION = "aion.parallel_business.v0.1"
SETTLEMENT_MODE_FIAT_FIRST = "fiat_first"


def _utc_now_ms() -> int:
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
class ServiceArea:
    country: str
    region: str
    towns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ServicePricingRule:
    currency: str = "EUR"
    base_price_minor: int = 0
    pricing_unit: str = "job"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ServiceEvidenceRequirement:
    evidence_type: str
    required: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ServiceSlaRule:
    response_time_minutes: Optional[int] = None
    completion_window_hours: Optional[int] = None
    emergency_supported: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ServiceExceptionPolicy:
    late_provider: str = "human_review_required"
    missing_evidence: str = "request_missing_evidence"
    quote_changed: str = "revise_quote_requires_human_review"
    unsafe_request: str = "block_and_escalate"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParallelServiceCatalogItem:
    service_key: str
    title: str
    category: str
    description: str = ""
    pricing: ServicePricingRule = field(default_factory=ServicePricingRule)
    evidence_requirements: List[ServiceEvidenceRequirement] = field(default_factory=list)
    sla: ServiceSlaRule = field(default_factory=ServiceSlaRule)
    exception_policy: ServiceExceptionPolicy = field(default_factory=ServiceExceptionPolicy)
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_key": self.service_key,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "pricing": self.pricing.to_dict(),
            "evidence_requirements": [item.to_dict() for item in self.evidence_requirements],
            "sla": self.sla.to_dict(),
            "exception_policy": self.exception_policy.to_dict(),
            "active": self.active,
        }


@dataclass
class ParallelBusinessProfile:
    business_id: str
    business_name: str
    vertical_key: str
    service_areas: List[ServiceArea] = field(default_factory=list)
    services: List[ParallelServiceCatalogItem] = field(default_factory=list)
    accepted_channels: List[str] = field(default_factory=lambda: ["legacy_web_form", "agent_protocol"])
    availability_summary: Dict[str, Any] = field(default_factory=dict)
    proof_required: bool = True
    settlement_mode: str = SETTLEMENT_MODE_FIAT_FIRST
    human_review_required: bool = True
    created_at_ms: int = field(default_factory=_utc_now_ms)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        services_by_key = {}
        for item in self.services:
            services_by_key[item.service_key] = item.to_dict()

        return {
            "protocol_version": PARALLEL_CATALOG_PROTOCOL_VERSION,
            "business_id": self.business_id,
            "business_name": self.business_name,
            "vertical_key": self.vertical_key,
            "service_areas": [area.to_dict() for area in self.service_areas],
            "services": services_by_key,
            "accepted_channels": list(self.accepted_channels),
            "availability_summary": dict(self.availability_summary),
            "proof_required": bool(self.proof_required),
            "settlement_mode": self.settlement_mode,
            "human_review_required": bool(self.human_review_required),
            "created_at_ms": int(self.created_at_ms),
            "metadata": dict(self.metadata),
            "safety": {
                "would_create_booking": False,
                "would_create_payment": False,
                "would_create_escrow": False,
                "would_expose_public_route": False,
                "would_execute_goal_engine": False,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        payload = self.to_payload()
        payload["catalog_hash"] = _stable_hash(payload)
        return payload


def build_home_fixed_parallel_catalog_preview() -> Dict[str, Any]:
    profile = ParallelBusinessProfile(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        service_areas=[
            ServiceArea(
                country="Spain",
                region="Almeria / Murcia",
                towns=[
                    "Arboleas",
                    "Albox",
                    "Huercal Overa",
                    "Zurgena",
                    "La Alfoquia",
                    "surrounding areas",
                ],
            )
        ],
        services=[
            ParallelServiceCatalogItem(
                service_key="general_home_repair",
                title="General Home Repairs",
                category="home_repair",
                description="General repairs, odd jobs, wall repairs, tile repairs, re-grouting, floors and small building works.",
                pricing=ServicePricingRule(currency="EUR", base_price_minor=0, pricing_unit="quote_required"),
                evidence_requirements=[
                    ServiceEvidenceRequirement("customer_problem_photo", True, "Customer photo or description before quote."),
                    ServiceEvidenceRequirement("completion_photo", True, "Photo evidence after work is complete."),
                ],
                sla=ServiceSlaRule(response_time_minutes=240, completion_window_hours=None, emergency_supported=False),
            ),
            ParallelServiceCatalogItem(
                service_key="roof_leak_repair",
                title="Roof Leak / Water Ingress Repair",
                category="roofing",
                description="Inspection and repair path for leaks, roof damage and water ingress.",
                pricing=ServicePricingRule(currency="EUR", base_price_minor=0, pricing_unit="inspection_or_quote_required"),
                evidence_requirements=[
                    ServiceEvidenceRequirement("leak_photo", True, "Photo or video of leak/water ingress."),
                    ServiceEvidenceRequirement("access_photo", False, "Optional photo showing roof/access area."),
                    ServiceEvidenceRequirement("completion_photo", True, "After-work evidence."),
                ],
                sla=ServiceSlaRule(response_time_minutes=120, completion_window_hours=None, emergency_supported=True),
            ),
            ParallelServiceCatalogItem(
                service_key="painting_decorating",
                title="Painting and Decorating",
                category="painting",
                description="Interior/exterior painting, decorating and wall refresh work.",
                pricing=ServicePricingRule(currency="EUR", base_price_minor=0, pricing_unit="quote_required"),
                evidence_requirements=[
                    ServiceEvidenceRequirement("area_photos", True, "Photos of rooms/walls/areas to quote."),
                    ServiceEvidenceRequirement("completion_photos", True, "Photos after completion."),
                ],
            ),
            ParallelServiceCatalogItem(
                service_key="pergola_canopy_repair",
                title="Pergola / Canopy / Outdoor Structure Work",
                category="outdoor_structures",
                description="Pergolas, canopies, garden structure repairs and upgrades.",
                pricing=ServicePricingRule(currency="EUR", base_price_minor=0, pricing_unit="quote_required"),
                evidence_requirements=[
                    ServiceEvidenceRequirement("structure_photo", True, "Photo of existing structure or desired area."),
                    ServiceEvidenceRequirement("completion_photo", True, "After-work evidence."),
                ],
            ),
        ],
        availability_summary={
            "mode": "human_confirmed",
            "emergency_jobs": "review_required",
            "booking_creation": "disabled_in_v0",
        },
        metadata={
            "positioning": "parallel_business_twin_for_agentic_commerce",
            "live_testbed": True,
            "human_website_remains_primary_for_humans": True,
        },
    )

    return profile.to_dict()
