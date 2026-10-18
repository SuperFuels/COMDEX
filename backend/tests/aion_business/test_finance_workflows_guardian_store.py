from __future__ import annotations

import json
import sys

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.accountant_harness_service import AccountantHarnessService
from backend.modules.aion_business.runtime.finance_recurring_work_service import FinanceRecurringWorkService
from backend.modules.aion_business.runtime.finance_bank_activity_service import FinanceBankActivityService
from backend.modules.aion_business.runtime.finance_integration_store import FinanceIntegrationStore
from backend.modules.aion_business.runtime.finance_operations_store import FinanceOperationsStore
from backend.modules.aion_business.runtime.finance_inbox_service import FinanceInboxService
from backend.modules.aion_business.runtime.finance_ledger_service import FinanceLedgerService
from backend.modules.aion_business.runtime.finance_transaction_reconciliation_service import FinanceTransactionReconciliationService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.tests.test_finance_bookkeeping_service import configure
from backend.tests.workflow_capsules.test_aion_finance_director_transaction_vertical import seed


class _Ledger:
    def latest(self, workspace_id: str, include_records: bool = False):
        return {
            "ledger_id": "ledger-private", "ledger_hash": "sha256:private-ledger",
            "records": {
                "accounts": [], "payments": [], "bank_transactions": [],
                "invoices": [{
                    "invoice_id": "invoice-private", "invoice_number": "INV-PRIVATE",
                    "invoice_type": "sales_invoice", "status": "authorised",
                    "contact": {"display_name": "Private Customer"}, "date": "2026-10-01",
                    "due_date": "2026-10-10", "total": 100, "amount_paid": 0,
                    "amount_due": 100, "reference": "PRIVATE", "is_overdue": True,
                }],
            },
        }


def test_finance_recurring_and_reconciliation_restart_from_encrypted_vault(monkeypatch, tmp_path):
    repository, _authority = configure(monkeypatch, tmp_path)
    repository.save_dict("acme", "business_financial_model", {
        "id": "acme.business_financial_model", "workspace_id": "acme",
        "kind": "business_financial_model", "currency": "EUR",
        "metrics": {"ending_cash": 1000}, "missing_information": [], "revision": 1,
    })
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"w" * 32)
    domains = VaultDomainStore(guardian)
    recurring = FinanceRecurringWorkService(repository, domain_store=domains)
    recurring.create(
        "acme", schedule_id="private-cash", kind="weekly_cash_update", cadence="weekly",
        next_run_at="2026-10-17T08:00:00+00:00", created_by="founder",
    )
    recurring.run("acme", "private-cash", run_at="2026-10-17T09:00:00+00:00")
    reconciliation = FinanceTransactionReconciliationService(
        repository, _Ledger(), domain_store=domains,
    )
    run = reconciliation.run("acme", created_at="2026-10-17T10:00:00+00:00", classify_unmatched=False)

    assert FinanceRecurringWorkService(repository, domain_store=domains).list("acme")[0]["run_count"] == 1
    assert FinanceTransactionReconciliationService(
        repository, _Ledger(), domain_store=domains,
    ).latest("acme")["run_id"] == run["run_id"]
    assert domains.list("finance.recurring_records", workspace_id="acme")
    assert domains.list("finance.reconciliation_records", workspace_id="acme")
    assert not (repository.base_dir / "acme" / "finance" / "recurring").exists()
    assert not (repository.base_dir / "acme" / "finance" / "transaction_reconciliations").exists()
    assert b"Private Customer" not in guardian.database.read_bytes()


def test_canonical_finance_ledger_restarts_from_encrypted_vault(monkeypatch, tmp_path):
    repository = seed(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "ledger-vault", business_name="Home Fixed", business_stable_id="home-fixed",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="home-fixed", encryption_key=b"l" * 32)
    domains = VaultDomainStore(guardian)
    integration_store = FinanceIntegrationStore(domain_store=domains)
    legacy_sync = repository.base_dir / "home-fixed" / "integrations" / "xero" / "syncs" / "xero_sync_test"
    protected_sync = integration_store.root("home-fixed", "xero") / "syncs" / "xero_sync_test"
    for source in legacy_sync.glob("*.json"):
        integration_store.write_json(
            protected_sync / source.name,
            json.loads(source.read_text(encoding="utf-8")),
        )
    subject = FinanceLedgerService(
        repository, domain_store=domains, integration_store=integration_store,
    )
    built = subject.build("home-fixed", created_at="2026-10-17T11:00:00+00:00")

    restarted = FinanceLedgerService(
        repository, domain_store=domains, integration_store=integration_store,
    )
    latest = restarted.latest("home-fixed", include_records=True)
    assert latest["ledger_hash"] == built["ledger_hash"]
    assert latest["records"]["invoices"][0]["contact"]["display_name"] == "Customer One"
    assert not (repository.base_dir / "home-fixed" / "finance" / "ledger").exists()
    assert domains.list("finance.ledger_records", workspace_id="home-fixed")
    assert domains.list("finance.integration_records", workspace_id="home-fixed")
    assert b"Customer One" not in guardian.database.read_bytes()


def test_provider_neutral_accounting_evidence_and_ledger_use_guardian(monkeypatch, tmp_path):
    repository, _authority = configure(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "provider-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"p" * 32)
    domains = VaultDomainStore(guardian)
    integrations = FinanceIntegrationStore(domain_store=domains)
    service = AccountantHarnessService(
        repository, domain_store=domains, integration_store=integrations,
    )
    result = service.ingest("acme", "quickbooks_online", {
        "accounts": [],
        "invoices": [{
            "Id": "private-invoice", "DocNumber": "PRIVATE-10",
            "TxnDate": "2026-10-01", "DueDate": "2026-10-30",
            "TotalAmt": 120, "Balance": 120,
            "CustomerRef": {"value": "private-customer", "name": "Private Customer"},
        }],
        "bills": [], "payments": [], "purchases": [], "journal_entries": [],
    }, company_id="private-company", occurred_at="2026-10-17T12:00:00+00:00")

    assert result["ledger"]["provider"] == "quickbooks_online"
    assert domains.list("finance.integration_records", workspace_id="acme")
    assert domains.list("finance.ledger_records", workspace_id="acme")
    assert not (repository.base_dir / "acme" / "integrations").exists()
    assert not (repository.base_dir / "acme" / "finance" / "ledger").exists()
    assert b"Private Customer" not in guardian.database.read_bytes()


def test_approved_bank_activity_restarts_from_finance_operations_vault(monkeypatch, tmp_path):
    repository, authority = configure(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "operations-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"o" * 32)
    domains = VaultDomainStore(guardian)
    operations = FinanceOperationsStore(domain_store=domains)
    service = FinanceBankActivityService(
        repository, authority, domain_store=domains, operations_store=operations,
    )
    record = service.prepare(
        "acme", source_type="controlled_test_fixture", transaction_type="receive",
        transaction_date="2026-10-17", amount=92.50, currency="EUR",
        reference="PRIVATE-RECEIPT", counterparty="Private Counterparty",
        bank_account_id="private-bank", source_document_id=None,
        source_invoice_id="private-invoice", test_purpose="Vault restart proof",
        prepared_by_person_id="person.owner",
    )
    service.approve(
        "acme", record["record_id"], approved_by_person_id="person.owner",
        approved_record_hash=record["record_hash"],
    )
    restarted = FinanceBankActivityService(
        repository, authority, domain_store=domains, operations_store=operations,
    )
    assert restarted.ledger_records("acme")[0]["contact"]["display_name"] == "Private Counterparty"
    assert domains.list("finance.operations_records", workspace_id="acme")
    assert not (repository.base_dir / "acme" / "finance" / "bank_activity").exists()
    assert b"Private Counterparty" not in guardian.database.read_bytes()


def test_finance_inbox_original_and_audit_are_vault_protected(monkeypatch, tmp_path):
    audit_events = []
    monkeypatch.setattr(sys, "audit", lambda name, *args: audit_events.append((name, args)))
    repository, _authority = configure(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "inbox-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    key = b"i" * 32
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=key)
    domains = VaultDomainStore(guardian)
    objects = VaultObjectStore(
        layout, guardian=guardian, business_stable_id="acme", encryption_key=key,
    )
    service = FinanceInboxService(
        repository, domain_store=domains, object_store=objects,
        operations_store=FinanceOperationsStore(domain_store=domains),
    )
    document, duplicate = service.ingest(
        "acme", filename="private-receipt.pdf", content=b"PRIVATE FINANCE RECEIPT",
        mime_type="application/pdf", submitted_by_person_id="person.owner",
    )

    assert duplicate is False
    assert "vault_object_id" in document["source"]
    assert "storage_path" not in document["source"]
    assert service.file_bytes("acme", document["id"])[0] == b"PRIVATE FINANCE RECEIPT"
    assert ("tessaris.vault_domain_access", ("finance.inbox_files", "put")) in audit_events
    assert ("tessaris.vault_domain_access", ("finance.inbox_files", "get")) in audit_events
    assert not (repository.base_dir / "acme" / "finance" / "inbox" / "documents").exists()
    assert domains.list("finance.operations_records", workspace_id="acme")
    assert b"PRIVATE FINANCE RECEIPT" not in guardian.database.read_bytes()
