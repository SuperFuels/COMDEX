from __future__ import annotations

from hashlib import sha256

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.capability_packages import CapabilityPackageAuthority
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_fabric.identity import DeviceIdentity


def test_capability_qualification_restarts_from_encrypted_train_agent_domain(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"c" * 32)
    domains = VaultDomainStore(guardian)
    publisher = DeviceIdentity(Ed25519PrivateKey.generate())
    artifact = tmp_path / "customer-capability.zip"
    artifact.write_bytes(b"replaceable product package")
    manifest = CapabilityPackageAuthority.sign_manifest({
        "package_id": "private-sales-adviser", "version": "1.0.0",
        "name": "Private Sales Adviser",
        "artifact": {"sha256": sha256(artifact.read_bytes()).hexdigest(), "bytes": artifact.stat().st_size},
        "permissions": {"network_hosts": [], "file_roots": [], "identity_scopes": [], "tools": [], "execution_actions": []},
        "limits": {"maximum_authorizations": 10},
        "components": {"prompt": "p1", "procedure": "r1", "tools": "t1", "policy": "g1"},
        "component_versions": {"prompt": ["p1"], "procedure": ["r1"], "tools": ["t1"], "policy": ["g1"]},
        "publishing": {"publisher_class": "customer", "curated": False, "commercial_terms": "customer-owned"},
        "contains_customer_brain": False, "contains_customer_data": False,
    }, publisher)

    first = CapabilityPackageAuthority(
        trusted_publishers=[publisher.public_key_b64], workspace_id="acme", domain_store=domains,
    )
    reference = first.package_ref(manifest)
    first.install(manifest, artifact)
    first.record_test(reference, kind="dry_run", passed=True, evidence={"private": "dry-run evidence"})

    restarted = CapabilityPackageAuthority(
        trusted_publishers=[publisher.public_key_b64], workspace_id="acme", domain_store=domains,
    )
    assert restarted.record(reference)["tests"]["dry_run"]["evidence"]["private"] == "dry-run evidence"
    plaintext = guardian.database.read_bytes()
    assert b"dry-run evidence" not in plaintext
