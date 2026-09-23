from pathlib import Path

from backend.modules.aion_gateway.agentmap_synthetic_agent_simulation import (
    SIMULATION_VERSION,
    build_synthetic_inbound_agent_simulation_preview,
    build_synthetic_inbound_agent_simulation_summary,
)


MODULE = Path("backend/modules/aion_gateway/agentmap_synthetic_agent_simulation.py")


def test_phase14e_synthetic_agent_simulation_module_exists():
    assert MODULE.exists()


def test_synthetic_agent_simulation_passes_for_default_home_fixed_flow():
    preview = build_synthetic_inbound_agent_simulation_preview()

    assert preview["simulation_version"] == SIMULATION_VERSION
    assert preview["passed"] is True
    assert preview["status"] == "passed"
    assert preview["checks"]["agentmap_discovery_available"] is True
    assert preview["checks"]["agentmap_live_verification_passed"] is True
    assert preview["checks"]["safe_capability_route_selected"] is True
    assert preview["checks"]["halted_at_human_review"] is True
    assert len(preview["simulation_hash"]) == 64
    assert len(preview["summary_hash"]) == 64


def test_synthetic_agent_simulation_is_deterministic():
    request = {
        "business_id": "home_fixed",
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
    }

    first = build_synthetic_inbound_agent_simulation_preview(request)
    second = build_synthetic_inbound_agent_simulation_preview(request)

    assert first["simulation_hash"] == second["simulation_hash"]
    assert first["summary_hash"] == second["summary_hash"]


def test_synthetic_agent_simulation_hash_changes_when_identity_changes():
    base = build_synthetic_inbound_agent_simulation_preview(
        {
            "business_id": "home_fixed",
            "business_name": "Home Fixed",
            "vertical_key": "home_repair",
        }
    )
    changed = build_synthetic_inbound_agent_simulation_preview(
        {
            "business_id": "other_business",
            "business_name": "Other Business",
            "vertical_key": "legal",
        }
    )

    assert base["simulation_hash"] != changed["simulation_hash"]


def test_synthetic_agent_simulation_keeps_intent_synthetic():
    preview = build_synthetic_inbound_agent_simulation_preview(
        {
            "synthetic_intent": {
                "intent_id": "custom_test",
                "intent_type": "service_quote_request",
                "request_text": "Test intent",
                "vertical_key": "home_repair",
                "synthetic": False,
            }
        }
    )

    assert preview["synthetic_intent"]["synthetic"] is True
    assert preview["checks"]["synthetic_intent_marked_synthetic"] is True


def test_synthetic_agent_simulation_halts_at_human_review_boundary():
    preview = build_synthetic_inbound_agent_simulation_preview()

    handoff = preview["gateway_preview"]["handoff"]

    assert handoff["state"] == "waiting_human_review"
    assert handoff["human_review_required"] is True
    assert handoff["live_execution_authorized"] is False
    assert "booking" in handoff["approval_required_before"]
    assert "payment" in handoff["approval_required_before"]


def test_synthetic_agent_simulation_blocks_all_live_side_effects():
    preview = build_synthetic_inbound_agent_simulation_preview()

    assert preview["checks"]["no_live_side_effects"] is True
    assert preview["side_effects"] == {
        "booking_created": False,
        "payment_created": False,
        "escrow_created": False,
        "job_dispatched": False,
        "external_message_sent": False,
        "live_chain_written": False,
        "public_route_mutated": False,
    }


def test_synthetic_agent_simulation_summary_is_minimal_and_safe():
    summary = build_synthetic_inbound_agent_simulation_summary()

    assert summary["passed"] is True
    assert summary["human_review_required"] is True
    assert summary["live_execution_enabled"] is False
    assert "synthetic_intent" not in summary
    assert "gateway_preview" not in summary
    assert len(summary["simulation_hash"]) == 64
    assert len(summary["summary_hash"]) == 64


def test_synthetic_agent_simulation_module_has_no_live_side_effect_calls():
    text = MODULE.read_text()

    forbidden = [
        "requests.get(",
        "requests.post(",
        "httpx.get(",
        "httpx.post(",
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
