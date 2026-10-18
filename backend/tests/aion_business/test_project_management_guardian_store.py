from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.project_management_service import ProjectManagementService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


class OfflineRouter:
    def is_configured(self, _provider):
        return False


def test_project_portfolio_survives_guardian_restart_without_plaintext_json(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"p" * 32),
        actor_id="project-test",
    )
    service = ProjectManagementService(provider_router=OfflineRouter(), domain_store=store)
    created = service.create_project("acme", {
        "title": "Private expansion", "outcome": "Open a private customer location",
        "customer": "Private Customer", "budget_total": "5000",
    }, actor_id="founder")
    updated = service.apply_action(
        "acme", created["projects"][0]["id"], "add_task",
        {
            "title": "Compare suppliers",
            "assigned_department": "procurement_from_update",
            "description": "Private supplier requirements",
        },
        actor_id="founder",
    )

    restarted = ProjectManagementService(provider_router=OfflineRouter(), domain_store=store)
    loaded = restarted.load("acme")

    assert loaded["projects"][0]["id"] == created["projects"][0]["id"]
    assert loaded["projects"][0]["customer"] == "Private Customer"
    assert updated["projects"][0]["tasks"][0]["assigned_department"] == "procurement_from_update"
    assert loaded["projects"][0]["tasks"][0]["assigned_department"] == "procurement_from_update"
    assert not (tmp_path / "business-containers" / "acme" / "project_management.json").exists()
    assert b"Private Customer" not in (layout.records / "guardian.sqlite3").read_bytes()
