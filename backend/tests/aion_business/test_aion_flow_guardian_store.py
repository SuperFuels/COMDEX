from __future__ import annotations

from backend.modules.aion_business.runtime.aion_flow_execution import AionFlowRunRepository
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def test_aion_flow_prepared_automation_and_run_restart_from_encrypted_vault(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"f" * 32)
    domains = VaultDomainStore(guardian)
    repository = AionFlowRunRepository(domain_store=domains)
    prepared = repository.save_prepared({
        "preparation_id": "prep-private", "phase": "prepared",
        "authorization_context": {"actor": {"workspace_id": "acme"}},
        "manifest": {"flow_id": "private-customer-follow-up", "nodes": []},
    })
    repository.save({
        "run_id": "run-private", "status": "verified",
        "authority_context": {"workspace_id": "acme"},
        "events": [{"event": "customer_follow_up_prepared"}],
        "updated_at": "2026-10-17T00:00:00+00:00",
    })

    restarted = AionFlowRunRepository(domain_store=domains)
    assert restarted.get_prepared(prepared["preparation_id"])["manifest"]["flow_id"] == "private-customer-follow-up"
    assert restarted.get("run-private")["events"][0]["event"] == "customer_follow_up_prepared"
    assert restarted.list()[0]["run_id"] == "run-private"
    assert not (tmp_path / ".runtime" / "aion_flow").exists()
    assert b"private-customer-follow-up" not in guardian.database.read_bytes()
