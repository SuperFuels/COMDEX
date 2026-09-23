from backend.services.aion_mission_mode.department_capability_map import (
    create_department_capability_map,
    get_department_capabilities,
    is_removed_placeholder_department,
    is_supported_department,
)
from backend.services.aion_mission_mode.business_function_router import (
    route_business_function,
    summarize_department_route,
)


def test_phase23m_supported_departments_are_correct_first_class_set():
    capability_map = create_department_capability_map()

    assert capability_map["supported_department_ids"] == [
        "marketing",
        "pilot",
        "sales",
        "finance",
        "operations",
        "support",
        "builder",
    ]

    for removed in ["ceo", "coo", "core", "hr", "aion"]:
        assert is_removed_placeholder_department(removed) is True
        assert is_supported_department(removed) is False


def test_phase23m_marketing_request_routes_to_marketing_with_business_support_departments():
    route = route_business_function(
        user_goal="Create a marketing campaign for Home Fixed with Facebook posts and adverts",
        business_id="home-fixed",
        mission_id="mission_marketing",
        mission_run_id="run_001",
    )

    assert route["primary_department"] == "marketing"
    assert route["supporting_departments"] == ["finance", "sales", "operations"]
    assert route["department_routes"][0]["department_id"] == "marketing"
    assert route["department_routes"][0]["capability"] == "campaign.plan"
    assert route["department_route_hash"].startswith("sha256:")


def test_phase23m_sales_request_routes_to_sales():
    route = route_business_function(
        user_goal="Create a sales pipeline and quote follow-up sequence for new leads",
        business_id="home-fixed",
        mission_id="mission_sales",
        mission_run_id="run_001",
    )

    assert route["primary_department"] == "sales"
    assert route["department_routes"][0]["capability"] == "pipeline.plan"


def test_phase23m_finance_request_routes_to_finance():
    route = route_business_function(
        user_goal="Create a cashflow forecast, pricing calculator and ROI model",
        business_id="home-fixed",
        mission_id="mission_finance",
        mission_run_id="run_001",
    )

    assert route["primary_department"] == "finance"
    assert "forecast.create" in get_department_capabilities("finance")


def test_phase23m_operations_request_routes_to_operations():
    route = route_business_function(
        user_goal="Create a job workflow, SOP and evidence checklist",
        business_id="home-fixed",
        mission_id="mission_ops",
        mission_run_id="run_001",
    )

    assert route["primary_department"] == "operations"
    assert route["department_routes"][0]["capability"] == "workflow.create"


def test_phase23m_support_request_routes_to_support():
    route = route_business_function(
        user_goal="Draft a customer reply, FAQ and aftercare response",
        business_id="home-fixed",
        mission_id="mission_support",
        mission_run_id="run_001",
    )

    assert route["primary_department"] == "support"
    assert route["department_routes"][0]["capability"] == "customer_reply.draft"


def test_phase23m_random_build_request_routes_to_builder():
    route = route_business_function(
        user_goal="Build me a PDF quote template and a simple calculator",
        business_id="home-fixed",
        mission_id="mission_builder",
        mission_run_id="run_001",
    )

    assert route["primary_department"] == "builder"
    assert route["department_routes"][0]["capability"] == "document.create"
    assert "calculator.create" in get_department_capabilities("builder")


def test_phase23m_removed_placeholder_requested_department_is_rejected_and_rerouted():
    route = route_business_function(
        user_goal="Create a marketing campaign",
        requested_department="CEO",
        business_id="home-fixed",
        mission_id="mission_removed_placeholder",
        mission_run_id="run_001",
    )

    assert route["rejected_department"] == "ceo"
    assert route["primary_department"] == "marketing"


def test_phase23m_route_hash_is_deterministic():
    a = route_business_function(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_hash",
        mission_run_id="run_001",
    )
    b = route_business_function(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_hash",
        mission_run_id="run_001",
    )

    assert a["department_route_hash"] == b["department_route_hash"]

    sa = summarize_department_route(a)
    sb = summarize_department_route(b)

    assert sa["summary_hash"] == sb["summary_hash"]
    assert sa["route_count"] == 4
