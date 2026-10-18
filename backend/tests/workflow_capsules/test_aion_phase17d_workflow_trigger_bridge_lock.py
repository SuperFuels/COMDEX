from backend.modules.aion_website_intake.public_intake_endpoint import (
    handle_public_website_intake_post,
    preview_home_fixed_public_intake,
)
from backend.modules.aion_website_intake.workflow_trigger_bridge import (
    bridge_public_intake_to_workflow,
    build_business_ticket_from_trigger,
    create_trigger_evidence_id,
    prepare_workflow_preview_from_ticket,
    preview_home_fixed_workflow_trigger_bridge,
    select_workflow_for_trigger,
)


def test_phase17d_selects_workflow_by_business_and_service():
    trigger = preview_home_fixed_public_intake()["trigger"]
    workflow = select_workflow_for_trigger(trigger)

    assert workflow["business_id"] == "home_fixed"
    assert workflow["workflow_id"] == "home_fixed_new_enquiry"
    assert workflow["detected_service"] == "Pergola / roof repair"
    assert workflow["workflow_mode"] == "guarded_preview"


def test_phase17d_creates_business_ticket_from_trigger():
    trigger = preview_home_fixed_public_intake()["trigger"]
    ticket = build_business_ticket_from_trigger(trigger)

    assert ticket["ticket_type"] == "website_intake_ticket"
    assert ticket["status"] == "preview_ready"
    assert ticket["business_id"] == "home_fixed"
    assert ticket["ticket_id"].startswith("ticket_preview_home_fixed_")
    assert ticket["workflow"]["workflow_id"] == "home_fixed_new_enquiry"


def test_phase17d_attaches_trigger_payload_to_ticket_evidence():
    trigger = preview_home_fixed_public_intake()["trigger"]
    ticket = build_business_ticket_from_trigger(trigger)

    evidence = ticket["evidence"][0]

    assert evidence["type"] == "website_intake_trigger_payload"
    assert evidence["label"] == "Website intake trigger"
    assert evidence["payload"] == trigger
    assert evidence["evidence_id"].startswith("evidence_website_intake_")


def test_phase17d_trigger_evidence_id_is_deterministic():
    trigger = preview_home_fixed_public_intake()["trigger"]

    assert create_trigger_evidence_id(trigger) == create_trigger_evidence_id(trigger)


def test_phase17d_prepares_guarded_workflow_preview():
    trigger = preview_home_fixed_public_intake()["trigger"]
    ticket = build_business_ticket_from_trigger(trigger)
    preview = prepare_workflow_preview_from_ticket(ticket)

    assert preview["ticket_id"] == ticket["ticket_id"]
    assert preview["workflow_id"] == "home_fixed_new_enquiry"
    assert preview["workflow_mode"] == "guarded_preview"
    assert preview["current_step"] == "workflow_entry_node"
    assert preview["suggested_next_action"] == "prepare_quote_preview"


def test_phase17d_workflow_preview_contains_customer_request_summary():
    result = preview_home_fixed_workflow_trigger_bridge()
    summary = result["workflow_preview"]["summary"]

    assert summary["service"] == "Pergola / roof repair"
    assert summary["location"] == "Arboleas, Almería"
    assert summary["urgency"] == "Medium / rain-related"
    assert "leaking pergola roof" in summary["message"]


def test_phase17d_preserves_no_side_effect_guards():
    result = preview_home_fixed_workflow_trigger_bridge()
    guards = result["guards"]

    assert guards["booking_created"] is False
    assert guards["payment_created"] is False
    assert guards["escrow_created"] is False
    assert guards["external_message_sent"] is False
    assert guards["live_chain_write"] is False
    assert guards["live_execution_allowed"] is False
    assert guards["human_review_required"] is True
    assert guards["preview_only"] is True


def test_phase17d_rejected_public_intake_does_not_create_ticket():
    rejected = handle_public_website_intake_post(
        {"message": "test"},
        business_id="unknown_business",
    )

    result = bridge_public_intake_to_workflow(rejected)

    assert result["ok"] is False
    assert result["status"] == "rejected"
    assert result["reason"] == "business_not_allowed"
    assert "ticket" not in result


def test_phase17d_bridge_returns_ticket_and_workflow_preview():
    result = preview_home_fixed_workflow_trigger_bridge()

    assert result["ok"] is True
    assert result["status"] == "workflow_preview_ready"
    assert result["ticket"]["ticket_id"].startswith("ticket_preview_home_fixed_")
    assert result["workflow_preview"]["preview_id"].startswith("workflow_preview_ticket_preview_home_fixed_")
