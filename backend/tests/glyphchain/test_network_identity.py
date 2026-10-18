from datetime import datetime, timezone

import pytest

from backend.modules.p2p.network_identity import NetworkIdentityError, NetworkIdentityStore


NOW = datetime(2026, 9, 26, 20, 0, tzinfo=timezone.utc)


def _store(root):
    return NetworkIdentityStore(root, chain_id="glyphchain-main", node_id="node-a", clock=lambda: NOW)


def test_identity_rotates_with_dual_signed_continuity_certificate(tmp_path):
    store = _store(tmp_path / "identity")
    first = store.identity()
    rotated = store.rotate(actor_id="owner-1", reason="Scheduled rotation", confirmation=store.CONFIRMATION)
    second = rotated["identity"]
    certificate = rotated["rotation_certificate"]
    assert second["active_version"] == 2
    assert second["public_key_hex"] != first["public_key_hex"]
    assert certificate["old_public_key_hex"] == first["public_key_hex"]
    assert certificate["new_public_key_hex"] == second["public_key_hex"]
    assert store.verify_rotation_chain() is True
    assert rotated["restart_required"] is True


def test_rotation_requires_exact_confirmation_and_preserves_old_key(tmp_path):
    store = _store(tmp_path / "identity")
    first = store.identity()
    with pytest.raises(NetworkIdentityError, match="confirmation_required"):
        store.rotate(actor_id="owner-1", reason="Rotate", confirmation="rotate")
    store.rotate(actor_id="owner-1", reason="Rotate", confirmation=store.CONFIRMATION)
    assert (store.root / "_secure_keys" / "v1.key").exists()
    assert store.identity()["retained_key_versions"] == 2
    assert first["raw_private_key_exposed"] is False


def test_encrypted_recovery_restores_all_versions_and_rejects_wrong_password(tmp_path):
    source = _store(tmp_path / "source")
    source.identity()
    source.rotate(actor_id="owner-1", reason="Rotate", confirmation=source.CONFIRMATION)
    package = source.export_recovery_bundle("correct horse battery staple")
    assert package["raw_private_keys_exposed"] is False
    assert set(package) == {"header", "salt_base64", "nonce_base64", "ciphertext_base64", "raw_private_keys_exposed"}
    target = _store(tmp_path / "target")
    restored = target.import_recovery_bundle(package, "correct horse battery staple")
    assert restored["restored_key_versions"] == 2
    assert target.identity()["public_key_hex"] == source.identity()["public_key_hex"]
    assert target.verify_rotation_chain() is True
    wrong = _store(tmp_path / "wrong")
    with pytest.raises(PermissionError, match="could not be authenticated"):
        wrong.import_recovery_bundle(package, "wrong password long enough")


def test_recovery_is_bound_to_chain_and_node(tmp_path):
    source = _store(tmp_path / "source"); source.identity()
    package = source.export_recovery_bundle("correct horse battery staple")
    other = NetworkIdentityStore(tmp_path / "other", chain_id="glyphchain-main", node_id="node-b", clock=lambda: NOW)
    with pytest.raises(NetworkIdentityError, match="identity_mismatch"):
        other.import_recovery_bundle(package, "correct horse battery staple")
