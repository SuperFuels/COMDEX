from backend.services.aion_mission_mode.marketing_department_pack import (
    MARKETING_BLOCKED_LIVE_ACTIONS,
    MARKETING_SAFE_ARTIFACTS,
    create_home_fixed_marketing_fixture_pack,
    create_marketing_department_pack,
)


def test_phase23q_home_fixed_marketing_routes_to_marketing_with_support_departments():
    pack = create_home_fixed_marketing_fixture_pack(evaluation_time=100)

    assert pack["business_id"] == "home-fixed"
    assert pack["primary_department"] == "marketing"
    assert pack["supporting_departments"] == ["finance", "sales", "operations"]
    assert pack["pack_hash"].startswith("sha256:")


def test_phase23q_marketing_pack_expands_beyond_text_plan():
    pack = create_home_fixed_marketing_fixture_pack(evaluation_time=100)

    marketing_capabilities = [
        item["department_capability"]
        for item in pack["tool_execution_queue"]["tool_execution_items"]
        if item["department_id"] == "marketing"
    ]

    assert "campaign.plan" in marketing_capabilities
    assert "social.post_draft" in marketing_capabilities
    assert "google_business_profile.post_draft" in marketing_capabilities
    assert "advert.copy_draft" in marketing_capabilities
    assert "landing_page.copy" in marketing_capabilities
    assert "content_calendar.create" in marketing_capabilities
    assert "campaign_pack.pdf" in marketing_capabilities


def test_phase23q_supporting_departments_have_finance_sales_operations_work():
    pack = create_home_fixed_marketing_fixture_pack(evaluation_time=100)

    department_ids = {
        item["department_id"]
        for item in pack["tool_execution_queue"]["tool_execution_items"]
    }

    assert "finance" in department_ids
    assert "sales" in department_ids
    assert "operations" in department_ids


def test_phase23q_live_marketing_actions_are_approval_blocked():
    pack = create_home_fixed_marketing_fixture_pack(evaluation_time=100)

    live_items = [
        item
        for item in pack["tool_execution_queue"]["tool_execution_items"]
        if item["department_capability"] in MARKETING_BLOCKED_LIVE_ACTIONS
    ]

    assert live_items
    assert all(item["status"] == "waiting_approval" for item in live_items)
    assert all(item["execution_allowed"] is False for item in live_items)
    assert all(item["approval_required"] is True for item in live_items)
    assert all(item["live_external_side_effect"] is True for item in live_items)


def test_phase23q_safe_or_staged_work_comes_before_live_execution():
    pack = create_home_fixed_marketing_fixture_pack(evaluation_time=100)

    assert pack["safe_or_staged_first"] is True
    assert pack["live_external_side_effects_performed"] is False
    assert pack["tool_execution_queue"]["live_execution_allowed"] is False


def test_phase23q_home_fixed_is_fixture_not_universal_hardcode():
    generic_pack = create_marketing_department_pack(
        user_goal="Create a marketing campaign for a plumbing business",
        business_id="plumbing-demo",
        mission_id="mission_generic",
        mission_run_id="run_001",
        business_context={
            "business_name": "Plumbing Demo",
            "vertical": "plumbing",
            "service_area": "generic",
        },
        evaluation_time=100,
    )

    assert generic_pack["business_id"] == "plumbing-demo"
    assert generic_pack["primary_department"] == "marketing"
    assert generic_pack["business_context"]["business_name"] == "Plumbing Demo"
    assert generic_pack["business_context"]["business_name"] != "Home Fixed"


def test_phase23q_safe_artifact_templates_are_first_class():
    labels = [item["artifact_label"] for item in MARKETING_SAFE_ARTIFACTS]

    assert "Facebook post pack" in labels
    assert "Google Business Profile post drafts" in labels
    assert "Advert copy variants" in labels
    assert "30/60/90 content calendar" in labels
    assert "Campaign approval PDF pack" in labels


def test_phase23q_pack_hash_is_deterministic():
    a = create_home_fixed_marketing_fixture_pack(evaluation_time=100)
    b = create_home_fixed_marketing_fixture_pack(evaluation_time=100)

    assert a["pack_hash"] == b["pack_hash"]
    assert a["tool_execution_queue"]["tool_queue_hash"] == b["tool_execution_queue"]["tool_queue_hash"]
