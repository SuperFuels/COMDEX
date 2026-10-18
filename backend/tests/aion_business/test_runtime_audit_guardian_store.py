from __future__ import annotations

from backend.modules.aion_business.runtime.audit_log import AuditLog
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.department_operational_store import DepartmentOperationalStore
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_runtime_audit_streams_restart_from_encrypted_append_only_domain(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"a" * 32)
    operational = DepartmentOperationalStore(domain_store=VaultDomainStore(guardian))
    audit = AuditLog(operational_store=operational)
    event = audit.log_event(
        workspace_id="acme", event_type="custom", summary="private operating decision",
        payload={"private": "customer detail"},
    )

    restarted = AuditLog(operational_store=operational)
    assert restarted.read_stream("acme", "events")[0]["id"] == event.id
    plaintext = guardian.database.read_bytes()
    assert b"private operating decision" not in plaintext
    assert b"customer detail" not in plaintext
    assert not (tmp_path / "audit").exists()
