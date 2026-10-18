from __future__ import annotations

import json

import pytest

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.notification_remote_access_service import (
    NotificationRemoteAccessService,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.pilot_unified.pairing import MobilePairingAuthority


def _subject(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"n" * 32)
    domains = VaultDomainStore(guardian)
    return NotificationRemoteAccessService(domain_store=domains), domains, guardian


def test_notification_delivery_receipt_is_minimised_and_retry_is_exact_once(tmp_path):
    subject, domains, guardian = _subject(tmp_path)
    private_content = "Private appointment at the customer's protected service address."
    prepared = subject.prepare_notification(
        "acme", notification_id="notice-1", recipient="private@example.test",
        channel="push", content=private_content, actor_id="owner",
    )
    duplicate = subject.prepare_notification(
        "acme", notification_id="notice-1", recipient="private@example.test",
        channel="push", content=private_content, actor_id="owner",
    )
    assert prepared["idempotent_replay"] is False
    assert duplicate["idempotent_replay"] is True
    calls = []

    def sender(payload):
        calls.append(payload)
        return {
            "ok": True, "provider": "sandbox-push",
            "provider_request_id": "provider-private-id-1", "provider_status": "accepted",
        }

    first = subject.deliver_notification(
        "acme", notification_id="notice-1", actor_id="owner", sender=sender,
    )
    replay = subject.deliver_notification(
        "acme", notification_id="notice-1", actor_id="owner", sender=sender,
    )
    assert len(calls) == 1
    assert first["external_delivery_performed"] is True
    assert replay["external_delivery_performed"] is False
    assert replay["idempotent_replay"] is True
    public = json.dumps(first)
    assert private_content not in public
    assert "private@example.test" not in public
    assert "provider-private-id-1" not in public
    receipts = domains.list("departments.operational_audit", workspace_id="acme")
    assert {row["payload"]["event_type"] for row in receipts} == {
        "notification_prepared", "notification_delivered",
    }
    assert all(row["payload"]["contains_content"] is False for row in receipts)
    assert private_content.encode() not in guardian.database.read_bytes()


def test_failed_notification_can_retry_but_conflicting_prepare_fails(tmp_path):
    subject, _, _ = _subject(tmp_path)
    subject.prepare_notification(
        "acme", notification_id="notice-2", recipient="owner@example.test",
        channel="email", content="Retry this governed notification.", actor_id="owner",
    )
    failed = subject.deliver_notification(
        "acme", notification_id="notice-2", actor_id="owner",
        sender=lambda payload: {"ok": False, "provider": "sandbox", "error_code": "timeout"},
    )
    delivered = subject.deliver_notification(
        "acme", notification_id="notice-2", actor_id="owner",
        sender=lambda payload: {
            "ok": True, "provider": "sandbox", "provider_request_id": "accepted-2",
        },
    )
    assert failed["notification"]["status"] == "delivery_failed"
    assert delivered["notification"]["status"] == "delivered"
    assert delivered["notification"]["attempt_count"] == 2
    with pytest.raises(ValueError, match="notification_prepare_idempotency_conflict"):
        subject.prepare_notification(
            "acme", notification_id="notice-2", recipient="owner@example.test",
            channel="email", content="Conflicting content.", actor_id="owner",
        )


def test_real_mobile_authority_revocation_is_reflected_in_guardian_and_blocks_reconnect(tmp_path):
    subject, domains, guardian = _subject(tmp_path)
    secret_root = tmp_path / "secret-store"
    mother = IdentityStore(secret_root / "mother").load_or_create()
    phone = IdentityStore(secret_root / "phone").load_or_create()
    identities = ProductionPrivateIdentity(
        secret_root / "identity", domain_store=domains, workspace_id="acme",
    )
    profile = identities.onboard(display_name="Journey Owner", role="adult")
    pairing = MobilePairingAuthority(
        secret_root / "pairing", mother_id="acme-mother", mother_identity=mother,
        endpoint="https://127.0.0.1:18770", ca_sha256="ab" * 32,
        identity_registry=identities,
    )
    challenge = pairing.begin_pairing(
        persona_id=profile["persona_id"], device_label="Owner phone",
        phone_public_key=phone.public_key_b64, requested_scopes=("workspace.read",),
    )
    signed = {
        key: challenge["phone_challenge"][key]
        for key in (
            "schema_version", "challenge_id", "mother_id", "mother_fingerprint",
            "mother_descriptor_hash", "persona_id", "device_id", "device_label",
            "requested_scopes", "nonce", "issued_at", "expires_at",
        )
    }
    connected = pairing.complete_pairing(
        challenge_id=signed["challenge_id"],
        confirmation_code=challenge["local_confirmation"]["confirmation_code"],
        phone_signature=phone.sign(canonical_bytes(signed)),
    )
    session = subject.record_remote_opened(
        "acme", session_id="session-1", device_id=connected["certificate"]["device_id"],
        persona_id=profile["persona_id"], scopes=["workspace.read"],
        certificate_fingerprint=connected["certificate"]["payload_hash"], actor_id="owner",
    )
    assert session["authority_stored_in_vault"] is False
    assert pairing.validate(
        certificate=connected["certificate"], lease=connected["lease"],
        required_scope="workspace.read",
    )["valid"] is True
    revocation = pairing.revoke_device(
        device_id=connected["certificate"]["device_id"], reason="owner_requested",
    )
    public = subject.record_remote_revoked(
        "acme", session_id="session-1", revocation=revocation, actor_id="owner",
    )
    assert public["status"] == "revoked"
    with pytest.raises(PermissionError, match="no longer trusted"):
        pairing.validate(
            certificate=connected["certificate"], lease=connected["lease"],
            required_scope="workspace.read",
        )
    renew = {
        "purpose": "renew_mobile_lease",
        "device_id": connected["certificate"]["device_id"],
        "persona_id": profile["persona_id"],
        "previous_lease_id": connected["lease"]["lease_id"],
        "requested_scopes": ["workspace.read"],
        "nonce": "revoked-reconnect-attempt-1",
    }
    with pytest.raises(PermissionError, match="no longer trusted"):
        pairing.renew_lease(renew, phone_signature=phone.sign(canonical_bytes(renew)))
    assert subject.remote_status("acme", "session-1")["status"] == "revoked"
    assert len(domains.list("security.audit", workspace_id="acme")) == 2
    raw = guardian.database.read_bytes()
    assert connected["lease"]["mother_signature"].encode() not in raw
    assert (secret_root / "phone" / "device_ed25519.pem").read_bytes() not in raw
