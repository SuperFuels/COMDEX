from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.xero_bookkeeping_export_service import (
    XeroBookkeepingExportService,
)
from backend.modules.aion_business.runtime.xero_sales_invoice_export_service import (
    XeroSalesInvoiceExportService,
)
from backend.tests.test_xero_bookkeeping_export_service import posted_bookkeeping
from backend.tests.test_xero_sales_invoice_export_service import posted_invoice


def _vault_store(tmp_path) -> VaultDomainStore:
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout, business_stable_id="acme", encryption_key=b"x" * 32
    )
    return VaultDomainStore(guardian, actor_id="test-xero-exports")


def test_xero_bookkeeping_export_survives_restart_in_guardian(monkeypatch, tmp_path):
    repository, authority, bookkeeping, draft = posted_bookkeeping(monkeypatch, tmp_path)
    store = _vault_store(tmp_path)
    service = XeroBookkeepingExportService(
        repository, authority, bookkeeping, domain_store=store
    )

    prepared = service.prepare(
        "acme", draft["draft_id"], xero_contact_id="private-contact-1",
        prepared_by_person_id="person.owner",
    )
    restarted = XeroBookkeepingExportService(
        repository, authority, bookkeeping, domain_store=store
    )

    assert restarted.load("acme", prepared["export_id"]) == prepared
    assert restarted.list("acme")[0]["payload"]["Invoices"][0]["Contact"] == {
        "ContactID": "private-contact-1"
    }
    assert not (
        tmp_path / ".runtime" / "AION_BUSINESS" / "business_containers"
        / "acme" / "finance" / "xero_bookkeeping_exports"
    ).exists()


def test_xero_sales_export_survives_restart_in_guardian(monkeypatch, tmp_path):
    repository, authority, sales, invoice = posted_invoice(monkeypatch, tmp_path)
    store = _vault_store(tmp_path)
    service = XeroSalesInvoiceExportService(
        repository, authority, sales.bookkeeping, sales, domain_store=store
    )

    prepared = service.prepare(
        "acme", invoice["invoice_id"], xero_contact_id="private-customer-1",
        prepared_by_person_id="person.owner",
    )
    restarted = XeroSalesInvoiceExportService(
        repository, authority, sales.bookkeeping, sales, domain_store=store
    )

    assert restarted.load("acme", prepared["export_id"]) == prepared
    assert restarted.list("acme")[0]["payload"]["Invoices"][0]["Contact"] == {
        "ContactID": "private-customer-1"
    }
    assert not (
        tmp_path / ".runtime" / "AION_BUSINESS" / "business_containers"
        / "acme" / "finance" / "xero_sales_invoice_exports"
    ).exists()
