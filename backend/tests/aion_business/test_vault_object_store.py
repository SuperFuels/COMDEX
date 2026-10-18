from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectError, VaultObjectStore


def object_store(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-data" / "Home-Fixed.business-vault",
        business_name="Home Fixed", business_stable_id="home-fixed",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="home-fixed", encryption_key=b"r" * 32)
    return VaultObjectStore(
        layout, guardian=guardian, business_stable_id="home-fixed", encryption_key=b"f" * 32
    )


def test_original_file_is_encrypted_and_round_trips(tmp_path):
    store = object_store(tmp_path)
    secret = b"private customer invoice contents"
    metadata = store.put_bytes(
        object_id="file-1", data=secret, original_name="invoice.pdf",
        content_type="application/pdf", idempotency_key="upload-1",
        actor_id="founder-1", recorded_at="2026-10-17T22:00:00Z",
    )
    assert metadata["original_name"] == "invoice.pdf"
    assert secret not in b"".join(path.read_bytes() for path in store.objects.rglob("*.tvobj"))
    returned_metadata, returned = store.get_bytes(object_id="file-1")
    assert returned == secret
    assert returned_metadata["plaintext_sha256"] == metadata["plaintext_sha256"]


def test_upload_replay_is_exact_and_conflicting_object_is_rejected(tmp_path):
    store = object_store(tmp_path)
    first = store.put_bytes(
        object_id="file-1", data=b"same", original_name="a.txt", content_type="text/plain",
        idempotency_key="upload-1", actor_id="founder-1", recorded_at="t1",
    )
    replay = store.put_bytes(
        object_id="file-1", data=b"same", original_name="a.txt", content_type="text/plain",
        idempotency_key="upload-1", actor_id="founder-1", recorded_at="t1",
    )
    assert first["sealed_sha256"] == replay["sealed_sha256"]
    assert replay["idempotent_replay"] is True
    assert len(list(store.objects.rglob("*.tvobj"))) == 1
    with pytest.raises(VaultObjectError, match="already_exists"):
        store.put_bytes(
            object_id="file-1", data=b"different", original_name="a.txt", content_type="text/plain",
            idempotency_key="upload-2", actor_id="founder-1", recorded_at="t2",
        )


def test_ciphertext_tamper_is_detected(tmp_path):
    store = object_store(tmp_path)
    store.put_bytes(
        object_id="file-1", data=b"untampered", original_name="a.txt", content_type="text/plain",
        idempotency_key="upload-1", actor_id="founder-1", recorded_at="t1",
    )
    blob = next(store.objects.rglob("*.tvobj"))
    damaged = bytearray(blob.read_bytes())
    damaged[-1] ^= 1
    blob.write_bytes(bytes(damaged))
    with pytest.raises(RuntimeError, match="sealed_integrity_failed"):
        store.get_bytes(object_id="file-1")


def test_tombstone_hides_file_but_retains_encrypted_blob(tmp_path):
    store = object_store(tmp_path)
    store.put_bytes(
        object_id="file-1", data=b"retained", original_name="a.txt", content_type="text/plain",
        idempotency_key="upload-1", actor_id="founder-1", recorded_at="t1",
    )
    blob = next(store.objects.rglob("*.tvobj"))
    store.tombstone(
        object_id="file-1", expected_version=1, reason_code="retention_review",
        idempotency_key="delete-1", actor_id="founder-1", recorded_at="t2",
    )
    with pytest.raises(KeyError, match="tombstoned"):
        store.get_bytes(object_id="file-1")
    assert blob.exists()


def test_display_name_cannot_escape_vault(tmp_path):
    store = object_store(tmp_path)
    with pytest.raises(VaultObjectError, match="original_name_invalid"):
        store.put_bytes(
            object_id="file-1", data=b"x", original_name="../../outside.txt",
            content_type="text/plain", idempotency_key="upload-1",
            actor_id="founder-1", recorded_at="t1",
        )
