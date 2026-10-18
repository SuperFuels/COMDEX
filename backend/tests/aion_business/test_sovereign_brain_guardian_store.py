from __future__ import annotations

import json

from backend.modules.aion_business.contracts.sovereign_brain import CANONICAL_STORE_KINDS
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.sovereign_brain_boundary import SovereignBrainBoundary
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_sovereign_brain_identity_memory_and_receipts_restart_from_guardian(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"s" * 32),
        actor_id="sovereign-brain-test",
    )
    legacy_root = tmp_path / "legacy-brain"
    brain = SovereignBrainBoundary.bootstrap(
        legacy_root, brain_id="acme", owner_id="founder",
        public_key_fingerprint="sha256:private-fingerprint", domain_store=store,
    )
    brain.upsert_store_record(
        "memory", {"private_fact": "Confidential acquisition target"}, record_id="memory-1",
    )
    brain.upsert_store_record(
        "receipt", {"decision": "Approved private acquisition review"}, record_id="receipt-1",
    )

    restarted = SovereignBrainBoundary(
        legacy_root, domain_store=store, workspace_id="acme",
    )

    assert restarted.status()["ok"] is True
    assert restarted.status()["brain_id"] == "acme"
    assert restarted.store("memory")["records"][0]["private_fact"] == "Confidential acquisition target"
    assert restarted.store("receipt")["records"][0]["record_id"] == "receipt-1"
    assert not legacy_root.exists()
    database = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Confidential acquisition target" not in database
    assert b"Approved private acquisition review" not in database


def test_sovereign_brain_legacy_records_are_copy_verified_receipted_and_retained(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"l" * 32),
        actor_id="sovereign-migration-test",
    )
    legacy_root = tmp_path / "legacy-brain"
    (legacy_root / "stores").mkdir(parents=True)
    identity = {
        "schema_version": "aion.sovereign_brain.v1", "kind": "brain_identity",
        "brain_id": "acme", "owner_id": "founder", "public_key_fingerprint": "sha256:legacy",
    }
    (legacy_root / "brain_identity.json").write_text(json.dumps(identity))
    for kind in CANONICAL_STORE_KINDS:
        payload = {
            "schema_version": "aion.sovereign_store.v1", "kind": kind,
            "records": [{"record_id": f"legacy-{kind}", "private": f"retained-{kind}"}],
        }
        (legacy_root / "stores" / f"{kind}.json").write_text(json.dumps(payload))

    brain = SovereignBrainBoundary.bootstrap(
        legacy_root, brain_id="acme", owner_id="ignored",
        public_key_fingerprint="sha256:ignored", domain_store=store,
    )

    assert brain.status()["brain_id"] == "acme"
    assert brain.store("memory")["records"][0]["private"] == "retained-memory"
    assert (legacy_root / "brain_identity.json").is_file()
    assert (legacy_root / "stores" / "memory.json").is_file()
    receipts = store.list("vault.migration_receipts", workspace_id="acme")
    assert len(receipts) == 1 + len(CANONICAL_STORE_KINDS)
    assert all(item["payload"]["verified"] for item in receipts)
    assert all(item["payload"]["source_retained"] for item in receipts)
