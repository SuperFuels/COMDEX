from __future__ import annotations

import json

import pytest

from backend.modules.aion_fabric.observer import ExplicitObserverSessions


def test_observer_requires_token_is_rate_limited_and_redacts_secret(tmp_path):
    observer = ExplicitObserverSessions(tmp_path)
    started = observer.start(persona_id="persona_owner", duration_seconds=600, interval_seconds=5)
    token = started["frame_token"]

    assert started["active"] is True
    assert "token_hash" not in started
    assert "frame_token" not in observer.snapshot()
    persisted = json.loads(observer.path.read_text(encoding="utf-8"))
    assert token not in observer.path.read_text(encoding="utf-8")
    assert persisted["raw_frames_retained"] is False

    accepted = observer.accept_frame(token)
    assert accepted["frames_accepted"] == 1
    with pytest.raises(ValueError, match="permitted interval"):
        observer.accept_frame(token)
    with pytest.raises(PermissionError, match="invalid"):
        observer.accept_frame("wrong-token")


def test_observer_stop_is_persona_bound(tmp_path):
    observer = ExplicitObserverSessions(tmp_path)
    observer.start(persona_id="persona_owner")

    with pytest.raises(PermissionError, match="another private identity"):
        observer.stop(persona_id="persona_guest")
    stopped = observer.stop(persona_id="persona_owner")
    assert stopped["active"] is False
    assert stopped["raw_frames_retained"] is False


def test_observer_resource_policy_throttles_then_pauses_without_frames(tmp_path):
    observer = ExplicitObserverSessions(tmp_path)
    started = observer.start(persona_id="persona_owner", capture_profile="detail", interval_seconds=3)

    low = observer.report_client_state(
        persona_id="persona_owner",
        battery_level=0.15,
        charging=False,
        thermal_state="nominal",
        visibility="visible",
    )
    assert low["resource_state"]["battery_band"] == "low"
    assert low["effective_interval_seconds"] == 15
    assert low["paused"] is False

    critical = observer.report_client_state(
        persona_id="persona_owner",
        battery_level=0.08,
        charging=False,
        thermal_state="nominal",
        visibility="visible",
    )
    assert critical["paused"] is True
    assert critical["pause_reason"] == "resource_battery_critical"
    with pytest.raises(PermissionError, match="paused"):
        observer.accept_frame(started["frame_token"])


def test_observer_visibility_pause_requires_visible_resume_and_stop_receipt(tmp_path):
    observer = ExplicitObserverSessions(tmp_path)
    observer.start(persona_id="persona_owner", capture_profile="battery_saver")
    hidden = observer.report_client_state(persona_id="persona_owner", visibility="hidden")
    assert hidden["paused"] is True

    visible = observer.report_client_state(persona_id="persona_owner", visibility="visible")
    assert visible["paused"] is False
    resumed = observer.resume(persona_id="persona_owner")
    assert resumed["capture_profile"] == "battery_saver"
    stopped = observer.stop(persona_id="persona_owner")
    assert len(stopped["session_receipt"]["receipt_hash"]) == 64
    assert stopped["session_receipt"]["raw_frames_retained"] is False


def test_observer_configuration_is_persona_bound_and_bounded(tmp_path):
    observer = ExplicitObserverSessions(tmp_path)
    observer.start(persona_id="persona_owner")
    with pytest.raises(PermissionError, match="another private identity"):
        observer.configure(persona_id="persona_guest", capture_profile="detail")
    configured = observer.configure(
        persona_id="persona_owner", capture_profile="detail", interval_seconds=1
    )
    assert configured["effective_interval_seconds"] == 3
    assert configured["max_frame_dimension"] == 1280
