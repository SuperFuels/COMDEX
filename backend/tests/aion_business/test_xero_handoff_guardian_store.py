from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.xero_reconciliation_handoff_service import XeroReconciliationHandoffService


def test_xero_handoff_and_blocked_receipt_restart_from_encrypted_reconciliation_domain(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"x" * 32)
    domains = VaultDomainStore(guardian)
    service = XeroReconciliationHandoffService(domain_store=domains)
    reconciliation = {
        "workspace_id": "acme", "run_id": "run-private", "ledger_id": "ledger-private",
        "matches": [{
            "match_id": "match-private", "match_type": "payment_to_invoice",
            "payment": {"reference": "customer-private"},
            "bank_transaction": {"amount": 123.45}, "invoice": {"contact": "Private Customer"},
            "review": {"decision": "accept_match"},
        }],
    }
    prepared = service.prepare("acme", reconciliation, "match-private")
    service.decide(
        "acme", prepared["handoff_id"], approved=True, decided_by="founder",
        decided_payload_hash=prepared["payload_hash"],
    )
    receipt = service.execute("acme", prepared["handoff_id"], attempted_by="finance-pilot")

    restarted = XeroReconciliationHandoffService(domain_store=domains)
    assert restarted.load("acme", prepared["handoff_id"])["latest_receipt"]["vault_entity_id"].endswith("/blocked_receipt")
    assert restarted.execute("acme", prepared["handoff_id"], attempted_by="finance-pilot")["receipt_hash"] == receipt["receipt_hash"]
    assert restarted.list("acme")[0]["handoff_id"] == prepared["handoff_id"]
    plaintext = guardian.database.read_bytes()
    assert b"Private Customer" not in plaintext
    assert b"customer-private" not in plaintext
