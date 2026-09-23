from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity


def _identity(tmp_path, name="phone"):
    return IdentityStore(tmp_path / name).load_or_create()


def test_adult_child_onboarding_and_guardian_boundary(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    adult = identities.onboard(display_name="Alex", role="adult")
    with pytest.raises(ValueError, match="already exists"):
        identities.onboard(display_name="alex", role="adult")
    child = identities.onboard(display_name="Sam", role="child", guardian_persona_id=adult["persona_id"], age_band="6-7")
    assert child["guardian_persona_id"] == adult["persona_id"]
    with pytest.raises(PermissionError):
        identities.onboard(display_name="No guardian", role="child", guardian_persona_id=child["persona_id"])


def test_signed_phone_possession_active_identity_and_revocation(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    profile = identities.onboard(display_name="Alex")
    phone = _identity(tmp_path)
    challenge = identities.begin_phone_enrollment(persona_id=profile["persona_id"], device_label="Alex phone", public_key=phone.public_key_b64, biometric_capable=True)
    signed = {key: challenge[key] for key in ("challenge_id", "persona_id", "device_id", "device_label", "biometric_capable", "nonce", "expires_at")}
    device = identities.complete_phone_enrollment(challenge["challenge_id"], signature=phone.sign(canonical_bytes(signed)))
    nonce = "activate-on-tv"
    payload = {"purpose": "activate_shared_screen", "persona_id": profile["persona_id"], "device_id": device["device_id"], "nonce": nonce}
    active = identities.activate_shared_screen(persona_id=profile["persona_id"], device_id=device["device_id"], nonce=nonce, signature=phone.sign(canonical_bytes(payload)))
    assert active["display_name"] == "Alex"
    assert active["private_details_on_shared_screen"] is False
    with pytest.raises(PermissionError, match="replay"):
        identities.activate_shared_screen(persona_id=profile["persona_id"], device_id=device["device_id"], nonce=nonce, signature=phone.sign(canonical_bytes(payload)))
    consent = identities.grant_consent(
        persona_id=profile["persona_id"],
        service="google_tasks",
        scopes=["https://www.googleapis.com/auth/tasks"],
        device_id=device["device_id"],
    )
    assert consent["silent_scope_expansion"] is False
    identities.revoke_device(persona_id=profile["persona_id"], device_id=device["device_id"], reason="lost")
    assert identities.snapshot()["active_shared_identity"] is None


def test_shared_tv_workspace_is_exclusive_renewable_and_signed_logout(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    alex = identities.onboard(display_name="Alex")
    becca = identities.onboard(display_name="Becca")
    alex_phone = _identity(tmp_path, "alex_phone")
    becca_phone = _identity(tmp_path, "becca_phone")

    def bind(profile, phone, label):
        challenge = identities.begin_phone_enrollment(
            persona_id=profile["persona_id"], device_label=label,
            public_key=phone.public_key_b64, biometric_capable=True,
        )
        signed = {key: challenge[key] for key in ("challenge_id", "persona_id", "device_id", "device_label", "biometric_capable", "nonce", "expires_at")}
        return identities.complete_phone_enrollment(challenge["challenge_id"], signature=phone.sign(canonical_bytes(signed)))

    alex_device = bind(alex, alex_phone, "Alex phone")
    becca_device = bind(becca, becca_phone, "Becca phone")
    alex_payload = {"purpose": "activate_shared_screen", "persona_id": alex["persona_id"], "device_id": alex_device["device_id"], "nonce": "alex-acquire"}
    active = identities.activate_shared_screen(
        persona_id=alex["persona_id"], device_id=alex_device["device_id"], nonce="alex-acquire",
        signature=alex_phone.sign(canonical_bytes(alex_payload)),
    )
    assert active["idle_timeout_seconds"] == 300
    assert active["exclusive"] is True

    becca_payload = {"purpose": "activate_shared_screen", "persona_id": becca["persona_id"], "device_id": becca_device["device_id"], "nonce": "becca-acquire"}
    with pytest.raises(PermissionError, match="currently controlled by Alex"):
        identities.activate_shared_screen(
            persona_id=becca["persona_id"], device_id=becca_device["device_id"], nonce="becca-acquire",
            signature=becca_phone.sign(canonical_bytes(becca_payload)),
        )

    renewed = identities.touch_shared_screen(persona_id=alex["persona_id"], source="private_phone_controller")
    assert renewed["last_activity_source"] == "private_phone_controller"
    release_payload = {"purpose": "release_shared_screen", "persona_id": alex["persona_id"], "device_id": alex_device["device_id"], "nonce": "alex-release"}
    released = identities.release_shared_screen_signed(
        persona_id=alex["persona_id"], device_id=alex_device["device_id"], nonce="alex-release",
        signature=alex_phone.sign(canonical_bytes(release_payload)),
    )
    assert released["released"] is True
    assert identities.snapshot()["shared_screen"]["state"] == "locked"

    acquired = identities.activate_shared_screen(
        persona_id=becca["persona_id"], device_id=becca_device["device_id"], nonce="becca-acquire",
        signature=becca_phone.sign(canonical_bytes(becca_payload)),
    )
    assert acquired["display_name"] == "Becca"


def test_shared_tv_presence_is_separate_from_activity_and_departure_locks(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    profile = identities.onboard(display_name="Alex")
    phone = _identity(tmp_path)
    challenge = identities.begin_phone_enrollment(
        persona_id=profile["persona_id"], device_label="Alex phone",
        public_key=phone.public_key_b64, biometric_capable=True,
    )
    signed = {key: challenge[key] for key in ("challenge_id", "persona_id", "device_id", "device_label", "biometric_capable", "nonce", "expires_at")}
    device = identities.complete_phone_enrollment(challenge["challenge_id"], signature=phone.sign(canonical_bytes(signed)))
    payload = {"purpose": "activate_shared_screen", "persona_id": profile["persona_id"], "device_id": device["device_id"], "nonce": "presence-acquire"}
    active = identities.activate_shared_screen(
        persona_id=profile["persona_id"], device_id=device["device_id"], nonce="presence-acquire",
        signature=phone.sign(canonical_bytes(payload)),
    )
    inactivity_deadline = active["expires_at"]
    present = identities.confirm_shared_screen_presence(persona_id=profile["persona_id"], device_id=device["device_id"])
    assert present["expires_at"] == inactivity_deadline
    assert present["presence_expires_at"] >= present["last_presence_at"]

    state = json.loads(identities.path.read_text(encoding="utf-8"))
    state["active_shared_identity"]["presence_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    identities._write(state)
    snapshot = identities.snapshot()
    assert snapshot["active_shared_identity"] is None
    assert snapshot["shared_screen"]["last_lock_reason"] == "trusted_phone_departed"


def test_memory_consent_export_scope_and_selective_deletion(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    owner = identities.onboard(display_name="Owner")
    other = identities.onboard(display_name="Other")
    memory = identities.remember(persona_id=owner["persona_id"], kind="preference", summary="Likes quiet films")
    with pytest.raises(PermissionError):
        identities.memories(persona_id=owner["persona_id"], requester_persona_id=other["persona_id"])
    updated = identities.update_memory(persona_id=owner["persona_id"], memory_id=memory["memory_id"], summary="Likes subtitled films", scope="household_shared")
    assert updated["scope"] == "household_shared"
    exported = identities.export(persona_id=owner["persona_id"], requester_persona_id=owner["persona_id"])
    assert exported["memories"][0]["summary"] == "Likes subtitled films"
    assert identities.delete_memory(persona_id=owner["persona_id"], memory_id=memory["memory_id"])["deleted"] is True
