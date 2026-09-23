from backend.modules.aion_website_intake.trigger_contract import (
    EVENT_TYPE,
    assert_preview_safe,
    build_home_fixed_preview_trigger,
    default_preview_guards,
)


def test_phase17a_event_type_is_canonical():
    trigger = build_home_fixed_preview_trigger()
    assert trigger["event_type"] == EVENT_TYPE
    assert trigger["event_type"] == "website_intake.trigger.created"


def test_phase17a_payload_supports_required_top_level_fields():
    trigger = build_home_fixed_preview_trigger()

    for key in [
        "trigger_id",
        "business_id",
        "source",
        "channel",
        "customer",
        "request",
        "workflow_trigger",
        "guards",
        "created_at",
    ]:
        assert key in trigger


def test_phase17a_home_fixed_preview_fixture_is_realistic():
    trigger = build_home_fixed_preview_trigger()

    assert trigger["business_id"] == "home_fixed"
    assert trigger["source"] == "home_fixed_website"
    assert trigger["channel"] == "website_form"
    assert "leaking pergola roof repaired in Arboleas" in trigger["request"]["message"]
    assert trigger["request"]["detected_service"] == "Pergola / roof repair"
    assert trigger["request"]["location"] == "Arboleas, Almería"
    assert trigger["request"]["urgency"] == "Medium / rain-related"


def test_phase17a_workflow_trigger_maps_to_home_fixed_enquiry_flow():
    trigger = build_home_fixed_preview_trigger()
    workflow = trigger["workflow_trigger"]

    assert workflow["workflow_id"] == "home_fixed_new_enquiry"
    assert workflow["entry_node"] == "new_website_enquiry"
    assert workflow["mode"] == "guarded_preview"
    assert workflow["next_action"] == "create_ticket_preview"


def test_phase17a_default_preview_guards_block_side_effects():
    guards = default_preview_guards()

    assert guards["booking_created"] is False
    assert guards["payment_created"] is False
    assert guards["escrow_created"] is False
    assert guards["external_message_sent"] is False
    assert guards["live_chain_write"] is False
    assert guards["live_execution_allowed"] is False
    assert guards["human_review_required"] is True
    assert guards["preview_only"] is True


def test_phase17a_assert_preview_safe_accepts_safe_trigger():
    trigger = build_home_fixed_preview_trigger()
    assert_preview_safe(trigger)


def test_phase17a_assert_preview_safe_rejects_live_side_effects():
    trigger = build_home_fixed_preview_trigger()
    trigger["guards"]["payment_created"] = True

    try:
        assert_preview_safe(trigger)
    except ValueError as exc:
        assert "payment_created" in str(exc)
    else:
        raise AssertionError("Expected unsafe trigger to be rejected")


def test_phase17a_trigger_id_is_stable_for_same_payload_shape():
    one = build_home_fixed_preview_trigger()
    two = build_home_fixed_preview_trigger()

    assert one["trigger_id"] == two["trigger_id"]
    assert one["trigger_id"].startswith("wit_")
