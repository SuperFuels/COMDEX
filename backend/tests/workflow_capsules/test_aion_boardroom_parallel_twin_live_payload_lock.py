from __future__ import annotations

from backend.modules.aion_gateway.boardroom_parallel_twin_payload import (
    BOARDROOM_PARALLEL_TWIN_PAYLOAD_VERSION,
    build_boardroom_parallel_twin_payload,
    build_boardroom_parallel_twin_summary,
)


def _payload() -> dict:
    out = build_boardroom_parallel_twin_payload()
    assert out["ok"] is True
    assert out["status"] == "preview_ready"
    return out["payload"]


def test_boardroom_parallel_twin_payload_has_version_and_identity():
    p = _payload()

    assert p["payload_version"] == BOARDROOM_PARALLEL_TWIN_PAYLOAD_VERSION
    assert p["business_id"] == "home_fixed"
    assert p["business_name"] == "Home Fixed"
    assert p["vertical_key"] == "home_repair"
    assert p["status"] == "preview_ready"
    assert isinstance(p["payload_hash"], str) and len(p["payload_hash"]) == 64


def test_boardroom_parallel_twin_payload_contains_required_sections():
    p = _payload()

    for key in [
        "machine_catalog",
        "machine_cart",
        "quote_preview",
        "fulfilment_job_preview",
        "settlement_readiness",
        "proof_receipt",
        "exception_recovery",
        "machine_trace_preview",
    ]:
        assert key in p
        assert isinstance(p[key], dict)


def test_boardroom_parallel_twin_payload_is_visibility_only():
    p = _payload()
    safety = p["safety"]

    assert safety["visibility_only"] is True
    assert safety["human_review_required"] is True
    assert safety["autonomous_execution_allowed"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_move_money"] is False
    assert safety["would_move_pho"] is False
    assert safety["would_require_wallet"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["public_a2a_route_exposed"] is False


def test_boardroom_parallel_twin_summary_exposes_section_presence():
    s = build_boardroom_parallel_twin_summary()

    assert s["ok"] is True
    assert s["business_name"] == "Home Fixed"
    assert s["has_machine_catalog"] is True
    assert s["has_machine_cart"] is True
    assert s["has_quote_preview"] is True
    assert s["has_fulfilment_job_preview"] is True
    assert s["has_settlement_readiness"] is True
    assert s["has_proof_receipt"] is True
    assert s["has_exception_recovery"] is True
    assert s["has_machine_trace_preview"] is True


def test_boardroom_parallel_twin_payload_hash_changes_with_job_id():
    p1 = build_boardroom_parallel_twin_payload(job_id="home_fixed_job_001")["payload"]
    p2 = build_boardroom_parallel_twin_payload(job_id="home_fixed_job_002")["payload"]

    assert p1["payload_hash"] != p2["payload_hash"]


def test_boardroom_parallel_twin_payload_does_not_expose_public_route():
    p = _payload()

    assert p["safety"]["public_a2a_route_exposed"] is False
