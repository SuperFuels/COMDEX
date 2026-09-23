from pathlib import Path

from backend.modules.aion_gateway.agentmap_human_review_simulation_bridge import (
    build_agentmap_human_review_simulation_bridge_preview,
    build_agentmap_human_review_simulation_bridge_summary,
)


MODULE = Path("backend/modules/aion_gateway/agentmap_human_review_simulation_bridge.py")


def test_phase14f_human_review_bridge_module_exists():
    assert MODULE.exists()


def test_human_review_bridge_passes_default_synthetic_flow():
    preview = build_agentmap_human_review_simulation_bridge_preview()

    assert preview["bridge_version"] == "aion.agentmap.human_review_bridge.v0.1"
    assert preview["passed"] is True
    assert preview["status"] == "passed"
    assert preview["checks"]["synthetic_simulation_passed"] is True
    assert preview["checks"]["review_request_created_as_preview"] is True
    assert preview["checks"]["review_request_waiting_human"] is True
    assert len(preview["bridge_hash"]) == 64
    assert len(preview["summary_hash"]) == 64


def test_human_review_bridge_creates_preview_review_request_only():
    preview = build_agentmap_human_review_simulation_bridge_preview()
    review = preview["review_request"]

    assert review["status"] == "waiting_human_review"
    assert review["preview_only"] is True
    assert review["synthetic_only"] is True
    assert review["human_review_required"] is True
    assert review["live_execution_authorized"] is False
    assert review["operator_action_required"] == "review_preview"
    assert "approve_preview_only" in review["allowed_preview_actions"]


def test_human_review_bridge_blocks_live_actions():
    preview = build_agentmap_human_review_simulation_bridge_preview()

    assert preview["safety_profile"]["live_execution_enabled"] is False
    assert preview["safety_profile"]["approval_required_before_live_execution"] is True
    assert not any(preview["side_effects"].values())

    blocked = preview["review_request"]["blocked_live_actions"]
    for item in [
        "booking",
        "payment",
        "escrow",
        "dispatch",
        "external_message",
        "live_chain_write",
    ]:
        assert item in blocked


def test_human_review_bridge_is_deterministic():
    first = build_agentmap_human_review_simulation_bridge_preview()
    second = build_agentmap_human_review_simulation_bridge_preview()

    assert first["bridge_hash"] == second["bridge_hash"]
    assert first["summary_hash"] == second["summary_hash"]
    assert first["review_request"]["review_request_id"] == second["review_request"]["review_request_id"]


def test_human_review_bridge_hash_changes_when_identity_changes():
    base = build_agentmap_human_review_simulation_bridge_preview()
    changed = build_agentmap_human_review_simulation_bridge_preview(
        {
            "business_id": "other_business",
            "business_name": "Other Business",
            "vertical_key": "legal",
        }
    )

    assert base["bridge_hash"] != changed["bridge_hash"]
    assert base["summary_hash"] != changed["summary_hash"]


def test_human_review_bridge_summary_is_minimal_and_safe():
    summary = build_agentmap_human_review_simulation_bridge_summary()

    assert summary["passed"] is True
    assert summary["review_status"] == "waiting_human_review"
    assert summary["human_review_required"] is True
    assert summary["live_execution_enabled"] is False
    assert "review_request_id" in summary
    assert "side_effects" not in summary
    assert "allowed_preview_actions" not in summary


def test_human_review_bridge_module_has_no_live_side_effects():
    text = MODULE.read_text()

    forbidden = [
        "requests.get(",
        "httpx.get(",
        "urllib.request",
        "send_email(",
        "send_sms(",
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
