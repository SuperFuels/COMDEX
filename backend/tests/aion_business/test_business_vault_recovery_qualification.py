from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.business_vault_recovery_qualification import (
    BusinessVaultRecoveryQualificationService,
)
from backend.modules.aion_business.runtime.business_vault_runtime import BusinessVaultRuntime
from backend.modules.aion_business.runtime.business_data_domain_registry import (
    BusinessDataDomainRegistry,
    PROTECTED_CONTINUITY_SURFACE_DOMAINS,
    REQUIRED_DEPARTMENT_VAULT_DOMAINS,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore


def recovery_runtime(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-data" / "Qualification.business-vault",
        business_name="Qualification",
        business_stable_id="qualification-business",
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    key = b"v" * 32
    guardian = VaultGuardian(
        layout, business_stable_id="qualification-business", encryption_key=key
    )
    objects = VaultObjectStore(
        layout,
        guardian=guardian,
        business_stable_id="qualification-business",
        encryption_key=key,
    )
    runtime = BusinessVaultRuntime(layout=layout, guardian=guardian, objects=objects)
    store = VaultDomainStore(guardian, actor_id="test")
    protected = sorted(
        set(REQUIRED_DEPARTMENT_VAULT_DOMAINS).union(
            *(set(domains) for domains in PROTECTED_CONTINUITY_SURFACE_DOMAINS.values())
        ) - {"file_cabinet.originals"}
    )
    for domain_id in protected:
        store.put(
            domain_id,
            workspace_id="workspace-1",
            entity_id=f"protected-{domain_id}",
            payload={"private_continuity_record": domain_id},
            expected_version=None,
            idempotency_key=f"seed-{domain_id.replace('.', '-')}",
        )
    objects.put_bytes(
        object_id="private-original",
        data=b"Private original customer evidence",
        original_name="evidence.txt",
        content_type="text/plain",
        idempotency_key="private-original",
        actor_id="test",
        recorded_at="2026-10-18T00:00:00+00:00",
    )
    return runtime, key


def test_recovery_drill_is_encrypted_separate_and_exact_once(tmp_path):
    runtime, key = recovery_runtime(tmp_path)
    service = BusinessVaultRecoveryQualificationService(
        runtime,
        vault_encryption_key=key,
        snapshot_encryption_key=b"s" * 32,
        staging_root=tmp_path / "secret-store" / "recovery",
        business_stable_id="qualification-business",
    )
    result = service.run(workspace_id="workspace-1", snapshot_id="journey26")

    assert result["snapshot_plaintext_absent"] is True
    assert result["corrupt_copy_detected"] is True
    assert result["restored_to_separate_clean_root"] is True
    assert result["live_vault_overwrite_refused"] is True
    assert result["snapshot_restore_hashes_match"] is True
    assert result["guardian_audit_healthy"] is True
    assert result["key_material_in_snapshot"] is False
    assert result["inventory"]["original_count"] == 1
    assert set(result["protected_continuity_domain_counts"]) == set(
        REQUIRED_DEPARTMENT_VAULT_DOMAINS
    ).union(*PROTECTED_CONTINUITY_SURFACE_DOMAINS.values())
    assert all(
        count == 1
        for count in result["protected_continuity_domain_counts"].values()
    )
    assert result["complete_registry_readback"] is True
    assert result["registered_domain_count"] == len(
        BusinessDataDomainRegistry().manifest()
    )
    assert set(result["registered_domain_counts"]) == set(
        BusinessDataDomainRegistry().manifest()
    )

    replay = service.run(workspace_id="workspace-1", snapshot_id="journey26")
    assert replay["idempotent_replay"] is True
    assert replay["snapshot_index_sha256"] == result["snapshot_index_sha256"]
    assert len(
        VaultDomainStore(runtime.guardian).list(
            "vault.migration_receipts", workspace_id="workspace-1"
        )
    ) == 1
    assert len(
        VaultDomainStore(runtime.guardian).list(
            "security.audit", workspace_id="workspace-1"
        )
    ) == 1
