from __future__ import annotations

import json
import copy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.pilot_unified.adoption import TrustedNetworkAuthority


def _authority(tmp_path):
    return TrustedNetworkAuthority(tmp_path, mother_identity=DeviceIdentity(Ed25519PrivateKey.generate()))


def test_useful_contact_invitation_preserves_exact_request_only(tmp_path):
    authority = _authority(tmp_path)
    created = authority.invite(
        sender_persona_id="persona_alice", sender_display_name="Alice",
        recipient_hint="bob@example.test", relationship="friend",
        exact_request={"kind": "task", "summary": "Please collect the parcel", "task_id": "task_1"},
    )
    inspected = authority.inspect(created["token"])
    assert inspected["sender_display_name"] == "Alice"
    assert inspected["request_summary"] == "Please collect the parcel"
    accepted = authority.accept(token=created["token"], recipient_persona_id="persona_bob", recipient_hint="bob@example.test")
    assert accepted["continued_request"]["task_id"] == "task_1"
    assert accepted["unrelated_sender_data_included"] is False
    with pytest.raises(PermissionError):
        authority.inspect(created["token"])


def test_invitation_state_tampering_is_detected(tmp_path):
    authority = _authority(tmp_path)
    created = authority.invite(
        sender_persona_id="alice", sender_display_name="Alice", recipient_hint="bob@example.test",
        relationship="friend", exact_request={"kind": "task", "summary": "Original request"},
    )
    state = authority._read()
    state["invitations"][0]["request_summary"] = "Altered request"
    authority._write(state)
    with pytest.raises(PermissionError, match="signature"):
        authority.inspect(created["token"])


@pytest.mark.parametrize("kind", ["employer", "client", "boardroom"])
def test_workspace_invitation_has_exact_role_and_scope(kind, tmp_path):
    authority = _authority(tmp_path / kind)
    created = authority.invite(
        sender_persona_id="owner", sender_display_name="Acme Owner", recipient_hint="worker@example.test",
        relationship="professional", kind=kind, workspace_ref="workspace_acme", workspace_role="reviewer",
        exact_request={"kind": "document_review", "summary": "Review the Q3 pack", "package_ref": "package_q3"},
    )
    accepted = authority.accept(token=created["token"], recipient_persona_id="worker", recipient_hint="worker@example.test")
    assert accepted["workspace_ref"] == "workspace_acme"
    assert accepted["workspace_role"] == "reviewer"
    assert accepted["continued_request"]["package_ref"] == "package_q3"


def test_contact_discovery_never_uploads_readable_address_book(tmp_path):
    authority = _authority(tmp_path)
    with pytest.raises(PermissionError):
        authority.discovery_tokens(contacts=["person@example.test"], consent=False, epoch="2026-09")
    result = authority.discovery_tokens(
        contacts=["Person@Example.Test", "+34 600 123 456", "not a route"], consent=True, epoch="2026-09"
    )
    rendered = json.dumps(result)
    assert result["readable_contacts_uploaded"] is False
    assert len(result["tokens"]) == 2
    assert "Person@Example.Test" not in rendered
    assert "600123456" not in rendered


def test_aggregate_activation_metrics_do_not_expose_people(tmp_path):
    authority = _authority(tmp_path)
    created = authority.invite(
        sender_persona_id="alice", sender_display_name="Alice", recipient_hint="bob@example.test",
        relationship="family", exact_request={"kind": "reminder", "summary": "Pick up milk"},
    )
    authority.accept(token=created["token"], recipient_persona_id="bob", recipient_hint="bob@example.test")
    metrics = authority.activation_metrics()
    assert metrics["aggregate_only"] is True
    assert metrics["created"] == metrics["accepted"] == 1
    assert "alice" not in json.dumps(metrics)


def test_export_revocation_and_deletion_stop_future_contact(tmp_path):
    authority = _authority(tmp_path)
    created = authority.invite(
        sender_persona_id="alice", sender_display_name="Alice", recipient_hint="bob@example.test",
        relationship="friend", exact_request={"kind": "message", "summary": "Hello"},
    )
    accepted = authority.accept(token=created["token"], recipient_persona_id="bob", recipient_hint="bob@example.test")
    exported = authority.export_person("bob")
    assert exported["relationships"][0]["relationship_id"] == accepted["relationship_id"]
    revoked = authority.revoke(relationship_id=accepted["relationship_id"], actor_persona_id="bob")
    assert revoked["future_contact_blocked"] is True
    assert authority.authorize_contact(
        relationship_id=accepted["relationship_id"], sender_persona_id="alice", recipient_persona_id="bob"
    ) is False

    second = authority.invite(
        sender_persona_id="alice", sender_display_name="Alice", recipient_hint="bob@example.test",
        relationship="friend", exact_request={"kind": "task", "summary": "Another request"},
    )
    authority.accept(token=second["token"], recipient_persona_id="bob", recipient_hint="bob@example.test")
    deleted = authority.delete_person("bob")
    assert deleted["deleted_private_invitations"] is True
    assert deleted["future_contact_blocked"] is True
    assert all(item["status"] == "revoked" for item in authority._read()["relationships"])


def test_signed_relationship_claim_imports_once_and_rejects_tampering(tmp_path):
    sender = _authority(tmp_path / "sender")
    recipient = _authority(tmp_path / "recipient")
    created = sender.invite(
        sender_persona_id="alice", sender_display_name="Alice", recipient_hint="bob@example.test",
        relationship="friend", exact_request={"kind": "message", "summary": "Hello"},
    )
    accepted = sender.accept(token=created["token"], recipient_persona_id="bob", recipient_hint="bob@example.test")
    imported = recipient.import_relationship(accepted["relationship_claim"], actor_persona_id="bob")
    assert imported["relationship_id"] == accepted["relationship_id"]
    assert recipient.import_relationship(accepted["relationship_claim"], actor_persona_id="bob") == imported
    changed = copy.deepcopy(accepted["relationship_claim"])
    changed["relationship"]["scope"] = "household"
    with pytest.raises(PermissionError, match="signature"):
        recipient.import_relationship(changed, actor_persona_id="bob")
