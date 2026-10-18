from __future__ import annotations

import hashlib

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService
from backend.modules.aion_business.runtime.support_case_service import SupportCaseService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.tests.test_finance_bookkeeping_service import configure


def test_email_delivery_reply_and_replay_survive_encrypted_vault_restart(monkeypatch, tmp_path):
    repository, _ = configure(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    key = b"e" * 32
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=key)
    domains = VaultDomainStore(guardian)
    objects = VaultObjectStore(
        layout, guardian=guardian, business_stable_id="acme", encryption_key=key,
    )
    sales = SalesRevenueService(repository, domain_store=domains, object_store=objects)
    support = SupportCaseService(repository, domain_store=domains, object_store=objects)
    opportunity = sales.create_enquiry(
        "acme", name="Journey Eleven Customer", email="journey11@example.test",
        phone=None, company_name=None, enquiry="Please send a written update.",
        source="website", source_reference="journey-11-enquiry", attribution={},
        consent={"contact_permission": "inbound_response"},
        created_by_person_id="person.owner",
    )["opportunity"]
    draft = sales.append_work_event(
        "acme", opportunity["opportunity_id"], kind="outbound_draft",
        title="Written customer update", summary="The reviewed update is ready to send.",
        details={"recipient": "journey11@example.test"}, lifecycle_stage=None,
        source="communications", provider="tessaris", source_reference="journey-11-draft",
        attachments=[], action={"status": "approved", "external_action_performed": False},
        recorded_by_person_id="person.owner",
    )["event"]
    message_body = "Private Journey Eleven provider message body."
    payload = dict(
        provider="provider-sandbox", provider_message_id="journey-11-message-1",
        provider_thread_id="journey-11-thread-1", channel="email",
        recipient="journey11@example.test", subject="Your written update",
        content_sha256=hashlib.sha256(message_body.encode()).hexdigest(),
        delivery_status="delivered", linked_draft_event_id=draft["event_id"],
        sent_at="2026-10-18T01:00:00+00:00", recorded_by_person_id="person.owner",
    )
    first = sales.record_message_delivery("acme", opportunity["opportunity_id"], **payload)
    replay = sales.record_message_delivery("acme", opportunity["opportunity_id"], **payload)
    assert first["deduplicated"] is False and replay["deduplicated"] is True
    with pytest.raises(ValueError, match="message_delivery_receipt_conflict"):
        sales.record_message_delivery(
            "acme", opportunity["opportunity_id"],
            **{**payload, "content_sha256": "f" * 64},
        )

    reply = {
        "id": "journey-11-reply-1", "threadId": "journey-11-thread-1",
        "from": "Journey Eleven Customer <journey11@example.test>",
        "subject": "Re: Your written update",
        "body": "Private Journey Eleven customer reply.",
    }
    imported = support.import_gmail_messages(
        "acme", messages=[reply], imported_by_person_id="person.owner",
    )
    duplicate = support.import_gmail_messages(
        "acme", messages=[reply], imported_by_person_id="person.owner",
    )
    assert imported["imported"] == 1
    assert duplicate["deduplicated"] == 1
    case = support.list_cases("acme")[0]
    assert {row["record_type"] for row in case["linked_records"]} >= {
        "sales_contact", "sales_opportunity",
    }

    restarted_sales = SalesRevenueService(
        repository, domain_store=domains, object_store=objects,
    )
    restarted_support = SupportCaseService(
        repository, domain_store=domains, object_store=objects,
    )
    restored_feed = restarted_sales.get_work_feed("acme", opportunity["opportunity_id"])
    assert len([row for row in restored_feed["events"] if row["kind"] == "outbound_message"]) == 1
    assert restarted_support.list_cases("acme")[0]["conversation"][0]["provider_message_id"] == "journey-11-reply-1"
    assert domains.list("sales.records", workspace_id="acme")
    assert domains.list("sales.audit", workspace_id="acme")
    assert domains.list("support.records", workspace_id="acme")
    assert domains.list("departments.operational_audit", workspace_id="acme")
    raw = guardian.database.read_bytes()
    assert message_body.encode() not in raw
    assert b"Private Journey Eleven customer reply." not in raw

