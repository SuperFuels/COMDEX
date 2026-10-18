from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _store(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-data" / "Acme.business-vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"v" * 32)
    return VaultDomainStore(guardian), guardian


def test_domain_records_are_encrypted_versioned_and_listed_by_workspace(tmp_path):
    store, guardian = _store(tmp_path)
    first = store.put(
        "train_agent.automations",
        workspace_id="acme",
        entity_id="automation-1",
        payload={"instruction": "Reconcile private bank feed"},
        expected_version=None,
        idempotency_key="automation-create",
    )
    store.put(
        "train_agent.automations",
        workspace_id="other",
        entity_id="automation-2",
        payload={"instruction": "Other tenant"},
        expected_version=None,
        idempotency_key="automation-other",
    )
    second = store.put(
        "train_agent.automations",
        workspace_id="acme",
        entity_id="automation-1",
        payload={"instruction": "Reconcile private bank feed", "enabled": True},
        expected_version=int(first["version"]),
        idempotency_key="automation-update",
    )
    assert second["version"] == 2
    assert store.get(
        "train_agent.automations", workspace_id="acme", entity_id="automation-1"
    )["payload"]["enabled"] is True
    assert len(store.list("train_agent.automations", workspace_id="acme")) == 1
    assert b"Reconcile private bank feed" not in guardian.database.read_bytes()
