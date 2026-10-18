from backend.modules.aion_website_intake.home_fixed_adapter import (
    classify_home_fixed_service,
    infer_home_fixed_urgency,
    normalize_home_fixed_multistep_form,
    normalize_home_fixed_simple_form,
    normalize_home_fixed_website_payload,
)


def test_phase17b_simple_form_maps_to_website_intake_trigger():
    trigger = normalize_home_fixed_simple_form(
        {
            "name": "Kevin",
            "phone": "+34 600 000 000",
            "email": "test@example.com",
            "message": "I need a leaking pergola roof repaired in Arboleas after the rain.",
            "location": "Arboleas",
            "source": "home_fixed_contact_form",
        }
    )

    assert trigger["event_type"] == "website_intake.trigger.created"
    assert trigger["business_id"] == "home_fixed"
    assert trigger["source"] == "home_fixed_contact_form"
    assert trigger["channel"] == "website_form"
    assert trigger["customer"]["name"] == "Kevin"
    assert trigger["request"]["detected_service"] == "Pergola / roof repair"
    assert trigger["request"]["location"] == "Arboleas"
    assert trigger["request"]["urgency"] == "Medium / rain-related"


def test_phase17b_multistep_builder_payload_maps_to_same_trigger_contract():
    trigger = normalize_home_fixed_multistep_form(
        {
            "source": "home_fixed_multistep_builder",
            "steps": [
                {
                    "id": "contact",
                    "fields": [
                        {"name": "full_name", "value": "Jane Customer"},
                        {"name": "email", "value": "jane@example.com"},
                        {"name": "phone", "value": "+34 611 111 111"},
                    ],
                },
                {
                    "id": "job",
                    "fields": [
                        {
                            "name": "job_details",
                            "value": "Water is coming through the pergola roof near the wall.",
                        },
                        {"name": "town", "value": "Arboleas, Almería"},
                    ],
                },
            ],
        }
    )

    assert trigger["event_type"] == "website_intake.trigger.created"
    assert trigger["source"] == "home_fixed_multistep_builder"
    assert trigger["customer"]["name"] == "Jane Customer"
    assert trigger["request"]["detected_service"] == "Pergola / roof repair"
    assert trigger["request"]["location"] == "Arboleas, Almería"


def test_phase17b_supports_form_builder_answers_dict():
    trigger = normalize_home_fixed_website_payload(
        {
            "answers": {
                "customer_name": "Builder User",
                "whatsapp": "+34 622 222 222",
                "description": "Need wall repair and painting in Albox",
                "area": "Albox",
            }
        }
    )

    assert trigger["customer"]["name"] == "Builder User"
    assert trigger["customer"]["phone"] == "+34 622 222 222"
    assert trigger["request"]["detected_service"] == "Painting"
    assert trigger["request"]["location"] == "Albox"


def test_phase17b_detects_home_fixed_services_from_message():
    assert classify_home_fixed_service("Pergola roof leaking", "") == "Pergola / roof repair"
    assert classify_home_fixed_service("Roof needs fixing", "") == "Roof repair"
    assert classify_home_fixed_service("Need tile repair", "") == "Tile repair"
    assert classify_home_fixed_service("Need garden work", "") == "Garden / exterior work"
    assert classify_home_fixed_service("Something general", "") == "General home repair"


def test_phase17b_explicit_service_wins_over_classifier():
    assert classify_home_fixed_service("roof leak", "Custom selected service") == "Custom selected service"


def test_phase17b_urgency_inference_handles_rain_and_emergency():
    assert infer_home_fixed_urgency("water coming through after rain", "") == "Medium / rain-related"
    assert infer_home_fixed_urgency("urgent dangerous issue", "") == "High"
    assert infer_home_fixed_urgency("normal request", "") == "Normal"


def test_phase17b_adapter_preserves_preview_safety_guards():
    trigger = normalize_home_fixed_simple_form(
        {
            "message": "I need a leaking pergola roof repaired in Arboleas",
            "location": "Arboleas",
        }
    )
    guards = trigger["guards"]

    assert guards["booking_created"] is False
    assert guards["payment_created"] is False
    assert guards["escrow_created"] is False
    assert guards["external_message_sent"] is False
    assert guards["live_chain_write"] is False
    assert guards["live_execution_allowed"] is False
    assert guards["human_review_required"] is True
    assert guards["preview_only"] is True


def test_phase17b_workflow_target_is_home_fixed_new_enquiry():
    trigger = normalize_home_fixed_simple_form(
        {
            "message": "Pergola roof leaking in Arboleas",
            "location": "Arboleas",
        }
    )

    workflow = trigger["workflow_trigger"]
    assert workflow["workflow_id"] == "home_fixed_new_enquiry"
    assert workflow["entry_node"] == "new_website_enquiry"
    assert workflow["mode"] == "guarded_preview"
