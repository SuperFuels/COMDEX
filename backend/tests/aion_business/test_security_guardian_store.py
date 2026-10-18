from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.cybersecurity_guard_service import (
    CommandEvidence,
    CybersecurityGuardService,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_security_state_and_audit_restart_from_encrypted_vault(monkeypatch, tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"s" * 32)
    domains = VaultDomainStore(guardian)
    subject = CybersecurityGuardService(domain_store=domains)
    monkeypatch.setattr(subject, "_inventory", lambda: ([{
        "asset_id": "device-private", "asset_type": "desktop_or_vm",
        "display_name": "Private Finance Workstation", "operating_system": "TestOS",
        "os_release": "1", "architecture": "arm64", "application_count": 2,
        "observed_at": "2026-10-17T00:00:00+00:00", "source": "test",
    }], {"firewall": CommandEvidence("OK", "Firewall enabled", "test")}))

    subject.run_safe_scan("acme", actor_id="owner")
    restarted = CybersecurityGuardService(domain_store=domains)
    state = restarted.load("acme")

    assert state["assets"][0]["display_name"] == "Private Finance Workstation"
    assert domains.list("security.records", workspace_id="acme")
    assert domains.list("security.audit", workspace_id="acme")
    assert b"Private Finance Workstation" not in guardian.database.read_bytes()
    assert not (tmp_path / "acme" / "cybersecurity_guard").exists()
