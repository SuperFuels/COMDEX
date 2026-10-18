from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_phase18_preview_api_returns_plumbing_hourly_ticket() -> None:
    response = client.get(
        "/api/local-node/aion/phase18/a2a-commercial-ticket-preview",
        params={"scenario": "home_fixed_plumbing_hourly"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["route"]["route_type"] == "hourly_service"
    assert data["service_rule"]["resource_type"] == "Plumber"
    assert data["proposal_preview"]["final_quote_created"] is False
    assert data["guard_envelope"]["preview_only"] is True
    assert data["api_contract"]["preview_only"] is True


def test_phase18_preview_api_returns_roof_discovery_ticket() -> None:
    response = client.get(
        "/api/local-node/aion/phase18/a2a-commercial-ticket-preview",
        params={"scenario": "home_fixed_roof_discovery"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["route"]["route_type"] == "discovery_session"
    assert data["service_rule"]["resource_type"] == "Roofer / general builder"
    assert data["service_rule"]["quote_or_proposal_required"] is True
    assert data["proposal_preview"]["final_quote_created"] is False
    assert "requires inspection" in data["proposal_preview"]["customer_visible_summary"]


def test_phase18_preview_api_never_creates_live_side_effects() -> None:
    response = client.get("/api/local-node/aion/phase18/a2a-commercial-ticket-preview")
    assert response.status_code == 200
    data = response.json()

    for section in [data["guard_envelope"], data["api_contract"]]:
        assert section["preview_only"] is True
        assert section["booking_created"] is False
        assert section["payment_created"] is False
        assert section["escrow_created"] is False
        assert section["external_message_sent"] is False
        assert section["live_chain_write"] is False
        assert section["human_review_required"] is True


def test_phase18_preview_api_returns_deterministic_hashes() -> None:
    first = client.get("/api/local-node/aion/phase18/a2a-commercial-ticket-preview").json()
    second = client.get("/api/local-node/aion/phase18/a2a-commercial-ticket-preview").json()

    assert first["ticket_hash"] == second["ticket_hash"]
    assert first["route"]["route_hash"] == second["route"]["route_hash"]

def test_phase18_preview_api_exposes_display_id_for_user_ui() -> None:
    data = client.get("/api/local-node/aion/phase18/a2a-commercial-ticket-preview?scenario=home_fixed_roof_discovery").json()
    assert data["display_id"] == "A2A-HF-001"
    assert data["ticket_id"] != data["display_id"]
    assert data["route"]["label"] == "Discovery / assessment visit"
    assert data["route"]["pricing_label"] == "Free or paid discovery"
    assert data["service_rule"]["resource_type"] == "Roofer / general builder"

def test_phase18_preview_api_plumbing_labels_are_customer_facing() -> None:
    data = client.get("/api/local-node/aion/phase18/a2a-commercial-ticket-preview?scenario=plumbing_hourly").json()
    assert data["display_id"] == "A2A-HF-001"
    assert data["route"]["label"] == "Hourly service / callout"
    assert data["route"]["pricing_label"] == "First hour plus hourly rate"
    assert data["service_rule"]["resource_type"] == "Plumber"

def test_phase18_roof_api_keeps_customer_request_separate_from_proposal_summary() -> None:
    data = client.get("/api/local-node/aion/phase18/a2a-commercial-ticket-preview?scenario=home_fixed_roof_discovery").json()
    assert data["customer_request"] == "Leaking pergola roof in Arboleas after rain"
    assert data["proposal_preview"]["customer_visible_summary"] == "Roof leak requires inspection before any final quote is prepared."
    assert data["proposal_preview"]["final_quote_created"] is False

def test_phase18_roof_api_requested_and_proposed_slots_are_consistent() -> None:
    data = client.get("/api/local-node/aion/phase18/a2a-commercial-ticket-preview?scenario=home_fixed_roof_discovery").json()
    assert data["availability_preview"]["requested_slot"] == "Tomorrow 11:30"
    assert data["availability_preview"]["available_slot"] == "Tomorrow 13:30"
    assert "11:30 is already held" in data["availability_preview"]["unavailable_reason"]

