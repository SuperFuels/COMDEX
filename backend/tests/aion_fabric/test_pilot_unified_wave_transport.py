from __future__ import annotations

import copy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.pilot_unified.wave_transport import OptionalWaveTransport


def _transport(tmp_path, name="one"):
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    transport = OptionalWaveTransport(tmp_path / name, mother_identity=identity, mtu=120)
    transport.enroll_bridge(
        bridge_id="bridge_test", bridge_public_key=identity.public_key_b64,
        capabilities=["wave.send", "wave.receive", "wallet.send"], local_confirmation=True,
    )
    return transport, identity


def test_radio_stays_hidden_and_economics_disabled(tmp_path):
    transport, _ = _transport(tmp_path)
    manifest = transport.product_manifest()
    assert manifest == {
        "visible_in_ordinary_setup": False,
        "radio_capability_advertised": False,
        "mock_driver_counts_as_hardware": False,
        "pho_enabled": False,
        "wallet_enabled": False,
    }
    receipt = transport.foundation_receipt()
    assert receipt["framing"] == "bounded_indexed_fragments"
    assert receipt["authentication"] == "ed25519_message_bundle"
    assert receipt["queue"] == "priority_ttl_retry_idempotent"
    assert receipt["store_and_forward"] is True
    assert receipt["physical_radio_driver_active"] is False
    assert receipt["internet_disconnected_delivery_verified"] is False


def test_bridge_capabilities_are_allowlisted_and_revocable(tmp_path):
    transport, _ = _transport(tmp_path)
    state = transport._read()
    assert state["bridges"][0]["capabilities"] == ["wave.receive", "wave.send"]
    transport.revoke_bridge("bridge_test")
    with pytest.raises(PermissionError):
        transport.enqueue(
            bridge_id="bridge_test", recipient_ref="bob", payload=b"hello", content_type="text/plain",
            idempotency_key="revoked-1",
        )


def test_fragment_reconstruct_integrity_deduplication_and_no_false_delivery(tmp_path):
    sender, sender_identity = _transport(tmp_path, "sender")
    receiver, _ = _transport(tmp_path, "receiver")
    receiver.trust_sender(sender_ref="mother_sender", signing_public_key=sender_identity.public_key_b64, local_confirmation=True)
    queued = sender.enqueue(
        bridge_id="bridge_test", recipient_ref="bob", payload=b"bounded private payload" * 20,
        content_type="application/pilot-task", priority="urgent", ttl_seconds=300,
        idempotency_key="wave-task-1",
    )
    assert queued["status"] == "queued"
    bundle = sender.outbound_bundle(queued["message_id"])
    reconstructed = receiver.reconstruct(
        bridge_id="bridge_test", fragments=bundle["fragments"],
        sender_ref="mother_sender", message_signature=bundle["message_signature"],
    )
    assert reconstructed["payload"] == b"bounded private payload" * 20
    assert reconstructed["status"] == "radio_reconstructed_locally"
    assert reconstructed["physical_delivery_verified"] is False
    duplicate = receiver.reconstruct(
        bridge_id="bridge_test", fragments=bundle["fragments"],
        sender_ref="mother_sender", message_signature=bundle["message_signature"],
    )
    assert duplicate["status"] == "duplicate_discarded"


def test_fragment_tampering_and_missing_sequence_fail(tmp_path):
    sender, sender_identity = _transport(tmp_path, "sender")
    receiver, _ = _transport(tmp_path, "receiver")
    receiver.trust_sender(sender_ref="mother_sender", signing_public_key=sender_identity.public_key_b64, local_confirmation=True)
    queued = sender.enqueue(
        bridge_id="bridge_test", recipient_ref="bob", payload=b"payload" * 100,
        content_type="text/plain", idempotency_key="wave-integrity-1",
    )
    bundle = sender.outbound_bundle(queued["message_id"])
    untrusted, _ = _transport(tmp_path, "untrusted")
    with pytest.raises(PermissionError, match="not trusted"):
        untrusted.reconstruct(
            bridge_id="bridge_test", fragments=bundle["fragments"],
            sender_ref="mother_sender", message_signature=bundle["message_signature"],
        )
    with pytest.raises(ValueError, match="incomplete"):
        receiver.reconstruct(
            bridge_id="bridge_test", fragments=bundle["fragments"][:-1],
            sender_ref="mother_sender", message_signature=bundle["message_signature"],
        )
    changed = copy.deepcopy(bundle["fragments"])
    changed[0]["data"] = "AAAA"
    with pytest.raises(PermissionError, match="integrity"):
        receiver.reconstruct(
            bridge_id="bridge_test", fragments=changed,
            sender_ref="mother_sender", message_signature=bundle["message_signature"],
        )


def test_queue_is_priority_ordered_idempotent_and_bounded(tmp_path):
    transport, _ = _transport(tmp_path)
    normal = transport.enqueue(
        bridge_id="bridge_test", recipient_ref="bob", payload=b"normal", content_type="text/plain",
        priority="normal", idempotency_key="normal-1",
    )
    urgent = transport.enqueue(
        bridge_id="bridge_test", recipient_ref="bob", payload=b"urgent", content_type="text/plain",
        priority="urgent", idempotency_key="urgent-1",
    )
    assert transport._read()["queue"][0]["message_id"] == urgent["message_id"]
    repeated = transport.enqueue(
        bridge_id="bridge_test", recipient_ref="bob", payload=b"normal", content_type="text/plain",
        priority="normal", idempotency_key="normal-1",
    )
    assert repeated["message_id"] == normal["message_id"]
    with pytest.raises(PermissionError):
        transport.enqueue(
            bridge_id="bridge_test", recipient_ref="bob", payload=b"different", content_type="text/plain",
            priority="normal", idempotency_key="normal-1",
        )
