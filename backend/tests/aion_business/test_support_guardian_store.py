from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.support_case_service import SupportCaseService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.tests.test_finance_bookkeeping_service import configure


def test_support_configuration_and_knowledge_restart_from_encrypted_vault(monkeypatch, tmp_path):
    repository, _ = configure(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    key = b"s" * 32
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=key)
    domains = VaultDomainStore(guardian)
    objects = VaultObjectStore(
        layout, guardian=guardian, business_stable_id="acme", encryption_key=key,
    )
    subject = SupportCaseService(
        repository, domain_store=domains, object_store=objects,
    )
    setup = subject.ensure_setup("acme")
    knowledge = subject.add_knowledge(
        "acme", title="Private warranty policy", source_type="warranty",
        content="Private customer warranty procedure retained for approved support decisions.",
        source_reference="policy:private-warranty:v1", jurisdiction="Spain",
        effective_from="2026-10-17", approved_by_person_id="person.owner",
    )
    subject.sales.create_enquiry(
        "acme", name="Support-linked Customer", email="linked@example.test",
        phone="+34600111222", company_name=None, enquiry="Linked support enquiry",
        source="support", source_reference="support-link-1", attribution={}, consent={},
        created_by_person_id="person.owner",
    )
    subject.finance.create_customer(
        "acme", name="Support-linked Finance Customer", email="finance-linked@example.test",
        created_by_person_id="person.owner",
    )

    restarted = SupportCaseService(
        repository, domain_store=domains, object_store=objects,
    )

    assert restarted.ensure_setup("acme")["setup_hash"] == setup["setup_hash"]
    assert restarted._get(
        "acme", "knowledge", knowledge["knowledge_id"], "knowledge_hash"
    )["title"] == "Private warranty policy"
    assert not (repository.base_dir / "acme" / "support" / "case_management").exists()
    assert not (repository.base_dir / "acme" / "sales" / "revenue_spine").exists()
    assert not (repository.base_dir / "acme" / "finance" / "sales").exists()
    assert domains.list("sales.records", workspace_id="acme")
    assert domains.list("finance.sales_records", workspace_id="acme")
    assert b"Private warranty policy" not in guardian.database.read_bytes()


def test_support_attachment_is_encrypted_linked_to_case_and_survives_restart(monkeypatch, tmp_path):
    repository, _ = configure(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    key = b"a" * 32
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=key)
    domains = VaultDomainStore(guardian)
    objects = VaultObjectStore(
        layout, guardian=guardian, business_stable_id="acme", encryption_key=key,
    )
    subject = SupportCaseService(
        repository, domain_store=domains, object_store=objects,
    )
    case = subject.create_case(
        "acme", channel="manual", subject="Contract evidence",
        message="Please retain the signed variation for review.",
        customer_name="Jamie Customer", email="jamie@example.test", phone=None,
        provider_thread_id=None, provider_message_id=None,
        source_reference="manual:contract-evidence", evidence_references=[],
        created_by_person_id="person.owner",
    )["case"]
    original = b"private signed variation evidence for support case"

    attachment = subject.capture_attachment(
        "acme", case["case_id"], filename="signed-variation.txt",
        content_type="text/plain", content=original,
        captured_by_person_id="person.owner",
    )

    assert attachment["status"] == "captured_protected"
    assert attachment["vault_receipt_hash"]
    _, recovered = objects.get_bytes(object_id=attachment["vault_object_id"])
    assert recovered == original
    assert original not in guardian.database.read_bytes()
    assert all(original not in path.read_bytes() for path in layout.files.rglob("*.tvobj"))

    restarted = SupportCaseService(
        repository, domain_store=domains, object_store=objects,
    )
    restored_case = restarted.load_case("acme", case["case_id"])
    assert restored_case["conversation"][-1]["evidence_references"] == [
        f"support-attachment:{attachment['attachment_id']}"
    ]
    stored_attachment = restarted._get(
        "acme", "attachment_metadata", attachment["attachment_id"], "attachment_hash"
    )
    assert stored_attachment["sha256"] == attachment["sha256"]
