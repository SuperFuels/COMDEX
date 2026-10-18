from backend.modules.aion_gateway.parallel_discovery import (
    DISCOVERY_PROTOCOL_VERSION,
    build_parallel_discovery_document,
)


def _doc():
    return build_parallel_discovery_document(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
    )


def test_discovery_document_builds_for_home_fixed():
    out = _doc()

    assert out["ok"] is True
    assert out["status"] == "preview"

    doc = out["document"]
    assert doc["protocol_version"] == DISCOVERY_PROTOCOL_VERSION
    assert doc["business_id"] == "home_fixed"
    assert doc["business_name"] == "Home Fixed"
    assert doc["vertical_key"] == "home_repair"


def test_discovery_document_lists_future_endpoint_placeholders():
    doc = _doc()["document"]
    endpoints = doc["endpoints"]

    for key in [
        "discovery",
        "ai_agent_discovery",
        "catalog",
        "capabilities",
        "quote",
        "trace",
        "proof",
    ]:
        assert key in endpoints
        assert endpoints[key]["public_route_exposed"] is False


def test_discovery_document_references_well_known_routes_but_does_not_expose_them():
    out = _doc()
    endpoints = out["document"]["endpoints"]

    assert endpoints["discovery"]["uri"] == "/.well-known/aion-agent"
    assert endpoints["ai_agent_discovery"]["uri"] == "/.well-known/ai-agent"
    assert out["public_route_exposed"] is False
    assert out["would_expose_well_known_route"] is False
    assert out["would_create_public_api"] is False


def test_discovery_document_includes_auth_and_rate_limit_placeholders():
    doc = _doc()["document"]

    assert doc["auth_policy"]["auth_required"] is True
    assert "api_key_later" in doc["auth_policy"]["supported_modes"]
    assert "signed_agent_later" in doc["auth_policy"]["supported_modes"]
    assert doc["auth_policy"]["public_write_allowed"] is False
    assert doc["rate_limit_policy"]["rate_limit_required"] is True
    assert doc["rate_limit_policy"]["abuse_protection_required"] is True


def test_discovery_hash_is_deterministic():
    first = _doc()["document"]["discovery_hash"]
    second = _doc()["document"]["discovery_hash"]

    assert first == second
    assert isinstance(first, str)
    assert len(first) == 64


def test_discovery_hash_changes_when_business_changes():
    first = _doc()["document"]["discovery_hash"]
    second = build_parallel_discovery_document(
        business_id="home_fixed_alt",
        business_name="Home Fixed",
        vertical_key="home_repair",
    )["document"]["discovery_hash"]

    assert first != second


def test_missing_business_id_blocks_preview():
    out = build_parallel_discovery_document(business_id="")

    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert "missing_business_id" in out["blocked_reasons"]


def test_discovery_has_no_side_effects():
    out = _doc()

    assert out["would_execute_goal_engine"] is False
    assert out["would_create_booking"] is False
    assert out["would_create_payment"] is False
    assert out["would_create_escrow"] is False
    assert out["would_move_money"] is False
