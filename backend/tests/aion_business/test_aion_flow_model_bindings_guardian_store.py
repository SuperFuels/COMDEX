from __future__ import annotations

from backend.modules.aion_business.runtime.aion_flow_model_bindings import AionFlowModelBindings
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _stores(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"m" * 32)
    return guardian, VaultDomainStore(guardian)


def test_model_binding_metadata_restarts_from_encrypted_train_agent_domain(tmp_path):
    guardian, domains = _stores(tmp_path)
    root = tmp_path / "external-security"
    first = AionFlowModelBindings(root, workspace_id="acme", domain_store=domains)
    public = first.create(
        binding_id="private-primary", provider="private",
        secret="highly-private-model-key", label="Founder private model",
    )

    restarted = AionFlowModelBindings(root, workspace_id="acme", domain_store=domains)
    listed = restarted.public_bindings()
    assert listed["bindings"] == [public]
    assert restarted.resolve(public["reference"]) == "highly-private-model-key"
    assert not first.state_path.exists()
    raw_guardian = guardian.database.read_bytes()
    assert b"Founder private model" not in raw_guardian
    assert b"highly-private-model-key" not in raw_guardian


def test_model_binding_metadata_is_workspace_isolated(tmp_path):
    _guardian, domains = _stores(tmp_path)
    root = tmp_path / "external-security"
    AionFlowModelBindings(root, workspace_id="alpha", domain_store=domains).create(
        binding_id="alpha-model", provider="local", secret="alpha-secret",
    )
    assert AionFlowModelBindings(
        root, workspace_id="beta", domain_store=domains,
    ).public_bindings()["bindings"] == []
