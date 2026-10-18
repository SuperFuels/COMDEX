from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.guardian_business_container_repository import GuardianBusinessContainerRepository
from backend.modules.aion_business.runtime.guardian_container_migration import (
    GuardianContainerMigration,
    GuardianContainerMigrationError,
)
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def migration(tmp_path):
    legacy = BusinessContainerRepository(base_dir=tmp_path / "legacy")
    layout = provision_business_vault(
        tmp_path / "customer-data" / "Home-Fixed.business-vault",
        business_name="Home Fixed", business_stable_id="home-fixed",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="home-fixed", encryption_key=b"c" * 32)
    target = GuardianBusinessContainerRepository(guardian)
    return legacy, guardian, GuardianContainerMigration(legacy=legacy, guardian=target)


def test_dry_run_writes_nothing(tmp_path):
    legacy, guardian, service = migration(tmp_path)
    legacy.save_dict("workspace-1", "business_map", {"private": "strategy"})
    result = service.migrate_workspace(
        "workspace-1", kinds=["business_map"], actor_id="founder-1", execute=False
    )
    assert result["candidate_count"] == 1
    assert result["verified_count"] == 0
    assert result["authority_switch_allowed"] is False
    assert guardian.verify_audit_chain()["receipt_count"] == 0


def test_execute_copies_verifies_receipts_and_retains_source(tmp_path):
    legacy, guardian, service = migration(tmp_path)
    source_path = legacy.save_dict("workspace-1", "business_map", {"private": "strategy"})
    result = service.migrate_workspace(
        "workspace-1", kinds=["business_map"], actor_id="founder-1", execute=True
    )
    assert result["migrated_count"] == 1
    assert result["verified_count"] == 1
    assert result["authority_switch_allowed"] is True
    assert result["legacy_sources_deleted"] == 0
    assert legacy.load_dict("workspace-1", "business_map") == {"private": "strategy"}
    assert source_path
    raw = guardian.database.read_bytes()
    assert b"strategy" not in raw
    receipt = guardian.get_record(
        collection="migration_receipts", record_id="workspace-1--business_map"
    )
    assert receipt["payload"]["source_retained"] is True


def test_repeated_migration_is_verified_without_duplicate_write(tmp_path):
    legacy, guardian, service = migration(tmp_path)
    legacy.save_dict("workspace-1", "business_map", {"revision": 1})
    service.migrate_workspace(
        "workspace-1", kinds=["business_map"], actor_id="founder-1", execute=True
    )
    repeated = service.migrate_workspace(
        "workspace-1", kinds=["business_map"], actor_id="founder-1", execute=True
    )
    assert repeated["migrated_count"] == 0
    assert repeated["verified_count"] == 1
    assert guardian.verify_audit_chain()["receipt_count"] == 2


def test_conflicting_existing_target_fails_closed(tmp_path):
    legacy, _, service = migration(tmp_path)
    legacy.save_dict("workspace-1", "business_map", {"revision": 1})
    service.guardian.save_dict(
        "workspace-1", "business_map", {"revision": 2},
        actor_id="founder-1", idempotency_key="preexisting", expected_version=None,
    )
    with pytest.raises(GuardianContainerMigrationError, match="target_conflict"):
        service.migrate_workspace(
            "workspace-1", kinds=["business_map"], actor_id="founder-1", execute=True
        )
