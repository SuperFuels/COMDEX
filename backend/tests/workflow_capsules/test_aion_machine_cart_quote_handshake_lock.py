from backend.modules.aion_gateway.machine_cart import (
    MACHINE_CART_PROTOCOL_VERSION,
    MachineCartConstraint,
    MachineCartLineItem,
    MachineCartRequest,
    build_home_fixed_machine_cart_quote_preview,
    preview_machine_cart_quote,
)


def test_home_fixed_machine_cart_valid_request_returns_quote_preview():
    out = build_home_fixed_machine_cart_quote_preview(
        service_key="roof_leak_repair",
        location_town="Arboleas",
        required_evidence=["leak_photo", "completion_photo"],
    )

    assert out["ok"] is True
    assert out["status"] == "preview_ready"
    assert out["quote_preview"]["protocol_version"] == MACHINE_CART_PROTOCOL_VERSION
    assert out["quote_preview"]["business_id"] == "home_fixed"
    assert len(out["quote_preview"]["quote_hash"]) == 64


def test_machine_cart_returns_fulfilment_job_preview_link_without_creating_job():
    out = build_home_fixed_machine_cart_quote_preview(
        required_evidence=["leak_photo", "completion_photo"],
    )

    link = out["fulfilment_job_preview_link"]
    assert link["would_create_fulfilment_job"] is False
    assert link["business_id"] == "home_fixed"
    assert "roof_leak_repair" in link["service_keys"]


def test_machine_cart_blocks_unsupported_service():
    out = build_home_fixed_machine_cart_quote_preview(service_key="spaceship_repair")

    assert out["ok"] is False
    assert out["status"] == "blocked"
    assert "unsupported_service:spaceship_repair" in out["blocked_reasons"]


def test_machine_cart_blocks_unsupported_location():
    out = build_home_fixed_machine_cart_quote_preview(location_town="Madrid")

    assert out["ok"] is False
    assert "unsupported_location" in out["blocked_reasons"]


def test_machine_cart_warns_when_required_evidence_missing():
    out = build_home_fixed_machine_cart_quote_preview(
        service_key="roof_leak_repair",
        location_town="Arboleas",
        required_evidence=[],
    )

    assert out["ok"] is True
    assert "missing_required_evidence_for_final_execution" in out["quote_preview"]["warnings"]
    assert "leak_photo" in out["quote_preview"]["missing_evidence"]


def test_machine_cart_hash_is_stable_for_same_payload():
    req_a = MachineCartRequest(
        business_id="home_fixed",
        line_items=[MachineCartLineItem(service_key="general_home_repair")],
        constraints=MachineCartConstraint(location_town="Albox"),
        created_at_ms=123,
    )
    req_b = MachineCartRequest(
        business_id="home_fixed",
        line_items=[MachineCartLineItem(service_key="general_home_repair")],
        constraints=MachineCartConstraint(location_town="Albox"),
        created_at_ms=123,
    )

    assert req_a.to_dict()["cart_hash"] == req_b.to_dict()["cart_hash"]


def test_machine_cart_quote_hash_changes_when_service_changes():
    first = build_home_fixed_machine_cart_quote_preview(service_key="general_home_repair")
    second = build_home_fixed_machine_cart_quote_preview(service_key="painting_decorating")

    assert first["quote_preview"]["quote_hash"] != second["quote_preview"]["quote_hash"]


def test_machine_cart_has_no_live_side_effects():
    out = build_home_fixed_machine_cart_quote_preview()
    safety = out["quote_preview"]["safety"]

    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_execute_goal_engine"] is False
    assert safety["would_expose_public_route"] is False
    assert safety["would_move_money"] is False
