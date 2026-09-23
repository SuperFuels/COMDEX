from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


RouteType = Literal[
    "fixed_product",
    "hourly_service",
    "discovery_session",
    "custom_quote",
    "metered_work",
    "subscription",
    "escrow_contract",
]

PricingModel = Literal[
    "fixed_price",
    "first_hour_plus_hourly",
    "free_discovery",
    "paid_discovery",
    "quote_required",
    "proposal_required",
    "usage_based",
]

NegotiationState = Literal[
    "agent_request_received",
    "route_rules_returned",
    "customer_agent_confirming",
    "availability_requested",
    "slot_proposed",
    "customer_agent_accepted",
    "human_approval_required",
    "proof_ready",
]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def deterministic_hash(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:24]}"


@dataclass(frozen=True)
class CommercialRoute:
    route_type: RouteType
    label: str
    pricing_model: PricingModel
    pricing_label: str
    requires_calendar: bool
    requires_human_review: bool
    requires_payment: bool
    requires_escrow: bool
    requires_proposal: bool
    requires_evidence: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["route_hash"] = deterministic_hash("route", data)
        return data


@dataclass(frozen=True)
class ServiceRule:
    service_key: str
    service_label: str
    first_hour_charge: str = "Not required"
    additional_hourly_rate: str = "Not required"
    discovery_visit: str = "Not required"
    quote_or_proposal_required: bool = False
    materials_policy: str = "Materials quoted separately where required"
    approval_threshold: str = "Human approval required before live booking/payment"
    resource_type: str = "engineer"


@dataclass(frozen=True)
class ProposalPreview:
    proposal_type: str
    customer_visible_summary: str
    price_or_rate: str
    next_action: str
    final_quote_created: bool = False


@dataclass(frozen=True)
class AvailabilityPreview:
    requested_slot: str
    available_slot: str
    alternatives: list[str] = field(default_factory=list)
    unavailable_reason: str = ""
    resource_model: str = "Single engineer now · multi-engineer ready later"
    resource_type: str = "engineer"
    live_booking_created: bool = False


@dataclass(frozen=True)
class GuardEnvelope:
    preview_only: bool = True
    booking_created: bool = False
    payment_created: bool = False
    escrow_created: bool = False
    external_message_sent: bool = False
    live_chain_write: bool = False
    human_review_required: bool = True

    def assert_no_live_side_effects(self) -> None:
        assert self.preview_only is True
        assert self.booking_created is False
        assert self.payment_created is False
        assert self.escrow_created is False
        assert self.external_message_sent is False
        assert self.live_chain_write is False
        assert self.human_review_required is True


@dataclass(frozen=True)
class A2ANegotiationStep:
    state: NegotiationState
    label: str
    detail: str


@dataclass(frozen=True)
class A2ACommercialTicket:
    ticket_id: str
    business_name: str
    customer_request: str
    vertical: str
    scenario_key: str
    route: CommercialRoute
    service_rule: ServiceRule
    proposal_preview: ProposalPreview
    availability_preview: AvailabilityPreview
    negotiation_state: NegotiationState
    negotiation_steps: list[A2ANegotiationStep]
    guard: GuardEnvelope = field(default_factory=GuardEnvelope)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["route"] = self.route.to_dict()
        data["ticket_hash"] = deterministic_hash("ticket", {
            "ticket_id": self.ticket_id,
            "business_name": self.business_name,
            "customer_request": self.customer_request,
            "vertical": self.vertical,
            "scenario_key": self.scenario_key,
            "route": self.route.to_dict(),
            "service_rule": asdict(self.service_rule),
            "proposal_preview": asdict(self.proposal_preview),
            "availability_preview": asdict(self.availability_preview),
            "negotiation_state": self.negotiation_state,
            "negotiation_steps": [asdict(step) for step in self.negotiation_steps],
            "guard": asdict(self.guard),
        })
        return data

    def assert_safe_preview(self) -> None:
        self.guard.assert_no_live_side_effects()
        assert self.proposal_preview.final_quote_created is False
        assert self.availability_preview.live_booking_created is False


def home_fixed_plumbing_hourly_ticket() -> A2ACommercialTicket:
    route = CommercialRoute(
        route_type="hourly_service",
        label="Hourly service / callout",
        pricing_model="first_hour_plus_hourly",
        pricing_label="First hour plus additional hourly rate",
        requires_calendar=True,
        requires_human_review=True,
        requires_payment=True,
        requires_escrow=False,
        requires_proposal=False,
    )

    return A2ACommercialTicket(
        ticket_id="a2a_home_fixed_plumbing_preview",
        business_name="Home Fixed",
        customer_request="Customer needs a plumber for a leak under the sink",
        vertical="home_services",
        scenario_key="plumbing_hourly_callout",
        route=route,
        service_rule=ServiceRule(
            service_key="plumbing_callout",
            service_label="Plumbing hourly callout",
            first_hour_charge="First hour callout charge required",
            additional_hourly_rate="Additional hours billed at pre-agreed hourly rate",
            discovery_visit="Not required for simple callout",
            quote_or_proposal_required=False,
            resource_type="plumber",
        ),
        proposal_preview=ProposalPreview(
            proposal_type="hourly_callout",
            customer_visible_summary="Plumber callout can be proposed with first-hour charge and approved extra-hour rules.",
            price_or_rate="First hour + agreed additional hourly rate",
            next_action="Customer-side agent confirms slot and business owner reviews before live booking.",
        ),
        availability_preview=AvailabilityPreview(
            requested_slot="Tomorrow 11:30",
            available_slot="Tomorrow 13:30",
            alternatives=["Tomorrow 15:00", "Next working day 09:30"],
            unavailable_reason="11:30 is already blocked in the engineer diary",
            resource_type="plumber",
        ),
        negotiation_state="human_approval_required",
        negotiation_steps=[
            A2ANegotiationStep("agent_request_received", "Agent request received", "Customer-side agent asked for a plumber callout."),
            A2ANegotiationStep("route_rules_returned", "Route rules returned", "AION returned first-hour plus hourly-rate rules."),
            A2ANegotiationStep("availability_requested", "Availability requested", "Customer requested tomorrow 11:30."),
            A2ANegotiationStep("slot_proposed", "Alternative slot proposed", "AION proposed 13:30 because 11:30 is unavailable."),
            A2ANegotiationStep("human_approval_required", "Human approval required", "No booking/payment is created until approval."),
        ],
    )


def home_fixed_roof_discovery_ticket() -> A2ACommercialTicket:
    route = CommercialRoute(
        route_type="discovery_session",
        label="Discovery / assessment visit",
        pricing_model="free_discovery",
        pricing_label="Free discovery before quote",
        requires_calendar=True,
        requires_human_review=True,
        requires_payment=False,
        requires_escrow=False,
        requires_proposal=True,
    )

    return A2ACommercialTicket(
        ticket_id="a2a_home_fixed_roof_discovery_preview",
        business_name="Home Fixed",
        vertical="home_services",
        scenario_key="roof_leak_discovery",
        route=route,
        service_rule=ServiceRule(
            service_key="roof_leak_assessment",
            service_label="Roof leak assessment",
            discovery_visit="Site visit / inspection required before quote",
            quote_or_proposal_required=True,
            resource_type="roofer",
        ),
        customer_request="Leaking pergola roof in Arboleas after rain",
        proposal_preview=ProposalPreview(
            proposal_type="discovery_visit",
            customer_visible_summary="Roof leak requires inspection before any final quote is prepared.",
            price_or_rate="Quote/proposal required after site visit",
            next_action="Book assessment preview, then prepare quote after evidence is captured.",
            final_quote_created=False,
        ),
        availability_preview=AvailabilityPreview(
            requested_slot="Tomorrow 11:30",
            available_slot="Tomorrow 13:30",
            alternatives=["Tomorrow 13:30"],
            unavailable_reason="11:30 is already held for another site visit.",
            resource_type="roofer",
        ),
        negotiation_state="human_approval_required",
        negotiation_steps=[
            A2ANegotiationStep("agent_request_received", "Agent request received", "Customer-side agent asked for roof leak repair."),
            A2ANegotiationStep("route_rules_returned", "Discovery route returned", "AION refused fake final quote and requires inspection."),
            A2ANegotiationStep("slot_proposed", "Assessment slot proposed", "AION proposed a site visit slot."),
            A2ANegotiationStep("human_approval_required", "Human approval required", "No booking/payment/escrow is created."),
        ],
    )
