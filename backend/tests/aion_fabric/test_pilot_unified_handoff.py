from __future__ import annotations

import base64

import pytest

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.pilot_inbox import PilotInbox
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.pilot_unified.adoption import TrustedNetworkAuthority
from backend.modules.pilot_unified.handoff import TrustedHandoffAuthority
from backend.modules.pilot_unified.inbox import UnifiedInbox
from backend.modules.pilot_unified.pairing import MobilePairingAuthority


def _mother(root, name):
    identity = IdentityStore(root / "mother_identity").load_or_create()
    identities = ProductionPrivateIdentity(root)
    profile = identities.onboard(display_name=name)
    pairing = MobilePairingAuthority(
        root, mother_id=f"mother_{name.lower()}", mother_identity=identity,
        endpoint=f"https://{name.lower()}.pilot.test:8770", ca_sha256="ab" * 32,
        identity_registry=identities,
    )
    inbox = UnifiedInbox(
        root, mother_id=f"mother_{name.lower()}", mother_identity=identity,
        pairing_authority=pairing, pilot_inbox=PilotInbox(root, identities=identities),
    )
    phone = IdentityStore(root / "phone_identity").load_or_create()
    challenge = pairing.begin_pairing(
        persona_id=profile["persona_id"], device_label=f"{name} phone",
        phone_public_key=phone.public_key_b64,
        requested_scopes=("inbox.read", "message.send", "task.create", "task.respond"),
    )
    signed = {
        key: challenge["phone_challenge"][key]
        for key in (
            "schema_version", "challenge_id", "mother_id", "mother_fingerprint",
            "mother_descriptor_hash", "persona_id", "device_id", "device_label",
            "requested_scopes", "nonce", "issued_at", "expires_at",
        )
    }
    paired = pairing.complete_pairing(
        challenge_id=signed["challenge_id"],
        confirmation_code=challenge["local_confirmation"]["confirmation_code"],
        phone_signature=phone.sign(canonical_bytes(signed)),
    )
    network = TrustedNetworkAuthority(root, mother_identity=identity)
    return {
        "identity": identity, "profile": profile, "phone": phone, "inbox": inbox,
        "certificate": paired["certificate"], "lease": paired["lease"],
        "network": network, "handoffs": TrustedHandoffAuthority(network=network, inbox=inbox),
    }


def _connect(alice, bob):
    alice["inbox"].trust_peer(bob["inbox"].descriptor())
    bob["inbox"].trust_peer(alice["inbox"].descriptor())
    invitation = alice["network"].invite(
        sender_persona_id=alice["profile"]["persona_id"], sender_display_name="Alice",
        recipient_hint="bob@example.test", relationship="friend",
        exact_request={"kind": "message", "summary": "Start a private Pilot connection"},
    )
    accepted = alice["network"].accept(
        token=invitation["token"], recipient_persona_id=bob["profile"]["persona_id"],
        recipient_hint="bob@example.test",
    )
    bob["network"].import_relationship(
        accepted["relationship_claim"], actor_persona_id=bob["profile"]["persona_id"],
    )
    return accepted


def _signed_send(alice, request):
    return alice["handoffs"].send(
        request, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=alice["phone"].sign(canonical_bytes(request)),
    )


def _base(alice, bob, relationship, kind, key):
    return {
        "persona_id": alice["profile"]["persona_id"],
        "recipient_persona_id": bob["profile"]["persona_id"],
        "recipient_mother_id": bob["inbox"].mother_id,
        "relationship_id": relationship["relationship_id"],
        "handoff_type": kind,
        "idempotency_key": key,
    }


def test_one_contract_hands_off_message_reminder_file_and_rights_safe_moment(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    relationship = _connect(alice, bob)

    requests = [
        {**_base(alice, bob, relationship, "message", "handoff_message_1"), "body": "The parcel is ready."},
        {
            **_base(alice, bob, relationship, "reminder", "handoff_reminder_1"),
            "card_type": "reminder", "title": "Collect parcel", "detail": "Before closing",
            "due_at": "2026-09-04T17:00:00+00:00",
        },
        {
            **_base(alice, bob, relationship, "file", "handoff_file_1"),
            "filename": "note.txt", "media_type": "text/plain",
            "content_base64": base64.b64encode(b"private note").decode("ascii"),
        },
        {
            **_base(alice, bob, relationship, "moment", "handoff_moment_1"),
            "card_type": "moment", "title": "That scene", "detail": "Rights-safe context only",
            "moment_id": "moment_verified_1", "context_hash": "ab" * 32,
            "share_mode": "context_card", "provider_url": "https://example.test/watch",
            "rights": {"protected_audio_copied": False, "protected_video_copied": False},
        },
    ]
    for request in requests:
        sent = _signed_send(alice, request)
        assert sent["transport_state"] == "encrypted_packet_ready"
        received = bob["inbox"].receive_packet(sent["result"]["delivery_packet"])
        assert received["status"] == "delivered"

    stream = bob["inbox"].stream(
        persona_id=bob["profile"]["persona_id"], certificate=bob["certificate"], lease=bob["lease"],
    )
    moment = next(item for item in stream["messages"] if item.get("kind") == "moment")
    assert moment["card"]["rights"]["protected_video_copied"] is False
    assert moment["card"]["moment_id"] == "moment_verified_1"


def test_task_requires_second_signed_approval_before_packet_exists(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    relationship = _connect(alice, bob)
    request = {
        **_base(alice, bob, relationship, "task", "handoff_task_1"),
        "title": "Collect the dry cleaning",
    }
    prepared = _signed_send(alice, request)
    assert prepared["transport_state"] == "awaiting_private_approval"
    assert "delivery_packet" not in prepared["result"]

    proposal = prepared["result"]
    approval = {
        "persona_id": alice["profile"]["persona_id"],
        "recipient_persona_id": bob["profile"]["persona_id"],
        "relationship_id": relationship["relationship_id"],
        "action_id": proposal["action_id"], "scope_hash": proposal["scope_hash"],
        "decision": "approved", "idempotency_key": "handoff_task_approve_1",
    }
    approved = alice["handoffs"].approve_task(
        approval, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=alice["phone"].sign(canonical_bytes(approval)),
    )
    received = bob["inbox"].receive_packet(approved["delivery_packet"])
    assert approved["transport_state"] == "encrypted_packet_ready"
    assert received["status"] == "awaiting_recipient_acceptance"


def test_revoked_or_wrong_relationship_blocks_every_handoff(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    relationship = _connect(alice, bob)
    alice["network"].revoke(
        relationship_id=relationship["relationship_id"], actor_persona_id=alice["profile"]["persona_id"],
    )
    request = {
        **_base(alice, bob, relationship, "message", "handoff_revoked_1"),
        "body": "This must not leave.",
    }
    with pytest.raises(PermissionError, match="not active"):
        _signed_send(alice, request)


def test_moment_handoff_rejects_copied_protected_media(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    relationship = _connect(alice, bob)
    request = {
        **_base(alice, bob, relationship, "moment", "handoff_unsafe_moment_1"),
        "card_type": "moment", "title": "Copied scene", "detail": "Must fail",
        "moment_id": "moment_unsafe_1", "context_hash": "cd" * 32,
        "share_mode": "raw_clip", "provider_url": "",
        "rights": {"protected_audio_copied": True, "protected_video_copied": True},
    }
    with pytest.raises(PermissionError, match="cannot copy protected"):
        _signed_send(alice, request)


def test_snapshot_exposes_only_current_persons_active_relationships(tmp_path):
    alice = _mother(tmp_path / "alice", "Alice")
    bob = _mother(tmp_path / "bob", "Bob")
    relationship = _connect(alice, bob)
    request = {"persona_id": alice["profile"]["persona_id"], "purpose": "read_trusted_handoffs"}
    snapshot = alice["handoffs"].snapshot(
        request, certificate=alice["certificate"], lease=alice["lease"],
        phone_signature=alice["phone"].sign(canonical_bytes(request)),
    )
    assert snapshot["relationships"][0]["relationship_id"] == relationship["relationship_id"]
    assert "recipient_hint" not in str(snapshot)
    assert snapshot["supported_types"] == ["file", "message", "moment", "reminder", "task"]
    bob_request = {"persona_id": bob["profile"]["persona_id"], "purpose": "read_trusted_handoffs"}
    bob_snapshot = bob["handoffs"].snapshot(
        bob_request, certificate=bob["certificate"], lease=bob["lease"],
        phone_signature=bob["phone"].sign(canonical_bytes(bob_request)),
    )
    assert bob_snapshot["relationships"][0]["peer_persona_id"] == alice["profile"]["persona_id"]
