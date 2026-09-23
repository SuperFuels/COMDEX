from pathlib import Path

from backend.modules.aion_gateway.agentmap_dashboard import (
    build_agentmap_dashboard_preview,
    build_agentmap_dashboard_summary,
)


MODULE = Path("backend/modules/aion_gateway/agentmap_dashboard.py")


def test_phase14g_agentmap_dashboard_module_exists():
    assert MODULE.exists()


def test_agentmap_dashboard_preview_is_ready_for_default_home_fixed_flow():
    preview = build_agentmap_dashboard_preview()

    assert preview["dashboard_version"] == "aion.agentmap.dashboard.v0.1"
    assert preview["status"] == "ready"
    assert preview["passed"] is True
    assert preview["business_id"] == "home_fixed"
    assert preview["vertical_key"] == "home_repair"
    assert len(preview["agentmap_hash"]) == 64
    assert len(preview["endpoint_hash"]) == 64
    assert len(preview["verification_hash"]) == 64
    assert len(preview["simulation_hash"]) == 64
    assert len(preview["dashboard_hash"]) == 64
    assert len(preview["summary_hash"]) == 64


def test_agentmap_dashboard_exposes_generate_button_and_machine_discovery_actions():
    preview = build_agentmap_dashboard_preview()
    actions = preview["ui_actions"]

    assert actions["generate_agentmap"]["label"] == "Generate AgentMap"
    assert actions["generate_agentmap"]["enabled"] is True
    assert actions["generate_agentmap"]["preview_only"] is True

    assert actions["regenerate_agentmap"]["enabled"] is True
    assert actions["copy_agentmap_url"]["enabled"] is True
    assert actions["copy_agentmap_url"]["value"] == "/agentmap.json"
    assert actions["download_agentmap_json"]["filename"] == "agentmap.json"
    assert actions["copy_install_tag"]["enabled"] is True
    assert "agentmap" in actions["copy_install_tag"]["value"]


def test_agentmap_dashboard_shows_validation_status_and_hashes():
    preview = build_agentmap_dashboard_preview()

    assert preview["status_panel"]["agentmap_generated"] is True
    assert preview["status_panel"]["agentmap_verified"] is True
    assert preview["status_panel"]["simulation_passed"] is True
    assert preview["status_panel"]["preview_only"] is True
    assert preview["status_panel"]["live_execution_enabled"] is False

    assert preview["checks"]["agentmap_hash_visible"] is True
    assert preview["checks"]["validation_status_available"] is True
    assert preview["agentmap_hash"]


def test_agentmap_dashboard_exposes_hosted_and_self_hosted_paths():
    preview = build_agentmap_dashboard_preview()

    assert preview["paths"]["canonical"] == "/agentmap.json"
    assert preview["paths"]["well_known"] == "/.well-known/agentmap.json"
    assert preview["checks"]["hosted_agentmap_url_available"] is True
    assert preview["checks"]["self_hosted_well_known_export_available"] is True


def test_agentmap_dashboard_keeps_preview_only_safety_boundary():
    preview = build_agentmap_dashboard_preview()

    assert preview["safety_profile"]["preview_only"] is True
    assert preview["safety_profile"]["read_only"] is True
    assert preview["safety_profile"]["human_review_required"] is True
    assert preview["safety_profile"]["live_execution_enabled"] is False

    assert not any(preview["side_effects"].values())


def test_agentmap_dashboard_is_deterministic():
    first = build_agentmap_dashboard_preview()
    second = build_agentmap_dashboard_preview()

    assert first["dashboard_hash"] == second["dashboard_hash"]
    assert first["summary_hash"] == second["summary_hash"]


def test_agentmap_dashboard_hash_changes_when_identity_changes():
    base = build_agentmap_dashboard_preview()
    changed = build_agentmap_dashboard_preview(
        {
            "business_id": "other_business",
            "business_name": "Other Business",
            "vertical_key": "legal",
        }
    )

    assert base["dashboard_hash"] != changed["dashboard_hash"]
    assert base["summary_hash"] != changed["summary_hash"]


def test_agentmap_dashboard_summary_is_minimal_and_safe():
    summary = build_agentmap_dashboard_summary()

    assert summary["status"] == "ready"
    assert summary["passed"] is True
    assert summary["generate_button_available"] is True
    assert summary["validation_status_available"] is True
    assert summary["human_review_required"] is True
    assert summary["live_execution_enabled"] is False
    assert len(summary["dashboard_hash"]) == 64
    assert len(summary["summary_hash"]) == 64


def test_agentmap_dashboard_module_has_no_live_side_effects():
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
