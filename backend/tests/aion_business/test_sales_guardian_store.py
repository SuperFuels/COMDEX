from __future__ import annotations

import sys

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.tests.test_finance_bookkeeping_service import configure


def test_sales_spine_records_files_and_audit_restart_from_encrypted_vault(monkeypatch, tmp_path):
    audit_events = []
    monkeypatch.setattr(sys, "audit", lambda name, *args: audit_events.append((name, args)))
    repository, authority = configure(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    key = b"r" * 32
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=key)
    domains = VaultDomainStore(guardian)
    objects = VaultObjectStore(
        layout, guardian=guardian, business_stable_id="acme", encryption_key=key,
    )
    subject = SalesRevenueService(
        repository, authority, domain_store=domains, object_store=objects,
    )
    created = subject.create_enquiry(
        "acme", name="Private Customer", email="private@example.test", phone="+34600123456",
        company_name=None, enquiry="Private sales requirement", source="website",
        source_reference="guardian-test-1", attribution={}, consent={},
        created_by_person_id="person.owner",
    )
    opportunity_id = created["opportunity"]["opportunity_id"]
    attachment = subject.store_work_feed_attachment(
        "acme", opportunity_id, filename="private-proposal.pdf",
        content=b"private sales attachment", media_type="application/pdf",
        recorded_by_person_id="person.owner",
    )

    restarted = SalesRevenueService(
        repository, authority, domain_store=domains, object_store=objects,
    )
    contacts = restarted.list_contacts("acme")
    opportunities = restarted.list_opportunities("acme")
    data, metadata = restarted.work_feed_attachment_bytes(
        "acme", opportunity_id, attachment["attachment_id"],
    )

    assert contacts[0]["name"] == "Private Customer"
    assert opportunities[0]["enquiry"] == "Private sales requirement"
    assert data == b"private sales attachment"
    assert metadata["vault_object_id"].startswith("sales-")
    assert ("tessaris.vault_domain_access", ("sales.files", "put")) in audit_events
    assert ("tessaris.vault_domain_access", ("sales.files", "get")) in audit_events
    assert domains.list("sales.audit", workspace_id="acme")
    assert not (repository.base_dir / "acme" / "sales" / "revenue_spine").exists()
    assert b"Private Customer" not in guardian.database.read_bytes()
    assert b"private sales attachment" not in b"".join(
        path.read_bytes() for path in objects.objects.rglob("*.tvobj")
    )
