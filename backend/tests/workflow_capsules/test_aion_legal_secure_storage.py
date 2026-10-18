from __future__ import annotations

import base64
import base64
import json
import shutil
import sys
import types

import pytest

from backend.modules.aion_business.runtime.legal_secure_storage import LegalEncryptedStore, LegalKeyStore


def test_encrypted_record_hides_content_and_rejects_tampering(tmp_path):
    keys = LegalKeyStore(tmp_path, runtime_mode="test")
    store = LegalEncryptedStore(tmp_path, purpose="signing_records", key_store=keys)
    path = tmp_path / "workspace-a" / "record-1.enc"
    value = {"document": "Highly confidential terms", "counterparty": "Private Person"}
    store.write(path, value, workspace_id="workspace-a", record_id="record-1")

    raw = path.read_text(encoding="utf-8")
    assert "Highly confidential terms" not in raw
    assert "Private Person" not in raw
    assert store.read(path, workspace_id="workspace-a", record_id="record-1") == value

    envelope = json.loads(raw)
    ciphertext = bytearray(base64.b64decode(envelope["ciphertext_base64"]))
    ciphertext[-1] ^= 1
    envelope["ciphertext_base64"] = base64.b64encode(ciphertext).decode("ascii")
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(PermissionError, match="could not be authenticated"):
        store.read(path, workspace_id="workspace-a", record_id="record-1")


def test_workspace_context_is_authenticated(tmp_path):
    store = LegalEncryptedStore(tmp_path, purpose="matter_records")
    path = tmp_path / "workspace-a" / "matter-1.enc"
    store.write(path, {"title": "Matter"}, workspace_id="workspace-a", record_id="matter-1")
    with pytest.raises(PermissionError, match="context does not match"):
        store.read(path, workspace_id="workspace-b", record_id="matter-1")


def test_plaintext_migration_verifies_encrypted_copy_before_removal(tmp_path):
    store = LegalEncryptedStore(tmp_path, purpose="matter_records")
    legacy = tmp_path / "workspace-a" / "matter-1.json"
    encrypted = legacy.with_suffix(".enc")
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"workspace_id": "workspace-a", "title": "Legacy"}), encoding="utf-8")
    value = store.migrate_plaintext(
        legacy, encrypted, workspace_id="workspace-a", record_id="matter-1",
    )
    assert value["title"] == "Legacy"
    assert encrypted.exists()
    assert not legacy.exists()


def test_production_keys_are_created_in_platform_keychain(monkeypatch, tmp_path):
    values = {}
    fake = types.SimpleNamespace(
        get_password=lambda service, account: values.get((service, account)),
        set_password=lambda service, account, value: values.__setitem__((service, account), value),
    )
    monkeypatch.setitem(sys.modules, "keyring", fake)
    keys = LegalKeyStore(tmp_path, runtime_mode="production")
    first = keys.encryption_key("workspace-a", "signing_records")
    second = keys.encryption_key("workspace-a", "signing_records")
    assert first == second
    assert len(first) == 32
    assert keys.source == "platform_keychain"
    assert not (tmp_path / "_secure_keys").exists()


def test_production_fails_closed_when_keychain_is_unavailable(monkeypatch, tmp_path):
    fake = types.SimpleNamespace(get_password=lambda *_: (_ for _ in ()).throw(RuntimeError("locked")))
    monkeypatch.setitem(sys.modules, "keyring", fake)
    keys = LegalKeyStore(tmp_path, runtime_mode="production")
    with pytest.raises(RuntimeError, match="Keychain is unavailable"):
        keys.encryption_key("workspace-a", "signing_records")


def test_rotation_keeps_retired_versions_available_for_old_records(tmp_path):
    keys = LegalKeyStore(tmp_path, runtime_mode="test")
    store = LegalEncryptedStore(tmp_path, purpose="signing_records", key_store=keys)
    old_path = tmp_path / "workspace-a" / "old.enc"
    new_path = tmp_path / "workspace-a" / "new.enc"
    store.write(old_path, {"version": "old"}, workspace_id="workspace-a", record_id="old")
    assert json.loads(old_path.read_text())["key_version"] == 1
    rotated = keys.rotate_encryption_key("workspace-a", "signing_records")
    store.write(new_path, {"version": "new"}, workspace_id="workspace-a", record_id="new")
    assert rotated["active_version"] == 2
    assert json.loads(new_path.read_text())["key_version"] == 2
    assert store.read(old_path, workspace_id="workspace-a", record_id="old")["version"] == "old"
    assert store.read(new_path, workspace_id="workspace-a", record_id="new")["version"] == "new"


def test_password_encrypted_recovery_restores_all_key_versions(tmp_path):
    source_root, restored_root = tmp_path / "source", tmp_path / "restored"
    source_keys = LegalKeyStore(source_root, runtime_mode="test")
    source_store = LegalEncryptedStore(source_root, purpose="matter_records", key_store=source_keys)
    old_path = source_root / "workspace-a" / "matter-old.enc"
    new_path = source_root / "workspace-a" / "matter-new.enc"
    source_store.write(old_path, {"title": "Old"}, workspace_id="workspace-a", record_id="matter-old")
    source_keys.rotate_encryption_key("workspace-a", "matter_records")
    source_store.write(new_path, {"title": "New"}, workspace_id="workspace-a", record_id="matter-new")
    source_keys.signing_key_bytes()
    source_keys.rotate_signing_key()
    source_keys.signing_key_bytes()
    active_storage_key = source_keys.encryption_key("workspace-a", "matter_records")
    package = source_keys.export_recovery_bundle("correct horse battery staple")
    assert base64.b64encode(active_storage_key).decode("ascii") not in json.dumps(package)

    restored_keys = LegalKeyStore(restored_root, runtime_mode="test")
    result = restored_keys.import_recovery_bundle(package, "correct horse battery staple")
    assert result["restored_key_versions"] == 4
    restored_store = LegalEncryptedStore(restored_root, purpose="matter_records", key_store=restored_keys)
    for source in (old_path, new_path):
        target = restored_root / "workspace-a" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    assert restored_store.read(restored_root / "workspace-a" / "matter-old.enc", workspace_id="workspace-a", record_id="matter-old")["title"] == "Old"
    assert restored_store.read(restored_root / "workspace-a" / "matter-new.enc", workspace_id="workspace-a", record_id="matter-new")["title"] == "New"
    assert restored_keys.signing_key_bytes(1) == source_keys.signing_key_bytes(1)
    assert restored_keys.signing_key_bytes(2) == source_keys.signing_key_bytes(2)

    with pytest.raises(PermissionError, match="could not be authenticated"):
        LegalKeyStore(tmp_path / "wrong", runtime_mode="test").import_recovery_bundle(
            package, "wrong password still long",
        )
