from __future__ import annotations

from backend.modules.aion_fabric.verified_navigation import UniversalVerifiedNavigation


def _start(service, *, expected=None, routes=None):
    return service.start(
        device_id="tv_1",
        surface="netflix",
        goal="leave profile chooser",
        expected=expected or {"kind": "view_not", "value": "profile_chooser"},
        routes=routes or [
            {"route_id": "remote_enter", "command": "enter", "arguments": {}},
            {"route_id": "pointer_click", "command": "pointer_click", "arguments": {}},
        ],
        before={"image_sha256": "a" * 64},
    )


def test_transport_delivery_waits_for_after_observation(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    _start(service)
    result = service.record_action_receipt({"receipt_id": "r1", "verified": True, "action": "remote_button", "after": {"transport_verified": True}})
    assert result["status"] == "awaiting_after_observation"


def test_owner_cancel_stops_active_verified_navigation(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    transaction = _start(service)

    cancelled = service.cancel_active(reason="voice_emergency_stop")

    assert cancelled["transaction_id"] == transaction["transaction_id"]
    assert cancelled["status"] == "cancelled"
    assert service.snapshot()["active"] is None


def test_structured_after_observation_verifies_goal(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    _start(service)
    service.record_action_receipt({"receipt_id": "r1", "verified": True, "after": {}})
    result = service.record_observation({"image_sha256": "b" * 64, "inference": {"surface": "netflix", "view": "browse"}})
    assert result["status"] == "verified"
    assert service.snapshot()["active"] is None
    assert service.snapshot()["route_memory_count"] == 1


def test_failed_visual_check_selects_alternative_route(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    _start(service)
    service.record_action_receipt({"receipt_id": "r1", "verified": True, "after": {}})
    result = service.record_observation({"image_sha256": "b" * 64, "inference": {"surface": "netflix", "view": "profile_chooser"}})
    assert result["status"] == "recovery_ready"
    assert service.current_route()["route_id"] == "pointer_click"


def test_screen_change_needs_both_distinct_hashes(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    _start(service, expected={"kind": "screen_changed"}, routes=[{"route_id": "right", "command": "right"}])
    service.record_action_receipt({"receipt_id": "r1", "verified": True, "after": {}})
    result = service.record_observation({"image_sha256": "a" * 64, "inference": {"surface": "netflix"}})
    assert result["status"] == "not_verified"


def test_text_contains_requires_observed_ocr(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    _start(service, expected={"kind": "text_contains", "value": "the crown"}, routes=[{"route_id": "search", "command": "netflix_search"}])
    service.record_action_receipt({"receipt_id": "r1", "verified": True, "action": "netflix_search", "after": {"transport_verified": True}})
    result = service.record_observation({"image_sha256": "b" * 64, "texts": ["Netflix", "The Crown", "Episodes"]})
    assert result["status"] == "verified"


def test_surface_screen_change_requires_both_surface_and_distinct_hash(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    _start(service, expected={"kind": "surface_screen_changed", "surface": "netflix"})
    service.record_action_receipt({"receipt_id": "r1", "verified": True, "after": {"transport_verified": True}})
    result = service.record_observation({"image_sha256": "b" * 64, "inference": {"surface": "netflix", "view": "browse"}})
    assert result["status"] == "verified"


def test_device_field_can_verify_without_pixels(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    _start(service, expected={"kind": "device_field", "field": "foreground_app_id", "equals": "netflix"}, routes=[{"route_id": "launch", "command": "netflix"}])
    result = service.record_action_receipt({"receipt_id": "r1", "verified": True, "after": {"foreground_app_id": "netflix"}})
    assert result["status"] == "verified"


def test_route_memory_prefers_previous_success(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    _start(service)
    service.record_action_receipt({"receipt_id": "r1", "verified": True, "after": {}})
    service.record_observation({"image_sha256": "b" * 64, "inference": {"view": "browse"}})
    second = _start(service, routes=[
        {"route_id": "pointer_click", "command": "pointer_click"},
        {"route_id": "remote_enter", "command": "enter"},
    ])
    assert second["routes"][0]["route_id"] == "remote_enter"


def test_same_idempotency_key_suppresses_duplicate_before_second_action(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    first = service.start(
        device_id="tv_1", surface="home", goal="volume_up",
        expected={"kind": "receipt_verified"},
        routes=[{"route_id": "volume_up", "command": "volume_up"}],
        idempotency_key="phone-request-123",
    )
    duplicate = service.start(
        device_id="tv_1", surface="home", goal="volume_up",
        expected={"kind": "receipt_verified"},
        routes=[{"route_id": "volume_up", "command": "volume_up"}],
        idempotency_key="phone-request-123",
    )

    assert duplicate["transaction_id"] == first["transaction_id"]
    assert duplicate["duplicate_suppressed"] is True
    assert len(service.snapshot()["active"]["attempts"]) == 0


def test_read_after_write_receipt_is_terminal_verified_evidence(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    service.start(
        device_id="tv_1", surface="home", goal="mute",
        expected={"kind": "receipt_verified"},
        routes=[{"route_id": "mute", "command": "mute"}],
    )
    result = service.record_action_receipt({
        "receipt_id": "receipt_mute", "verified": True,
        "action": "set_mute", "after": {"muted": True},
    })

    assert result["status"] == "verified"
    assert result["after_evidence"]["kind"] == "read_after_write_receipt"


def test_reliability_report_requires_sample_and_never_counts_delivery_alone(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    for index in range(20):
        service.start(
            device_id="tv_1", surface="home", goal="observe",
            expected={"kind": "receipt_verified"},
            routes=[{"route_id": "observe", "command": "observe"}],
            idempotency_key=f"observe-{index}",
        )
        service.record_action_receipt({"receipt_id": f"r-{index}", "verified": index != 19, "after": {}})
    report = service.reliability_report(device_id="tv_1")

    assert report["sample_size"] == 20
    assert report["verified"] == 19
    assert report["verified_or_recovered_rate"] == 0.95
    assert report["closure_target_met"] is True
    assert report["delivery_alone_counted_as_success"] is False


def test_new_goal_preserves_unverified_superseded_transaction(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    _start(service)
    service.start(
        device_id="tv_1", surface="netflix", goal="go back",
        expected={"kind": "screen_changed"},
        routes=[{"route_id": "back", "command": "back"}],
    )
    report = service.reliability_report(device_id="tv_1", minimum_sample=1)

    assert report["sample_size"] == 1
    assert report["not_verified"] == 1
    assert report["closure_target_met"] is False


def test_owner_confirmation_closes_ambiguous_changed_screen(tmp_path):
    service = UniversalVerifiedNavigation(tmp_path)
    transaction = service.start(
        device_id="tv_1", surface="netflix", goal="profile_2",
        expected={"kind": "surface_screen_changed", "surface": "netflix"},
        routes=[
            {"route_id": "profile.vertical", "command": "profile_2"},
            {"route_id": "fallback", "command": "pointer_click"},
        ],
        before={"image_sha256": "a" * 64},
    )
    service.record_action_receipt({
        "receipt_id": "receipt-1", "verified": True, "action": "netflix_profile",
        "after": {"buttons_delivered": ["DOWN", "ENTER"]},
    })
    ambiguous = service.record_observation({
        "image_sha256": "b" * 64,
        "inference": {"surface": "unknown", "view": "camera_observation"},
    })
    assert ambiguous["status"] == "recovery_ready"
    confirmed = service.record_owner_confirmation(transaction_id=transaction["transaction_id"], confirmed=True)
    assert confirmed["status"] == "verified"
    assert confirmed["route_index"] == 0
    assert confirmed["after_evidence"]["kind"] == "owner_visual_confirmation"
