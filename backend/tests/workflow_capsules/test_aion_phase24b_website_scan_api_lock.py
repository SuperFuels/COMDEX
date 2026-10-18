from pathlib import Path


ROUTER = Path("backend/api/local_node_router.py").read_text()
GATE = Path("backend/services/aion_mission_mode/website_scan_usage_gate.py").read_text()


def test_phase24b_website_scan_routes_exist():
    assert '"/api/aion/small-business/website-scan"' in ROUTER
    assert '"/aion/small-business/website-scan"' in ROUTER


def test_phase24b_website_scan_routes_use_openai_foundation_service_and_usage_gate():
    assert "scan_website_with_openai" in ROUTER
    assert "website_scan_allowed" in ROUTER
    assert "login_required_before_openai_scan" in GATE
    assert "AION_REQUIRE_SCAN_LOGIN" in GATE


def test_design_system_evidence_scan_does_not_require_paid_llm_capacity():
    assert 'payload.get("evidence_only") is True' in ROUTER
    assert "collect_website_evidence" in ROUTER
    assert '"provider": "deterministic_public_website"' in ROUTER
    assert '"live_external_side_effect": False' in ROUTER
    assert '"css_custom_properties"' in ROUTER
    assert '"font_roles"' in ROUTER
