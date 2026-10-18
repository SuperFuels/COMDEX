from __future__ import annotations

import base64
import json
import stat

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.node_control_plane_contract import (
    HEARTBEAT_SCHEMA,
    NodeControlPlaneError,
    NodeHeartbeatRegistry,
    issue_node_certificate_revocation,
    issue_node_certificate,
    sign_node_heartbeat,
)


def encoded_public(key):
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def setup_contract(tmp_path):
    authority = Ed25519PrivateKey.generate()
    node = Ed25519PrivateKey.generate()
    certificate = issue_node_certificate(
        {"node_id": "node-1", "tenant_id": "tenant-1", "node_public_key": encoded_public(node), "platform_class": "node-capable", "architecture": "arm64"},
        authority_private_key=authority, approved_by="founder-1",
        issued_at="2026-10-17T00:00:00+00:00", expires_at="2027-10-17T00:00:00+00:00",
    )
    registry = NodeHeartbeatRegistry(tmp_path / "control-plane" / "nodes.sqlite3")
    return authority, node, certificate, registry


def heartbeat(sequence=1):
    return {
        "schema_version": HEARTBEAT_SCHEMA, "node_id": "node-1", "tenant_id": "tenant-1",
        "sequence": sequence, "issued_at": "2026-10-17T01:00:00+00:00",
        "platform_class": "node-capable", "architecture": "arm64", "update_channel": "stable",
        "components": {"node": "1.0.0", "guardian": "1.0.0"},
        "checks": {"node": "healthy", "guardian": "healthy"},
    }


def test_approved_certificate_and_signed_content_free_heartbeat(tmp_path):
    authority, node, certificate, registry = setup_contract(tmp_path)
    signed = sign_node_heartbeat(heartbeat(), node_private_key=node)
    result = registry.accept(
        signed, certificate=certificate, authority_public_key=authority.public_key(),
        now="2026-10-17T01:01:00+00:00",
    )
    assert result == {"accepted": True, "node_id": "node-1", "tenant_id": "tenant-1", "sequence": 1, "content_free": True}
    assert "vault" not in str(signed["payload"]).lower()


def test_extra_content_or_command_field_is_rejected(tmp_path):
    _, node, _, _ = setup_contract(tmp_path)
    value = heartbeat()
    value["customer_document"] = "private"
    with pytest.raises(NodeControlPlaneError, match="fields_invalid"):
        sign_node_heartbeat(value, node_private_key=node)
    value = heartbeat()
    value["checks"]["private-customer"] = "healthy"
    with pytest.raises(NodeControlPlaneError, match="status_invalid"):
        sign_node_heartbeat(value, node_private_key=node)


def test_heartbeat_replay_is_rejected(tmp_path):
    authority, node, certificate, registry = setup_contract(tmp_path)
    signed = sign_node_heartbeat(heartbeat(), node_private_key=node)
    registry.accept(signed, certificate=certificate, authority_public_key=authority.public_key(), now="2026-10-17T01:01:00+00:00")
    with pytest.raises(NodeControlPlaneError, match="replayed"):
        registry.accept(signed, certificate=certificate, authority_public_key=authority.public_key(), now="2026-10-17T01:02:00+00:00")


def test_tampered_heartbeat_and_expired_certificate_fail(tmp_path):
    authority, node, certificate, registry = setup_contract(tmp_path)
    signed = sign_node_heartbeat(heartbeat(), node_private_key=node)
    signed["payload"]["sequence"] = 2
    with pytest.raises(NodeControlPlaneError, match="signature_invalid"):
        registry.accept(signed, certificate=certificate, authority_public_key=authority.public_key(), now="2026-10-17T01:01:00+00:00")
    signed = sign_node_heartbeat(heartbeat(), node_private_key=node)
    with pytest.raises(NodeControlPlaneError, match="not_current"):
        registry.accept(signed, certificate=certificate, authority_public_key=authority.public_key(), now="2028-10-17T01:01:00+00:00")


def test_registry_revalidates_signed_payload_and_rejects_stale_health(tmp_path):
    authority, node, certificate, registry = setup_contract(tmp_path)
    invalid = heartbeat()
    invalid["checks"]["node"] = "PRIVATE-CUSTOMER-CONTENT"
    encoded = json.dumps(
        invalid, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    manually_signed = {
        "payload": invalid,
        "signature": base64.urlsafe_b64encode(node.sign(encoded)).decode().rstrip("="),
    }
    with pytest.raises(NodeControlPlaneError, match="status_invalid"):
        registry.accept(
            manually_signed, certificate=certificate,
            authority_public_key=authority.public_key(),
            now="2026-10-17T01:01:00+00:00",
        )

    valid = sign_node_heartbeat(heartbeat(), node_private_key=node)
    with pytest.raises(NodeControlPlaneError, match="stale"):
        registry.accept(
            valid, certificate=certificate,
            authority_public_key=authority.public_key(),
            now="2026-10-17T02:00:00+00:00",
        )


def test_registry_is_private_bounded_and_refuses_symlink_database(tmp_path):
    authority, node, certificate, _registry = setup_contract(tmp_path)
    database = tmp_path / "bounded" / "nodes.sqlite3"
    registry = NodeHeartbeatRegistry(database, max_nodes=1)
    registry.accept(
        sign_node_heartbeat(heartbeat(), node_private_key=node),
        certificate=certificate, authority_public_key=authority.public_key(),
        now="2026-10-17T01:01:00+00:00",
    )
    assert stat.S_IMODE(database.stat().st_mode) & 0o077 == 0

    other_node = Ed25519PrivateKey.generate()
    other_certificate = issue_node_certificate(
        {
            "node_id": "node-2", "tenant_id": "tenant-1",
            "node_public_key": encoded_public(other_node),
            "platform_class": "node-capable", "architecture": "arm64",
        },
        authority_private_key=authority, approved_by="founder-1",
        issued_at="2026-10-17T00:00:00+00:00",
        expires_at="2027-10-17T00:00:00+00:00",
    )
    other_heartbeat = {**heartbeat(), "node_id": "node-2"}
    with pytest.raises(NodeControlPlaneError, match="capacity_exceeded"):
        registry.accept(
            sign_node_heartbeat(other_heartbeat, node_private_key=other_node),
            certificate=other_certificate,
            authority_public_key=authority.public_key(),
            now="2026-10-17T01:01:00+00:00",
        )

    link = tmp_path / "linked.sqlite3"
    link.symlink_to(tmp_path / "actual.sqlite3")
    with pytest.raises(NodeControlPlaneError, match="path_unsafe"):
        NodeHeartbeatRegistry(link)


def test_signed_revocation_stops_lost_node_but_not_rotated_certificate(tmp_path):
    authority, node, certificate, registry = setup_contract(tmp_path)
    revocation = issue_node_certificate_revocation(
        certificate,
        authority_private_key=authority,
        node_id="node-1",
        tenant_id="tenant-1",
        revoked_at="2026-10-17T01:00:30+00:00",
        reason_code="device_lost",
    )
    result = registry.apply_revocation(
        revocation,
        authority_public_key=authority.public_key(),
        now="2026-10-17T01:01:00+00:00",
    )
    assert result["revoked"] is True
    assert result["content_free"] is True
    with pytest.raises(NodeControlPlaneError, match="certificate_revoked"):
        registry.accept(
            sign_node_heartbeat(heartbeat(), node_private_key=node),
            certificate=certificate,
            authority_public_key=authority.public_key(),
            now="2026-10-17T01:01:00+00:00",
        )

    rotated = Ed25519PrivateKey.generate()
    rotated_certificate = issue_node_certificate(
        {
            "node_id": "node-1", "tenant_id": "tenant-1",
            "node_public_key": encoded_public(rotated),
            "platform_class": "node-capable", "architecture": "arm64",
        },
        authority_private_key=authority,
        approved_by="founder-1",
        issued_at="2026-10-17T01:00:45+00:00",
        expires_at="2027-10-17T00:00:00+00:00",
    )
    rotated_heartbeat = heartbeat(sequence=2)
    assert registry.accept(
        sign_node_heartbeat(rotated_heartbeat, node_private_key=rotated),
        certificate=rotated_certificate,
        authority_public_key=authority.public_key(),
        now="2026-10-17T01:01:00+00:00",
    )["accepted"] is True


def test_tampered_or_future_revocation_fails_closed(tmp_path):
    authority, _node, certificate, registry = setup_contract(tmp_path)
    revocation = issue_node_certificate_revocation(
        certificate,
        authority_private_key=authority,
        node_id="node-1",
        tenant_id="tenant-1",
        revoked_at="2026-10-17T01:02:00+00:00",
        reason_code="key_compromised",
    )
    with pytest.raises(NodeControlPlaneError, match="from_future"):
        registry.apply_revocation(
            revocation,
            authority_public_key=authority.public_key(),
            now="2026-10-17T01:01:00+00:00",
        )

    revocation["payload"]["reason_code"] = "device_replaced"
    with pytest.raises(NodeControlPlaneError, match="signature_invalid"):
        registry.apply_revocation(
            revocation,
            authority_public_key=authority.public_key(),
            now="2026-10-17T01:03:00+00:00",
        )
