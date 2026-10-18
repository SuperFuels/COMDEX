from backend.workflow_capsules.aion_a2a_commercial_ticket import (
    A2ACommercialTicket,
    AvailabilityPreview,
    CommercialRoute,
    GuardEnvelope,
    ProposalPreview,
    ServiceRule,
    home_fixed_plumbing_hourly_ticket,
    home_fixed_roof_discovery_ticket,
)


def test_commercial_route_schema_supports_universal_fields() -> None:
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

    data = route.to_dict()
    assert data["route_type"] == "hourly_service"
    assert data["pricing_model"] == "first_hour_plus_hourly"
    assert data["requires_calendar"] is True
    assert data["requires_human_review"] is True
    assert data["route_hash"].startswith("route_")


def test_guard_envelope_blocks_all_live_side_effects() -> None:
    guard = GuardEnvelope()
    guard.assert_no_live_side_effects()

    assert guard.preview_only is True
    assert guard.booking_created is False
    assert guard.payment_created is False
    assert guard.escrow_created is False
    assert guard.external_message_sent is False
    assert guard.live_chain_write is False
    assert guard.human_review_required is True


def test_home_fixed_plumbing_hourly_ticket_is_realistic_and_safe() -> None:
    ticket = home_fixed_plumbing_hourly_ticket()
    data = ticket.to_dict()

    ticket.assert_safe_preview()

    assert data["route"]["route_type"] == "hourly_service"
    assert data["route"]["pricing_model"] == "first_hour_plus_hourly"
    assert data["service_rule"]["resource_type"] == "plumber"
    assert "First hour" in data["service_rule"]["first_hour_charge"]
    assert "Additional hours" in data["service_rule"]["additional_hourly_rate"]
    assert data["availability_preview"]["requested_slot"] == "Tomorrow 11:30"
    assert data["availability_preview"]["available_slot"] == "Tomorrow 13:30"
    assert data["availability_preview"]["live_booking_created"] is False
    assert data["ticket_hash"].startswith("ticket_")


def test_home_fixed_roof_discovery_does_not_fake_final_quote() -> None:
    ticket = home_fixed_roof_discovery_ticket()
    data = ticket.to_dict()

    ticket.assert_safe_preview()

    assert data["route"]["route_type"] == "discovery_session"
    assert data["route"]["requires_proposal"] is True
    assert data["service_rule"]["resource_type"] == "roofer"
    assert data["service_rule"]["quote_or_proposal_required"] is True
    assert "inspection required before quote" in data["service_rule"]["discovery_visit"]
    assert data["proposal_preview"]["final_quote_created"] is False
    assert "requires inspection" in data["proposal_preview"]["customer_visible_summary"]


def test_ticket_hash_is_deterministic() -> None:
    first = home_fixed_plumbing_hourly_ticket().to_dict()["ticket_hash"]
    second = home_fixed_plumbing_hourly_ticket().to_dict()["ticket_hash"]
    assert first == second


def test_backend_contract_names_are_present() -> None:
    assert CommercialRoute
    assert ServiceRule
    assert A2ACommercialTicket
    assert ProposalPreview
    assert AvailabilityPreview
