from pathlib import Path

from backend.modules.aion_gateway.agentmap_discovery_endpoint import (
    build_agentmap_discovery_endpoint_preview,
)
from backend.modules.aion_gateway.agentmap_live_verification import (
    build_agentmap_live_verification_preview,
    build_agentmap_live_verification_summary,
)


MODULE = Path("backend/modules/aion_gateway/agentmap_live_verification.py")


def test_phase14d_live_verification_module_exists():
    assert MODULE.exists()


def test_agentmap_live_verification_accepts_valid_preview_payload():
    endpoint = build_agentmap_discovery_endpoint_preview()
    preview = build_agentmap_live_verification_preview(
        {
            "observed_agentmap_payload": endpoint,
            "expected_agentmap_hash": endpoint["agentmap_hash"],
            "expected_endpoint_hash": endpoint["endpoint_hash"],
            "observed_status_code": 200,
            "observed_content_type": "application/json",
        }
    )

    assert preview["verification_version"] == "aion.agentmap.verification.v0.1"
    assert preview["verified"] is True
    assert preview["status"] == "verified"
    assert preview["checks"]["agentmap_hash_matches_expected"] is True
    assert preview["checks"]["schema_valid"] is True
    assert len(preview["verification_hash"]) == 64
    assert len(preview["summary_hash"]) == 64


def test_agentmap_live_verification_rejects_hash_mismatch():
    endpoint = build_agentmap_discovery_endpoint_preview()
    bad_payload = dict(endpoint)
    bad_payload["agentmap_hash"] = "bad_hash"

    preview = build_agentmap_live_verification_preview(
        {
            "observed_agentmap_payload": bad_payload,
            "observed_status_code": 200,
            "observed_content_type": "application/json",
        }
    )

    assert preview["verified"] is False
    assert preview["status"] == "not_verified"
    assert preview["checks"]["agentmap_hash_matches_expected"] is False


def test_agentmap_live_verification_is_deterministic():
    endpoint = build_agentmap_discovery_endpoint_preview()
    request = {
        "observed_agentmap_payload": endpoint,
        "expected_agentmap_hash": endpoint["agentmap_hash"],
        "expected_endpoint_hash": endpoint["endpoint_hash"],
        "observed_status_code": 200,
        "observed_content_type": "application/json",
    }

    first = build_agentmap_live_verification_preview(request)
    second = build_agentmap_live_verification_preview(request)

    assert first["verification_hash"] == second["verification_hash"]
    assert first["summary_hash"] == second["summary_hash"]


def test_agentmap_live_verification_hash_changes_when_identity_changes():
    endpoint = build_agentmap_discovery_endpoint_preview()
    base = build_agentmap_live_verification_preview(
        {
            "observed_agentmap_payload": endpoint,
            "expected_agentmap_hash": endpoint["agentmap_hash"],
            "expected_endpoint_hash": endpoint["endpoint_hash"],
            "observed_status_code": 200,
            "observed_content_type": "application/json",
        }
    )

    changed_endpoint = build_agentmap_discovery_endpoint_preview(
        {
            "business_id": "other_business",
            "business_name": "Other Business",
            "vertical_key": "legal",
        }
    )
    changed = build_agentmap_live_verification_preview(
        {
            "business_id": "other_business",
            "business_name": "Other Business",
            "vertical_key": "legal",
            "observed_agentmap_payload": changed_endpoint,
            "expected_agentmap_hash": changed_endpoint["agentmap_hash"],
            "expected_endpoint_hash": changed_endpoint["endpoint_hash"],
            "observed_status_code": 200,
            "observed_content_type": "application/json",
        }
    )

    assert base["verification_hash"] != changed["verification_hash"]


def test_agentmap_live_verification_safety_boundary_blocks_live_actions():
    preview = build_agentmap_live_verification_preview()
    safety = preview["safety_profile"]

    assert safety["preview_only"] is True
    assert safety["read_only"] is True
    assert safety["human_review_required"] is True
    assert safety["public_route_mounted"] is False
    assert safety["live_side_effects_enabled"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_dispatch_job"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False


def test_agentmap_live_verification_summary_is_minimal():
    summary = build_agentmap_live_verification_summary()

    assert "observed" not in summary
    assert "checks" not in summary
    assert "verification_hash" in summary
    assert "summary_hash" in summary
    assert summary["preview_only"] is True
    assert summary["read_only"] is True


def test_agentmap_live_verification_module_has_no_live_side_effects():
    text = MODULE.read_text()

    forbidden = [
        "requests.get(",
        "httpx.get(",
        "urllib.request",
        "send_email",
        "send_sms",
        "create_booking(",
        "capture_payment(",
        "release_escrow(",
        "dispatch_job(",
        "write_live_chain(",
        "uuid.uuid4(",
        "random.random(",
        "secrets.token",
    ]

    for item in forbidden:
        assert item not in text
