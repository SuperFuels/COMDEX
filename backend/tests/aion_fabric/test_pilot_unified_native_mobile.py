from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.pilot_unified.native_mobile import NativeMobileSecurityAuthority


def _authority(tmp_path):
    return NativeMobileSecurityAuthority(
        tmp_path, mother_identity=DeviceIdentity(Ed25519PrivateKey.generate()), device_id="phone_test"
    )


@pytest.mark.parametrize("kind", ["pairing", "invitation", "task", "approval", "tv_takeover"])
def test_signed_single_use_deep_links(kind, tmp_path):
    authority = _authority(tmp_path)
    link = authority.issue_deep_link(kind=kind, object_ref="object_123")
    assert authority.consume_deep_link(link) == {"kind": kind, "object_ref": "object_123", "verified": True}
    with pytest.raises(PermissionError, match="already"):
        authority.consume_deep_link(link)


def test_deep_link_tampering_fails(tmp_path):
    authority = _authority(tmp_path)
    link = authority.issue_deep_link(kind="task", object_ref="task_1")
    with pytest.raises((ValueError, PermissionError)):
        authority.consume_deep_link(link[:-1] + ("A" if link[-1] != "A" else "B"))
    with pytest.raises(PermissionError):
        authority.consume_deep_link(link.replace("/task?", "/approval?"))


def test_locked_notifications_never_expose_content(tmp_path):
    authority = _authority(tmp_path)
    preview = authority.notification_preview(kind="message", sender_label="Private Person", unlocked=False)
    assert preview == {"title": "Pilot", "body": "Open Pilot to view a private update.", "protected": True}
    authority.set_app_lock(locked=False)
    unlocked = authority.notification_preview(kind="message", sender_label="Becca", unlocked=True)
    assert unlocked["body"] == "New message update"
    assert unlocked["content_included"] is False


def test_private_cache_is_encrypted_and_lock_bound(tmp_path):
    authority = _authority(tmp_path)
    value = {"message": "private household content"}
    receipt = authority.write_secure_cache(cache_id="inbox", value=value)
    assert receipt["encrypted"] is True
    stored = (authority.root / "cache-inbox.bin").read_bytes()
    assert b"private household content" not in stored
    with pytest.raises(PermissionError):
        authority.read_secure_cache(cache_id="inbox")
    authority.set_app_lock(locked=False)
    assert authority.read_secure_cache(cache_id="inbox") == value
    controls = authority.privacy_controls()
    assert controls["clipboard_private_copy_timeout_seconds"] == 30
    assert "redact_private_surfaces" in controls["screenshot_policy"]
    assert controls["hardware_backed_cache_key_required_in_production"] is True


def test_camera_and_microphone_require_permission_and_indicators(tmp_path):
    authority = _authority(tmp_path)
    with pytest.raises(PermissionError):
        authority.permission(name="microphone_ptt", status="denied", active=True)
    state = authority.permission(name="microphone_ptt", status="granted", active=True)
    assert state["indicator"] is True
    authority.set_app_lock(locked=True)
    saved = json.loads(authority.state_path.read_text())
    assert saved["permissions"]["microphone_ptt"]["indicator"] is False


def test_lifecycle_instrumentation_locks_on_suspend(tmp_path):
    authority = _authority(tmp_path)
    authority.set_app_lock(locked=False)
    foreground = authority.lifecycle(event="foreground", battery_percent=77, thermal="nominal", network="wifi")
    assert foreground["background_delivery_allowed"] is False
    background = authority.lifecycle(event="background", battery_percent=76, thermal="fair", network="cellular")
    assert background["background_delivery_allowed"] is True
    authority.lifecycle(event="suspended", battery_percent=75, thermal="fair", network="offline")
    assert json.loads(authority.state_path.read_text())["app_locked"] is True


def test_biometric_confirmation_is_exact_signed_single_use_possession_not_identity(tmp_path):
    authority = _authority(tmp_path)
    phone = DeviceIdentity(Ed25519PrivateKey.generate())
    payload_hash = canonical_hash({"recipient": "contact_becca", "body": "Collect dry cleaning"})
    challenge = authority.issue_biometric_challenge(action_ref="task_send_123", payload_hash=payload_hash)
    approval = {
        **challenge, "schema_version": "pilot.native-biometric-approval.v1",
        "local_authentication": "biometric_or_device_passcode",
    }
    result = authority.consume_biometric_approval(
        approval, device_public_key=phone.public_key_b64,
        signature=phone.sign(canonical_bytes(approval)),
    )
    assert result == {
        "approved": True, "action_ref": "task_send_123", "payload_hash": payload_hash,
        "possession_confirmed": True, "biometric_identity_inferred": False,
    }
    with pytest.raises(PermissionError, match="unavailable|replay"):
        authority.consume_biometric_approval(
            approval, device_public_key=phone.public_key_b64,
            signature=phone.sign(canonical_bytes(approval)),
        )

    changed = authority.issue_biometric_challenge(action_ref="task_send_456", payload_hash=payload_hash)
    tampered = {
        **changed, "schema_version": "pilot.native-biometric-approval.v1",
        "payload_hash": canonical_hash({"different": True}),
        "local_authentication": "biometric",
    }
    with pytest.raises(PermissionError):
        authority.consume_biometric_approval(
            tampered, device_public_key=phone.public_key_b64,
            signature=phone.sign(canonical_bytes(tampered)),
        )


def test_background_inbox_wake_is_content_free_and_idempotent(tmp_path):
    authority = _authority(tmp_path)
    token = "a" * 64
    registered = authority.register_push_channel(platform="apns", provider_token=token)
    assert registered["content_preview_allowed"] is False
    assert token not in authority.state_path.read_text()
    calls = []

    def sender(platform, provider_token, payload):
        calls.append((platform, provider_token, payload))
        return {"accepted": True, "provider_id": "apns_123"}

    first = authority.deliver_background_event(event_id="inbox_event_123", kind="task", sender=sender)
    second = authority.deliver_background_event(event_id="inbox_event_123", kind="task", sender=sender)
    assert first["state"] == "provider_accepted"
    assert first["human_delivery_verified"] is False
    assert first["private_content_sent"] is False
    assert second["duplicate"] is True
    assert len(calls) == 1
    assert calls[0][0:2] == ("apns", token)
    assert calls[0][2]["private_content_included"] is False
    assert calls[0][2]["notification"]["body"] == "Open Pilot to view a private update."
    assert "apns_123" not in authority.state_path.read_text()
