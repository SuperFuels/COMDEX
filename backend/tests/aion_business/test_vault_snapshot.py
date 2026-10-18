from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.modules.aion_business.runtime.vault_snapshot import VaultSnapshotError, VaultSnapshotService


def populated_vault(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-data" / "Home-Fixed.business-vault",
        business_name="Home Fixed", business_stable_id="home-fixed",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="home-fixed", encryption_key=b"r" * 32)
    guardian.put_record(
        collection="customers", record_id="customer-1",
        payload={"name": "Private Customer"}, expected_version=None,
        idempotency_key="customer-create", actor_id="founder-1", recorded_at="t1",
    )
    objects = VaultObjectStore(
        layout, guardian=guardian, business_stable_id="home-fixed", encryption_key=b"f" * 32
    )
    objects.put_bytes(
        object_id="file-1", data=b"Private attachment", original_name="evidence.txt",
        content_type="text/plain", idempotency_key="file-create",
        actor_id="founder-1", recorded_at="t2",
    )
    return layout


def test_external_snapshot_restores_records_and_files(tmp_path):
    source = populated_vault(tmp_path)
    service = VaultSnapshotService(source, encryption_key=b"s" * 32)
    snapshot = service.create_snapshot(
        destination_root=tmp_path / "offline-backup", snapshot_id="snapshot-1", created_at="t3"
    )
    all_snapshot_bytes = b"".join(path.read_bytes() for path in snapshot.rglob("*") if path.is_file())
    assert b"Private Customer" not in all_snapshot_bytes
    assert b"Private attachment" not in all_snapshot_bytes

    restored_layout = service.restore_snapshot(
        snapshot_path=snapshot, destination_root=tmp_path / "restored-vault"
    )
    guardian = VaultGuardian(
        restored_layout, business_stable_id="home-fixed", encryption_key=b"r" * 32
    )
    assert guardian.get_record(collection="customers", record_id="customer-1")["payload"]["name"] == "Private Customer"
    objects = VaultObjectStore(
        restored_layout, guardian=guardian, business_stable_id="home-fixed", encryption_key=b"f" * 32
    )
    assert objects.get_bytes(object_id="file-1")[1] == b"Private attachment"

    inspected = service.inspect_snapshot(snapshot_path=snapshot)
    assert inspected["key_material_in_snapshot"] is False
    assert {entry["relative_path"] for entry in inspected["entries"]} >= {
        "vault.manifest.json",
        "records/guardian.sqlite3",
    }


def test_snapshot_destination_cannot_overlap_vault(tmp_path):
    source = populated_vault(tmp_path)
    service = VaultSnapshotService(source, encryption_key=b"s" * 32)
    with pytest.raises(VaultSnapshotError, match="overlap"):
        service.create_snapshot(
            destination_root=source.snapshots, snapshot_id="snapshot-1", created_at="t3"
        )


def test_tampered_snapshot_index_is_rejected_without_partial_restore(tmp_path):
    source = populated_vault(tmp_path)
    service = VaultSnapshotService(source, encryption_key=b"s" * 32)
    snapshot = service.create_snapshot(
        destination_root=tmp_path / "offline-backup", snapshot_id="snapshot-1", created_at="t3"
    )
    index = snapshot / "index.enc"
    damaged = bytearray(index.read_bytes())
    damaged[-1] ^= 1
    index.write_bytes(bytes(damaged))
    destination = tmp_path / "restored-vault"
    with pytest.raises(VaultSnapshotError, match="index_integrity_failed"):
        service.restore_snapshot(snapshot_path=snapshot, destination_root=destination)
    assert not destination.exists()


def test_restore_refuses_non_empty_destination(tmp_path):
    source = populated_vault(tmp_path)
    service = VaultSnapshotService(source, encryption_key=b"s" * 32)
    snapshot = service.create_snapshot(
        destination_root=tmp_path / "offline-backup", snapshot_id="snapshot-1", created_at="t3"
    )
    destination = tmp_path / "restored-vault"
    destination.mkdir()
    (destination / "keep.txt").write_text("do not overwrite")
    with pytest.raises(VaultSnapshotError, match="not_empty"):
        service.restore_snapshot(snapshot_path=snapshot, destination_root=destination)
    assert (destination / "keep.txt").read_text() == "do not overwrite"
