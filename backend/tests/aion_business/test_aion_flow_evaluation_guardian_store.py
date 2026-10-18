from __future__ import annotations

from backend.modules.aion_business.runtime.aion_flow_evaluation import AionFlowEvaluationService
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_aion_flow_evaluation_restarts_from_encrypted_train_agent_domain(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"e" * 32)
    domains = VaultDomainStore(guardian)
    service = AionFlowEvaluationService(domain_store=domains)
    created = service.create(
        graph={"nodes": [{"id": "model-1", "type": "model", "model_manifest_id": "champion"}]},
        node_id="model-1", challenger_value="private-challenger",
        evidence_pack={"customer": "private evidence"}, minimum_samples=1,
        authority_context={"person_id": "founder", "workspace_id": "acme", "organisation_id": "acme"},
    )

    restarted = AionFlowEvaluationService(domain_store=domains)
    loaded = restarted.get(created["experiment_id"])
    assert loaded["swap"]["challenger_value"] == "private-challenger"
    assert restarted.list(workspace_id="acme")["experiments"][0]["experiment_id"] == created["experiment_id"]
    plaintext = guardian.database.read_bytes()
    assert b"private-challenger" not in plaintext
    assert b"private evidence" not in plaintext
