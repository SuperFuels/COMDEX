from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.department_operational_store import DepartmentOperationalStore
from backend.modules.aion_business.runtime.medium_business_operating_service import MediumBusinessOperatingService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_medium_business_model_and_audit_restart_from_encrypted_vault(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"m" * 32)
    operational = DepartmentOperationalStore(domain_store=VaultDomainStore(guardian))
    service = MediumBusinessOperatingService(
        workspace_id="acme", operational_store=operational,
    )
    saved = service.configure(
        {
            "group": {"name": "Private Group"}, "entities": [], "units": [],
            "locations": [], "people": [], "roles": [], "projects": [],
            "workflows": [], "identity_providers": [], "policies": {},
        },
        expected_revision=0,
        changed_by="private-founder",
    )
    assert saved["revision"] == 1

    restarted = MediumBusinessOperatingService(
        workspace_id="acme", operational_store=operational,
    )
    assert restarted.state()["group"]["name"] == "Private Group"
    assert restarted._read_audit()[0]["actor"] == "private-founder"
    plaintext = guardian.database.read_bytes()
    assert b"Private Group" not in plaintext
    assert b"private-founder" not in plaintext
    assert not (tmp_path / "medium_business").exists()
