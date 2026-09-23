from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_fabric.provider_telemetry import TrustedProviderTelemetry
from backend.modules.aion_fabric.entertainment_execution import VerifiedEntertainmentExecution
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def envelope(*, nonce: str = "unique_nonce_123456", observed_at: str | None = None):
    return {
        "schema_version": "pilot.provider-telemetry-envelope.v1",
        "source_id": "source_netflix_bridge_01",
        "provider": "netflix",
        "persona_id": "persona_owner01",
        "nonce": nonce,
        "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
        "content": {"content_id": "81234567", "title": "The Crown", "series_title": "The Crown", "season": "2", "episode": "3"},
        "playback": {"state": "playing", "position_seconds": 321, "duration_seconds": 3600},
        "entitlement": {"status": "included"},
    }


def trusted_store(tmp_path, identity):
    store = TrustedProviderTelemetry(tmp_path)
    store.register_source(
        source_id="source_netflix_bridge_01",
        provider="netflix",
        public_key=identity.public_key_b64,
        persona_id="persona_owner01",
        scopes=["metadata.read", "playback.read", "entitlement.read"],
        approved_by="local owner confirmation",
    )
    return store


def test_signed_provider_telemetry_is_normalized_and_persona_bound(tmp_path):
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    store = trusted_store(tmp_path, identity)
    payload = envelope()
    result = store.accept(payload, identity.sign(canonical_bytes(payload)))

    assert result["authenticated"] is True
    assert result["content"]["title"] == "The Crown"
    assert result["playback"]["state"] == "playing"
    assert result["entitlement"] == {"status": "included", "verified": True}
    assert result["raw_provider_response_retained"] is False
    assert store.latest(persona_id="persona_owner01")["telemetry_id"] == result["telemetry_id"]
    assert store.latest(persona_id="persona_someone_else") is None


def test_replay_and_wrong_signature_are_rejected(tmp_path):
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    attacker = DeviceIdentity(Ed25519PrivateKey.generate())
    store = trusted_store(tmp_path, identity)
    payload = envelope()

    with pytest.raises(PermissionError, match="signature"):
        store.accept(payload, attacker.sign(canonical_bytes(payload)))
    store.accept(payload, identity.sign(canonical_bytes(payload)))
    with pytest.raises(PermissionError, match="replay"):
        store.accept(payload, identity.sign(canonical_bytes(payload)))


def test_stale_and_cross_persona_telemetry_are_rejected(tmp_path):
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    store = trusted_store(tmp_path, identity)
    stale = envelope(observed_at=(datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat())
    with pytest.raises(PermissionError, match="stale"):
        store.accept(stale, identity.sign(canonical_bytes(stale)))
    wrong = envelope(nonce="different_nonce_123456")
    wrong["persona_id"] = "persona_someone_else"
    with pytest.raises(PermissionError, match="binding"):
        store.accept(wrong, identity.sign(canonical_bytes(wrong)))


def test_scope_boundary_prevents_ungranted_entitlement_claim(tmp_path):
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    store = TrustedProviderTelemetry(tmp_path)
    store.register_source(
        source_id="source_netflix_bridge_01",
        provider="netflix",
        public_key=identity.public_key_b64,
        persona_id="persona_owner01",
        scopes=["metadata.read", "playback.read"],
        approved_by="local owner confirmation",
    )
    payload = envelope()
    result = store.accept(payload, identity.sign(canonical_bytes(payload)))

    assert result["playback"]["state"] == "playing"
    assert result["entitlement"] == {"status": "unknown", "verified": False}
    snapshot = store.snapshot(persona_id="persona_owner01")
    assert snapshot["public_keys_exposed"] is False
    assert snapshot["provider_secrets_exposed"] is False


def test_signed_telemetry_reconciles_only_matching_private_execution(tmp_path):
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    telemetry_store = trusted_store(tmp_path, identity)
    execution_store = VerifiedEntertainmentExecution(tmp_path)
    execution = execution_store.prepare(
        item={"title": "The Crown", "url": "https://www.netflix.com/title/81234567"},
        persona_id="persona_owner01",
    )
    execution_store.confirm(execution["execution_id"], persona_id="persona_owner01")
    payload = envelope()
    telemetry = telemetry_store.accept(payload, identity.sign(canonical_bytes(payload)))
    reconciled = execution_store.reconcile_telemetry(telemetry)

    assert reconciled["status"] == "playback_verified"
    assert reconciled["playback_verified"] is True
    assert reconciled["entitlement"] == "included"
    assert reconciled["provider_telemetry_id"] == telemetry["telemetry_id"]


def test_signed_telemetry_does_not_reconcile_a_different_title(tmp_path):
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    telemetry_store = trusted_store(tmp_path, identity)
    execution_store = VerifiedEntertainmentExecution(tmp_path)
    execution_store.prepare(
        item={"title": "Another title", "url": "https://www.netflix.com/title/89999999"},
        persona_id="persona_owner01",
    )
    payload = envelope()
    telemetry = telemetry_store.accept(payload, identity.sign(canonical_bytes(payload)))

    assert execution_store.reconcile_telemetry(telemetry) is None
