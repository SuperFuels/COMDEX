from backend.modules.aion_website_intake.public_intake_endpoint import (
    PUBLIC_INTAKE_EVENT,
    create_ticket_preview_id,
    handle_public_website_intake_post,
    preview_home_fixed_public_intake,
)


def test_phase17c_public_endpoint_accepts_home_fixed_website_form_post():
    result = handle_public_website_intake_post(
        {
            "name": "Kevin",
            "phone": "+34 600 000 000",
            "email": "test@example.com",
            "message": "I need a leaking pergola roof repaired in Arboleas after rain.",
            "location": "Arboleas",
        },
        business_id="home_fixed",
        origin="https://homefixed.example",
    )

    assert result["ok"] is True
    assert result["status_code"] == 202
    assert result["event_type"] == PUBLIC_INTAKE_EVENT
    assert result["ticket_preview_id"].startswith("ticket_preview_home_fixed_")
    assert result["trigger"]["event_type"] == "website_intake.trigger.created"
    assert result["trigger"]["request"]["detected_service"] == "Pergola / roof repair"


def test_phase17c_public_endpoint_returns_ticket_preview_id_deterministically():
    trigger = {
        "event_type": "website_intake.trigger.created",
        "business_id": "home_fixed",
        "source": "test",
        "channel": "website_form",
        "customer": {"name": "A"},
        "request": {"message": "B"},
        "workflow_trigger": {"workflow_id": "home_fixed_new_enquiry"},
        "guards": {"preview_only": True},
    }

    first = create_ticket_preview_id(trigger)
    second = create_ticket_preview_id(trigger)

    assert first == second
    assert first.startswith("ticket_preview_home_fixed_")


def test_phase17c_public_endpoint_rejects_unknown_business():
    result = handle_public_website_intake_post(
        {"message": "test"},
        business_id="unknown_business",
    )

    assert result["ok"] is False
    assert result["status_code"] == 403
    assert result["error"] == "business_not_allowed"


def test_phase17c_public_endpoint_rejects_non_object_payload():
    result = handle_public_website_intake_post(
        "not a dict",  # type: ignore[arg-type]
        business_id="home_fixed",
    )

    assert result["ok"] is False
    assert result["status_code"] == 400
    assert result["error"] == "payload_must_be_object"


def test_phase17c_public_endpoint_preserves_preview_side_effect_guards():
    result = preview_home_fixed_public_intake()
    guards = result["guards"]
    trigger_guards = result["trigger"]["guards"]

    for guard_set in [guards, trigger_guards]:
        assert guard_set["booking_created"] is False
        assert guard_set["payment_created"] is False
        assert guard_set["escrow_created"] is False
        assert guard_set["external_message_sent"] is False
        assert guard_set["live_chain_write"] is False
        assert guard_set["live_execution_allowed"] is False
        assert guard_set["human_review_required"] is True
        assert guard_set["preview_only"] is True


def test_phase17c_public_endpoint_response_points_to_boardroom_ticket_preview():
    result = preview_home_fixed_public_intake()

    assert result["next"]["boardroom"] == "ticket_preview_available"
    assert result["next"]["workflow_mode"] == "guarded_preview"
    assert result["next"]["human_review_required"] is True


def test_phase17c_home_fixed_preview_fixture_is_realistic():
    result = preview_home_fixed_public_intake()
    trigger = result["trigger"]

    assert trigger["business_id"] == "home_fixed"
    assert trigger["request"]["location"] == "Arboleas, Almería"
    assert trigger["request"]["urgency"] == "Medium / rain-related"
    assert "leaking pergola roof" in trigger["request"]["message"]
    assert result["origin"] == "https://homefixed.example"


def test_phase17c_public_endpoint_has_domain_guard_placeholder():
    result = handle_public_website_intake_post(
        {"message": "Need roof repair", "location": "Arboleas"},
        business_id="home_fixed",
        origin="https://homefixed.example",
    )

    assert result["origin"] == "https://homefixed.example"
    assert result["ok"] is True
