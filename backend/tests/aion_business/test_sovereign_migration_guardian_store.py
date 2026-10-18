from __future__ import annotations

import json

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.sovereign_migration_orchestrator import (
    SovereignMigrationOrchestrator,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_sovereign_migration_journal_restarts_from_guardian_and_imports_legacy(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"m" * 32),
        actor_id="migration-test",
    )
    journal = tmp_path / "legacy-journal"
    journal.mkdir()
    legacy = {
        "schema_version": "aion.sovereign_brain_migration.v1",
        "migration_id": "move.legacy", "state": "verified_waiting_activation",
        "brain_id": "acme", "private_note": "Rack destination is confidential",
    }
    legacy_path = journal / "move.legacy.json"
    legacy_path.write_text(json.dumps(legacy))
    service = SovereignMigrationOrchestrator(
        tmp_path / "source", journal, domain_store=store, workspace_id="acme",
    )

    imported = service._read("move.legacy")
    imported["state"] = "target_active_source_retained"
    service._write("move.legacy", imported)
    restarted = SovereignMigrationOrchestrator(
        tmp_path / "source", journal, domain_store=store, workspace_id="acme",
    )

    assert restarted._read("move.legacy")["state"] == "target_active_source_retained"
    assert restarted._read("move.legacy")["legacy_journal_source_retained"] is True
    assert legacy_path.is_file()
    assert b"Rack destination is confidential" not in (layout.records / "guardian.sqlite3").read_bytes()
