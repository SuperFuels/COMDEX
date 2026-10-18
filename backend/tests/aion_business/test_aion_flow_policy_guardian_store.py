from __future__ import annotations

from backend.modules.aion_business.runtime.aion_flow_policy import AionFlowPolicyStore
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_aion_flow_policy_restarts_from_encrypted_train_agent_domain(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"p" * 32)
    domains = VaultDomainStore(guardian)
    policy = AionFlowPolicyStore(tmp_path / "identity", domain_store=domains)
    initial = policy.effective("acme")
    saved = policy.configure(
        "acme", {"allowed_purposes": ["private automation"]},
        changed_by="private-founder", expected_revision=initial["revision"],
    )

    restarted = AionFlowPolicyStore(tmp_path / "identity", domain_store=domains)
    assert restarted.effective("acme")["allowed_purposes"] == ["private automation"]
    assert restarted.effective("acme")["policy_hash"] == saved["policy_hash"]
    plaintext = guardian.database.read_bytes()
    assert b"private automation" not in plaintext
    assert b"private-founder" not in plaintext
    assert not (tmp_path / "identity" / "acme.json").exists()
