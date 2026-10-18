from __future__ import annotations

from backend.modules.aion_business.contracts.external_specialists import ExternalSpecialistSpec
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.department_operational_store import DepartmentOperationalStore
from backend.modules.aion_business.runtime.external_specialist_registry import ExternalSpecialistRegistry
from backend.modules.aion_business.contracts.external_work_orders import ExternalWorkOrderRecord
from backend.modules.aion_business.runtime.external_work_order_repository import ExternalWorkOrderRepository
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_external_specialists_restart_from_encrypted_department_vault(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"e" * 32)
    departments = DepartmentOperationalStore(domain_store=VaultDomainStore(guardian))
    registry = ExternalSpecialistRegistry(operational_store=departments)
    registry.save(ExternalSpecialistSpec(
        id="private-reviewer", workspace_id="acme", name="Private Reviewer",
        specialist_type="human_specialist", provider="trusted-network",
        capabilities=["legal_review"], priority=10,
    ))

    restarted = ExternalSpecialistRegistry(operational_store=departments)
    assert restarted.load("acme", "private-reviewer").name == "Private Reviewer"
    assert restarted.list_ids("acme") == ["private-reviewer"]
    assert restarted.resolve_for_capability(
        workspace_id="acme", capability="legal_review",
    ).selected_specialist_id == "private-reviewer"
    assert b"Private Reviewer" not in guardian.database.read_bytes()
    assert not (tmp_path / "external_specialists").exists()


def test_new_department_features_share_the_registered_operational_domain(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"n" * 32)
    store = DepartmentOperationalStore(domain_store=VaultDomainStore(guardian))
    store.put(
        workspace_id="acme", department_id="future_department",
        feature_id="new_feature", record_id="record-1",
        payload={"private": "future business data"},
    )

    records = store.list_feature(
        workspace_id="acme", department_id="future_department", feature_id="new_feature",
    )
    assert records[0]["payload"]["private"] == "future business data"
    assert b"future business data" not in guardian.database.read_bytes()


def test_external_work_orders_restart_from_encrypted_department_vault(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"w" * 32)
    operational = DepartmentOperationalStore(domain_store=VaultDomainStore(guardian))
    repository = ExternalWorkOrderRepository(operational_store=operational)
    repository.save(ExternalWorkOrderRecord(
        id="work-private", workspace_id="acme", capability="legal_review",
        objective="Review private agreement",
    ))

    restarted = ExternalWorkOrderRepository(operational_store=operational)
    assert restarted.load("acme", "work-private").objective == "Review private agreement"
    assert restarted.list_ids("acme") == ["work-private"]
    assert b"Review private agreement" not in guardian.database.read_bytes()
