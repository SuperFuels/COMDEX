from backend.modules.aion_gateway.a2a_api import (
    A2A_ALLOWED_PREVIEW_ENDPOINTS,
    A2A_API_VERSION,
    build_a2a_endpoint_preview,
    build_a2a_namespace_summary,
    build_guarded_a2a_namespace_preview,
)


def test_guarded_a2a_namespace_has_version_and_identity():
    p = build_guarded_a2a_namespace_preview()

    assert p["ok"] is True
    assert p["status"] == "guarded_a2a_namespace_preview_ready"
    assert p["contract_version"] == A2A_API_VERSION
    assert p["namespace"] == "/api/aion/a2a/*"
    assert p["business_id"] == "home_fixed"
    assert p["vertical_key"] == "home_repair"


def test_guarded_a2a_namespace_lists_required_endpoints():
    p = build_guarded_a2a_namespace_preview()
    keys = {e["endpoint_key"] for e in p["endpoints"]}

    assert keys == A2A_ALLOWED_PREVIEW_ENDPOINTS

    for key in [
        "business_capabilities",
        "business_machine_catalog",
        "business_availability",
        "machine_cart_quote_request_preview",
        "job_request_preview",
        "job_trace",
        "job_evidence",
        "settlement_readiness",
        "proof_commitment",
        "proof_receipt",
        "trust_summary",
    ]:
        assert key in keys


def test_guarded_a2a_namespace_is_preview_only_and_guarded():
    p = build_guarded_a2a_namespace_preview()

    assert p["guarded"] is True
    assert p["preview_only"] is True
    assert p["public_route_exposed"] is False
    assert p["requires_auth"] is True
    assert p["auth_mode"] == "api_key_or_signed_agent_preview"
    assert p["deterministic_responses"] is True
    assert p["schema_versioned"] is True


def test_guarded_a2a_namespace_has_no_side_effects():
    safety = build_guarded_a2a_namespace_preview()["safety"]

    assert safety["would_execute_workflow"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_move_money"] is False
    assert safety["would_move_pho"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["public_route_exposed"] is False


def test_endpoint_preview_methods_are_deterministic():
    get_endpoint = build_a2a_endpoint_preview(endpoint_key="business_capabilities")
    post_endpoint = build_a2a_endpoint_preview(endpoint_key="machine_cart_quote_request_preview")

    assert get_endpoint["status"] == "preview_ready"
    assert get_endpoint["endpoint"]["method"] == "GET"
    assert get_endpoint["endpoint"]["path"] == "/api/aion/a2a/home_fixed/business_capabilities"

    assert post_endpoint["status"] == "preview_ready"
    assert post_endpoint["endpoint"]["method"] == "POST"
    assert post_endpoint["endpoint"]["path"] == "/api/aion/a2a/home_fixed/machine_cart_quote_request_preview"


def test_endpoint_preview_blocks_unsupported_endpoint():
    out = build_a2a_endpoint_preview(endpoint_key="live_payment_capture")

    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert "unsupported_a2a_endpoint" in out["endpoint"]["blocked_reasons"]


def test_namespace_hash_is_stable():
    p1 = build_guarded_a2a_namespace_preview()
    p2 = build_guarded_a2a_namespace_preview()

    assert p1["namespace_hash"] == p2["namespace_hash"]


def test_namespace_hash_changes_with_business_identity():
    p1 = build_guarded_a2a_namespace_preview(business_id="home_fixed")
    p2 = build_guarded_a2a_namespace_preview(business_id="other_business")

    assert p1["namespace_hash"] != p2["namespace_hash"]


def test_namespace_summary_is_compact():
    s = build_a2a_namespace_summary()

    assert s["ok"] is True
    assert s["status"] == "a2a_namespace_summary_ready"
    assert s["endpoint_count"] == len(A2A_ALLOWED_PREVIEW_ENDPOINTS)
    assert "trust_summary" in s["endpoint_keys"]
    assert s["guarded"] is True
    assert s["preview_only"] is True
    assert s["public_route_exposed"] is False
