from backend.services.aion_mission_mode.pilot_cockpit_frontend_mount import (
    PilotCockpitFrontendMount,
    PilotCockpitFrontendMountError,
)


def test_phase21b_entrypoint_renders_visible_pilot():
    entry = PilotCockpitFrontendMount.build_pilot_entrypoint("home-fixed", "mission-001")

    assert entry["component"] == "aion_pilot_entrypoint"
    assert entry["label"] == "AION Pilot"
    assert entry["visible"] is True
    assert entry["enabled"] is True
    assert entry["opens"] == "pilot_cockpit"
    assert entry["live_external_actions_enabled"] is False
    assert entry["requires_existing_approval_chain"] is True
    assert entry["entrypoint_hash"].startswith("sha256:")


def test_phase21b_status_strip_supports_all_required_states():
    for status in PilotCockpitFrontendMount.VALID_STATUSES:
        strip = PilotCockpitFrontendMount.build_status_strip(status)

        assert strip["component"] == "pilot_status_strip"
        assert strip["status"] == status
        assert strip["status_message"]
        assert "No money" in strip["safety_message"]
        assert strip["status_hash"].startswith("sha256:")


def test_phase21b_unknown_status_fails_closed():
    try:
        PilotCockpitFrontendMount.build_status_strip("execute_live")
    except PilotCockpitFrontendMountError as exc:
        assert "Unknown Pilot status" in str(exc)
    else:
        raise AssertionError("unknown status did not fail closed")


def test_phase21b_cockpit_shell_identifies_native_executor_not_ui_automation():
    shell = PilotCockpitFrontendMount.build_cockpit_shell("home-fixed", "mission-001")

    assert shell["pilot_identity"] == "AION native runtime executor"
    assert shell["not_ui_automation"] is True
    assert shell["safe_read_model"] is True


def test_phase21b_cockpit_has_required_panels():
    shell = PilotCockpitFrontendMount.build_cockpit_shell("home-fixed", "mission-001")

    for panel in [
        "mission_composer",
        "plan_preview",
        "pilot_stream",
        "business_container_files",
        "artifact_outputs",
        "approvals",
        "blocked_actions",
        "mission_map",
        "proof_replay",
        "feedback",
    ]:
        assert panel in shell["panels"]


def test_phase21b_cockpit_cannot_execute_raw_tools_or_mutate_external_systems():
    shell = PilotCockpitFrontendMount.build_cockpit_shell("home-fixed", "mission-001")

    assert shell["can_execute_raw_tools"] is False
    assert shell["can_mutate_external_systems"] is False
    assert shell["can_mutate_live_memory"] is False
    assert shell["requires_plan_review"] is True
    assert shell["requires_exact_payload_approval_for_live_actions"] is True


def test_phase21b_required_safety_message_is_visible():
    shell = PilotCockpitFrontendMount.build_cockpit_shell("home-fixed", "mission-001")

    assert shell["required_visible_message"] == "AION stopped itself before doing anything risky."


def test_phase21b_boardroom_mount_payload_is_visible_operator_panel():
    payload = PilotCockpitFrontendMount.build_boardroom_mount_payload("home-fixed", "mission-001")

    assert payload["schema_version"] == "aion.phase21b.pilot_cockpit_frontend_mount.v1"
    assert payload["mount_location"] == "boardroom"
    assert payload["render_mode"] == "visible_operator_panel"
    assert payload["live_action_buttons_default"] == "hidden"
    assert payload["mount_payload_hash"].startswith("sha256:")


def test_phase21b_hash_is_deterministic():
    one = PilotCockpitFrontendMount.build_boardroom_mount_payload("home-fixed", "mission-001")
    two = PilotCockpitFrontendMount.build_boardroom_mount_payload("home-fixed", "mission-001")

    assert one["mount_payload_hash"] == two["mount_payload_hash"]


def test_phase21b_status_counts_are_visible():
    strip = PilotCockpitFrontendMount.build_status_strip(
        "waiting_approval",
        blocked_count=2,
        approval_count=3,
    )

    assert strip["blocked_count"] == 2
    assert strip["approval_count"] == 3
