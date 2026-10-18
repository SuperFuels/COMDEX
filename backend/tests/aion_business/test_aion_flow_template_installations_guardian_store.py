from __future__ import annotations

from backend.modules.aion_business.runtime.aion_flow_templates import AionFlowTemplateLibrary
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _store(layout) -> VaultDomainStore:
    return VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"t" * 32)
    )


def test_template_installations_restart_from_encrypted_train_agent_domain(tmp_path):
    vault_root = tmp_path / "Business Vault"
    layout = provision_business_vault(
        vault_root, business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    product_root = tmp_path / "application" / "aion-flow-templates"

    first = AionFlowTemplateLibrary(product_root, domain_store=_store(layout))
    installed = first.install(
        "governed-email-drafting@1.0.0",
        organisation_id="acme",
        bindings={"email_connector": "vault://connector/private-mailbox"},
        actor_role="owner",
    )
    assert installed["status"] == "installed_unapproved"

    restarted = AionFlowTemplateLibrary(product_root, domain_store=_store(layout))
    listed = restarted.list_installations(organisation_id="acme")["installations"]
    assert listed[0]["bindings"]["email_connector"] == "vault://connector/private-mailbox"
    removed = restarted.remove(installed["installation_id"], actor_role="owner")
    assert removed["status"] == "removed"

    raw = b"".join(path.read_bytes() for path in vault_root.rglob("*") if path.is_file())
    assert b"private-mailbox" not in raw
