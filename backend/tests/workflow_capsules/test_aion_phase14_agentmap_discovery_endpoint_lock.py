from pathlib import Path

from backend.modules.aion_gateway.agentmap_discovery_endpoint import (
    CANONICAL_AGENTMAP_PATH,
    WELL_KNOWN_AGENTMAP_PATH,
    build_agentmap_discovery_endpoint_preview,
    build_agentmap_discovery_endpoint_summary,
)


ROOT = Path(__file__).resolve().parents[3]


def test_agentmap_discovery_endpoint_declares_read_only_paths():
    preview = build_agentmap_discovery_endpoint_preview()

    assert preview["status"] == "agentmap_discovery_endpoint_preview_only"
    assert preview["paths"]["canonical"] == CANONICAL_AGENTMAP_PATH
    assert preview["paths"]["well_known"] == WELL_KNOWN_AGENTMAP_PATH
    assert preview["paths"]["canonical"] == "/agentmap.json"
    assert preview["paths"]["well_known"] == "/.well-known/agentmap.json"

    assert preview["http_preview"]["allowed_methods"] == ["GET", "HEAD"]
    assert "POST" in preview["http_preview"]["forbidden_write_methods"]
    assert preview["http_preview"]["route_exposed"] is False
    assert preview["http_preview"]["public_route_mounted"] is False


def test_agentmap_discovery_endpoint_includes_hashes_and_manifest():
    preview = build_agentmap_discovery_endpoint_preview()

    assert preview["agentmap_manifest"]
    assert preview["agentmap_hash"]
    assert preview["endpoint_hash"]
    assert preview["summary_hash"]

    again = build_agentmap_discovery_endpoint_preview()
    assert preview["endpoint_hash"] == again["endpoint_hash"]
    assert preview["summary_hash"] == again["summary_hash"]


def test_agentmap_discovery_endpoint_hash_changes_when_identity_changes():
    base = build_agentmap_discovery_endpoint_preview({"business_id": "home_fixed"})
    changed = build_agentmap_discovery_endpoint_preview(
        {
            "business_id": "legal_demo",
            "business_name": "Legal Demo",
            "vertical_key": "legal",
        }
    )

    assert base["endpoint_hash"] != changed["endpoint_hash"]


def test_agentmap_discovery_endpoint_exposes_safe_capability_routes_only():
    preview = build_agentmap_discovery_endpoint_preview()
    routes = preview["safe_capability_routes"]

    assert routes
    assert "agentmap_manifest" in routes
    assert "proof_receipt_lookup" in routes
    assert "trust_summary" in routes

    for route in routes.values():
        assert route["method"] == "GET"
        assert route["read_only"] is True
        assert route["side_effects_enabled"] is False
        assert route["requires_human_review_before_execution"] is True
        assert route["input_schema_ref"].startswith("aion.schema.")
        assert route["output_schema_ref"].startswith("aion.schema.")
        assert route["route_type"].endswith("_preview")


def test_agentmap_discovery_endpoint_safety_profile_blocks_live_side_effects():
    preview = build_agentmap_discovery_endpoint_preview()
    safety = preview["safety_profile"]

    assert safety["preview_only"] is True
    assert safety["read_only"] is True
    assert safety["human_review_required"] is True
    assert safety["live_side_effects_enabled"] is False
    assert safety["public_route_mounted"] is False
    assert safety["unauthenticated_public_write_route_exposed"] is False

    assert safety["would_create_booking"] is False
    assert safety["would_create_live_job"] is False
    assert safety["would_execute_goal_engine"] is False
    assert safety["would_move_money"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_release_funds"] is False
    assert safety["would_dispatch_work"] is False
    assert safety["would_send_external_messages"] is False
    assert safety["would_write_live_chain"] is False


def test_agentmap_discovery_endpoint_summary_is_minimal_and_read_only():
    summary = build_agentmap_discovery_endpoint_summary()

    assert summary["canonical_path"] == "/agentmap.json"
    assert summary["well_known_path"] == "/.well-known/agentmap.json"
    assert summary["agentmap_hash"]
    assert summary["endpoint_hash"]
    assert summary["summary_hash"]
    assert summary["preview_only"] is True
    assert summary["read_only"] is True
    assert summary["human_review_required"] is True
    assert summary["public_route_mounted"] is False
    assert summary["live_side_effects_enabled"] is False


def test_agentmap_discovery_endpoint_module_has_no_live_provider_coupling():
    module = ROOT / "backend/modules/aion_gateway/agentmap_discovery_endpoint.py"
    text = module.read_text().lower()

    forbidden = [
        "smtplib",
        "twilio",
        "sendgrid",
        "mailgun",
        "postmark",
        "stripe",
        "revolut",
        "paypal",
        "create_payment(",
        "capture_payment(",
        "release_escrow(",
        "transfer_funds(",
        "send_email(",
        "send_sms(",
        "post_social(",
        "dispatch_job(",
        "uuid.uuid4(",
        "random.random(",
        "secrets.token",
    ]

    for term in forbidden:
        assert term not in text
