from backend.services.aion_mission_mode.small_business_foundation import (
    create_small_business_foundation_profile,
    summarize_small_business_foundation,
    validate_small_business_foundation_input,
)


def _home_fixed_input():
    return {
        "business_name": "Home Fixed",
        "business_type": "services",
        "industry": "Property maintenance and outdoor living improvements",
        "service_area": "Almería and Murcia",
        "primary_goal": "get_more_leads",
        "website": "https://homefixed.example",
        "social_accounts": "@HomeFixed, Facebook/HomeFixed",
        "products_services": "Painting, repairs, pergolas, carports, villa upgrades",
        "target_customers": "Villa owners, expats, homeowners",
        "tone_of_voice": "Reliable, practical, professional",
        "current_tools": "Facebook, Google Business Profile, website",
        "current_pain_points": "Needs more regular leads and repeatable marketing",
        "growth_goals": "Increase leads and bookings",
        "contact_email": "info@homefixed.example",
        "phone_number": "+34 711 269 364",
        "business_address": "Albox, Almería",
        "opening_hours": "Monday to Friday",
        "pricing_notes": "Free quote. Job pricing depends on scope.",
        "brand_notes": "Practical property improvement brand.",
        "reviews_or_proof": "Before and after project photos.",
        "extra_notes": "Keep website service language and CTAs.",
    }


def test_phase24b_minimum_required_fields_are_small_and_clear():
    result = validate_small_business_foundation_input({
        "business_name": "Home Fixed",
        "business_type": "services",
        "industry": "Property maintenance",
        "service_area": "Almería",
        "primary_goal": "get_more_leads",
    })

    assert result["valid"] is True
    assert result["missing_required_fields"] == []
    assert result["required_fields"] == [
        "business_name",
        "business_type",
        "industry",
        "service_area",
        "primary_goal",
    ]


def test_phase24b_missing_required_fields_do_not_create_foundation_hash():
    profile = create_small_business_foundation_profile({
        "business_name": "Home Fixed",
        "business_type": "services",
    })

    assert profile["status"] == "needs_required_fields"
    assert profile["foundation_hash"] is None
    assert "industry" in profile["validation"]["missing_required_fields"]
    assert profile["live_external_side_effect"] is False


def test_phase24b_home_fixed_foundation_profile_is_created():
    profile = create_small_business_foundation_profile(_home_fixed_input())

    assert profile["schema_version"] == "aion.small_business_foundation.v0"
    assert profile["mode"] == "small_business_growth"
    assert profile["business_id"] == "home-fixed"
    assert profile["business_name"] == "Home Fixed"
    assert profile["business_type"] == "services"
    assert profile["industry"] == "Property maintenance and outdoor living improvements"
    assert profile["service_area"] == "Almería and Murcia"
    assert profile["primary_goal"] == "get_more_leads"
    assert profile["status"] == "draft_ready_for_review"
    assert profile["foundation_hash"].startswith("sha256:")


def test_phase24b_optional_fields_can_be_completed_later():
    profile = create_small_business_foundation_profile({
        "business_name": "Test Business",
        "business_type": "both",
        "industry": "Retail and services",
        "service_area": "Local",
        "primary_goal": "automate_work",
    })

    assert profile["optional_fields_can_be_completed_later"] is True
    assert profile["website"] == ""
    assert profile["social_accounts"] == []
    assert profile["foundation_hash"].startswith("sha256:")


def test_phase24b_enrichment_tasks_are_staged_not_live():
    profile = create_small_business_foundation_profile(_home_fixed_input())
    tasks = profile["staged_enrichment_tasks"]

    assert any(task["task_id"] == "website_scan" for task in tasks)
    assert any(task["task_id"] == "social_profile_read" for task in tasks)
    assert any(task["task_id"] == "manual_foundation_review" for task in tasks)

    for task in tasks:
        assert task["live_external_side_effect"] is False
        assert task["status"] in {"staged", "ready"}
        assert task["tool_mode"] in {"read_only_external", "safe_internal"}


def test_phase24b_foundation_hash_is_deterministic_for_same_inputs():
    first = create_small_business_foundation_profile(_home_fixed_input())
    second = create_small_business_foundation_profile(_home_fixed_input())

    assert first["foundation_hash"] == second["foundation_hash"]


def test_phase24b_summary_is_ready_for_approval():
    profile = create_small_business_foundation_profile(_home_fixed_input())
    summary = summarize_small_business_foundation(profile)

    assert summary["ready_for_approval"] is True
    assert summary["business_name"] == "Home Fixed"
    assert summary["business_type"] == "services"
    assert summary["industry"] == "Property maintenance and outdoor living improvements"
    assert summary["primary_goal"] == "get_more_leads"
    assert summary["staged_enrichment_count"] >= 3
    assert summary["foundation_hash"] == profile["foundation_hash"]


def test_phase24b_department_readiness_waits_for_foundation_approval():
    profile = create_small_business_foundation_profile(_home_fixed_input())

    assert profile["department_readiness"]["pilot"] == "ready"
    assert profile["department_readiness"]["marketing"] == "ready_after_foundation_approval"
    assert profile["department_readiness"]["sales"] == "ready_after_foundation_approval"
    assert profile["department_readiness"]["finance"] == "ready_after_foundation_approval"
    assert profile["department_readiness"]["operations"] == "ready_after_foundation_approval"
    assert profile["department_readiness"]["support"] == "ready_after_foundation_approval"
    assert profile["department_readiness"]["builder"] == "ready_after_foundation_approval"


def test_phase24b_foundation_keeps_additional_business_information():
    profile = create_small_business_foundation_profile(_home_fixed_input())

    assert profile["contact_email"] == "info@homefixed.example"
    assert profile["phone_number"] == "+34 711 269 364"
    assert profile["business_address"] == "Albox, Almería"
    assert profile["opening_hours"] == "Monday to Friday"
    assert profile["pricing_notes"] == "Free quote. Job pricing depends on scope."
    assert profile["brand_notes"] == "Practical property improvement brand."
    assert profile["reviews_or_proof"] == "Before and after project photos."
    assert profile["extra_notes"] == "Keep website service language and CTAs."
