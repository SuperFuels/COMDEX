from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.aion_flow_harness_context import AionFlowHarnessAuthority
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_fabric.identity import DeviceIdentity


def test_harness_and_route_selection_restart_from_encrypted_train_agent_domain(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"h" * 32)
    domains = VaultDomainStore(guardian)
    issuer = DeviceIdentity(Ed25519PrivateKey.generate())
    signed = AionFlowHarnessAuthority.sign_manifest({
        "harness_id": "private-sales-analysis", "version": "1",
        "instructions": "Analyse private sales evidence without inventing facts.",
        "input_schema": {"required": ["sales"]},
        "output_schema": {"required": ["findings"]},
        "examples": [], "declared_tools": [],
        "domain_pack": {"department": "sales", "customer": "private-acme"},
    }, issuer)

    first = AionFlowHarnessAuthority(
        trusted_issuers=[issuer.public_key_b64], workspace_id="acme", domain_store=domains,
    )
    reference = first.harness_ref(signed)
    first.register(signed)
    first.select(route_id="private-sales-route", harness_ref=reference)

    restarted = AionFlowHarnessAuthority(
        trusted_issuers=[issuer.public_key_b64], workspace_id="acme", domain_store=domains,
    )
    assert restarted.record(reference)["manifest"]["domain_pack"]["customer"] == "private-acme"
    assert restarted.select(route_id="private-sales-route", harness_ref=reference)["active"] == reference
    plaintext = guardian.database.read_bytes()
    assert b"private-acme" not in plaintext
    assert b"private-sales-route" not in plaintext
