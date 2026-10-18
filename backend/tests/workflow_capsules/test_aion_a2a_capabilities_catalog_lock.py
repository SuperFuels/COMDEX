from backend.modules.aion_gateway.a2a_capabilities import (
    A2A_CAPABILITIES_VERSION,
    build_a2a_capabilities_catalog_bundle,
    build_business_capabilities_preview,
    build_business_machine_catalog_preview,
)


def test_business_capabilities_preview_has_identity_and_version():
    p = build_business_capabilities_preview()

    assert p["ok"] is True
    assert p["status"] == "preview_ready"
    assert p["contract_version"] == A2A_CAPABILITIES_VERSION
    assert p["endpoint_key"] == "business_capabilities"
    assert p["method"] == "GET"
    assert p["business_id"] == "home_fixed"
    assert p["business_name"] == "Home Fixed"
    assert p["vertical_key"] == "home_repair"
    assert p["industry_key"] == "trades"


def test_business_capabilities_are_universal_not_trade_hardcoded():
    p = build_business_capabilities_preview()

    assert p["universal_gateway"] is True
    assert p["vertical_adapter_required"] is True
    assert "capability_profile" in p
    assert "service_categories" in p
    assert "accepted_protocols" in p
    assert "authentication" in p
    assert "schemas" in p


def test_business_capabilities_advertise_protocols_and_auth_preview():
    p = build_business_capabilities_preview()

    assert "aion.a2a.preview.v0" in p["accepted_protocols"]
    assert "aion.machine_cart.preview.v0" in p["accepted_protocols"]
    assert "aion.proof_receipt.preview.v0" in p["accepted_protocols"]
    assert p["authentication"]["required"] is True
    assert p["authentication"]["mode"] == "api_key_or_signed_agent_preview"
    assert p["authentication"]["production_auth_enforced"] is False


def test_machine_catalog_preview_has_identity_and_catalog_items():
    p = build_business_machine_catalog_preview()

    assert p["ok"] is True
    assert p["status"] == "preview_ready"
    assert p["contract_version"] == A2A_CAPABILITIES_VERSION
    assert p["endpoint_key"] == "business_machine_catalog"
    assert p["method"] == "GET"
    assert p["business_id"] == "home_fixed"
    assert p["vertical_key"] == "home_repair"
    assert p["industry_key"] == "trades"
    assert len(p["items"]) >= 3


def test_machine_catalog_items_are_machine_readable():
    p = build_business_machine_catalog_preview()

    for item in p["items"]:
        assert item["service_id"]
        assert item["label"]
        assert item["category"]
        assert item["request_schema"]
        assert item["quote_schema"]
        assert item["evidence_schema"]
        assert item["requires_human_review"] is True
        assert item["live_booking_supported"] is False


def test_catalog_notes_explain_vertical_adapter_boundary():
    p = build_business_machine_catalog_preview()
    joined = " ".join(p["vertical_mapping_notes"])

    assert "Home Fixed" in joined
    assert "universal" in joined
    assert "vertical adapter" in joined
    assert "Legal" in joined
    assert "accounting" in joined


def test_phase_11b_safety_has_no_side_effects():
    for p in [
        build_business_capabilities_preview(),
        build_business_machine_catalog_preview(),
        build_a2a_capabilities_catalog_bundle(),
    ]:
        safety = p["safety"]
        assert safety["guarded"] is True
        assert safety["preview_only"] is True
        assert safety["public_route_exposed"] is False
        assert safety["requires_auth"] is True
        assert safety["would_execute_workflow"] is False
        assert safety["would_create_booking"] is False
        assert safety["would_move_money"] is False
        assert safety["would_move_pho"] is False
        assert safety["would_create_payment"] is False
        assert safety["would_create_escrow"] is False
        assert safety["would_send_external_message"] is False


def test_capability_and_catalog_hashes_are_stable():
    c1 = build_business_capabilities_preview()
    c2 = build_business_capabilities_preview()
    m1 = build_business_machine_catalog_preview()
    m2 = build_business_machine_catalog_preview()

    assert c1["capabilities_hash"] == c2["capabilities_hash"]
    assert m1["catalog_hash"] == m2["catalog_hash"]


def test_hashes_change_with_vertical_identity():
    c1 = build_business_capabilities_preview(vertical_key="home_repair", industry_key="trades")
    c2 = build_business_capabilities_preview(vertical_key="legal_services", industry_key="professional_services")

    assert c1["capabilities_hash"] != c2["capabilities_hash"]


def test_capabilities_catalog_bundle_contains_both_responses():
    b = build_a2a_capabilities_catalog_bundle()

    assert b["ok"] is True
    assert b["status"] == "preview_ready"
    assert b["business_id"] == "home_fixed"
    assert b["vertical_key"] == "home_repair"
    assert b["industry_key"] == "trades"
    assert b["universal_gateway"] is True
    assert b["capabilities"]["endpoint_key"] == "business_capabilities"
    assert b["machine_catalog"]["endpoint_key"] == "business_machine_catalog"
    assert b["bundle_hash"]
