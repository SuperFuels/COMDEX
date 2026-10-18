from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.signed_model_catalogue import SignedModelCatalogue
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_model_catalogue_and_private_outcomes_use_guardian_without_plaintext(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"c" * 32),
        actor_id="catalogue-test",
    )
    root = tmp_path / "application" / "model-catalogue"
    catalogue = SignedModelCatalogue(
        root, trusted_issuers=[], workspace_id="acme", domain_store=store,
    )
    catalogue._write(catalogue.catalogue_path, {
        "schema_version": "aion.model_catalogue.v1", "models": {},
        "routes": {"private-task": {"champion": "private-model@1"}},
    })
    catalogue._write(catalogue.private_scores_path, {
        "schema_version": "aion.customer_private_model_outcomes.v1",
        "outcomes": [{"customer_id": "private-customer", "score": 0.9}],
    }, mode=0o600)

    restarted = SignedModelCatalogue(
        root, trusted_issuers=[], workspace_id="acme", domain_store=store,
    )
    assert restarted._state()["routes"]["private-task"]["champion"] == "private-model@1"
    assert restarted._private()["outcomes"][0]["customer_id"] == "private-customer"
    assert not root.exists()
    database = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"private-customer" not in database
    assert b"private-model" not in database
