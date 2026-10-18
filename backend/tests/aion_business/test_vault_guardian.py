from __future__ import annotations

import sqlite3

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian, VaultGuardianError


def guardian(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-data" / "Home-Fixed.business-vault",
        business_name="Home Fixed", business_stable_id="home-fixed",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    return VaultGuardian(layout, business_stable_id="home-fixed", encryption_key=b"k" * 32)


def test_versioned_record_is_encrypted_and_replay_safe(tmp_path):
    service = guardian(tmp_path)
    created = service.put_record(
        collection="customers", record_id="customer-1",
        payload={"name": "Secret Customer", "email": "private@example.com"},
        expected_version=None, idempotency_key="create-1", actor_id="founder-1",
        recorded_at="2026-10-17T20:00:00Z",
    )
    replay = service.put_record(
        collection="customers", record_id="customer-1",
        payload={"name": "Secret Customer", "email": "private@example.com"},
        expected_version=None, idempotency_key="create-1", actor_id="founder-1",
        recorded_at="2026-10-17T20:00:00Z",
    )
    assert replay == created
    assert service.get_record(collection="customers", record_id="customer-1")["payload"]["name"] == "Secret Customer"
    raw_database = service.database.read_bytes()
    assert b"Secret Customer" not in raw_database
    assert b"private@example.com" not in raw_database


def test_optimistic_versioning_preserves_history(tmp_path):
    service = guardian(tmp_path)
    service.put_record(
        collection="customers", record_id="customer-1", payload={"name": "First"},
        expected_version=None, idempotency_key="create", actor_id="founder-1", recorded_at="t1",
    )
    with pytest.raises(VaultGuardianError, match="version_conflict"):
        service.put_record(
            collection="customers", record_id="customer-1", payload={"name": "Stale"},
            expected_version=None, idempotency_key="stale", actor_id="founder-1", recorded_at="t2",
        )
    service.put_record(
        collection="customers", record_id="customer-1", payload={"name": "Second"},
        expected_version=1, idempotency_key="update", actor_id="founder-1", recorded_at="t3",
    )
    assert service.get_record(collection="customers", record_id="customer-1", version=1)["payload"] == {"name": "First"}
    assert service.get_record(collection="customers", record_id="customer-1")["payload"] == {"name": "Second"}
    assert service.verify_audit_chain()["receipt_count"] == 2


def test_tombstone_hides_current_record_without_deleting_versions(tmp_path):
    service = guardian(tmp_path)
    service.put_record(
        collection="customers", record_id="customer-1", payload={"name": "First"},
        expected_version=None, idempotency_key="create", actor_id="founder-1", recorded_at="t1",
    )
    service.tombstone_record(
        collection="customers", record_id="customer-1", expected_version=1,
        reason_code="customer_request", idempotency_key="delete", actor_id="founder-1",
        recorded_at="t2",
    )
    with pytest.raises(KeyError, match="tombstoned"):
        service.get_record(collection="customers", record_id="customer-1")
    assert service.get_record(
        collection="customers", record_id="customer-1", version=1
    )["payload"] == {"name": "First"}
    assert service.get_record(
        collection="customers", record_id="customer-1", include_tombstone=True
    )["tombstone"] is True


def test_guardian_history_tables_reject_mutation(tmp_path):
    service = guardian(tmp_path)
    service.put_record(
        collection="customers", record_id="customer-1", payload={"name": "First"},
        expected_version=None, idempotency_key="create", actor_id="founder-1", recorded_at="t1",
    )
    with sqlite3.connect(service.database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="guardian_history_immutable"):
            connection.execute("DELETE FROM guardian_record_versions")
