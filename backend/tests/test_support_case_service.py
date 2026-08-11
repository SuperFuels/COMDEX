from __future__ import annotations

import json
from pathlib import Path
import pytest

from backend.modules.aion_business.runtime.support_case_service import SupportCaseService
from backend.tests.test_finance_bookkeeping_service import configure


def setup_support(monkeypatch, tmp_path: Path):
    repository, _ = configure(monkeypatch, tmp_path)
    service = SupportCaseService(repository)
    service.sales.create_enquiry(
        "acme", name="Jamie Customer", email="jamie@example.test", phone="+34600123456",
        company_name=None, enquiry="Roof repair", source="website", source_reference="lead-1",
        attribution={}, consent={"contact_permission": "inbound_response"},
        created_by_person_id="person.owner")
    return service


def create_case(service: SupportCaseService, **overrides):
    payload = {
        "channel": "email", "subject": "Where is my repair update?",
        "message": "Please tell me the status of the roof repair.",
        "customer_name": "Jamie Customer", "email": "jamie@example.test", "phone": None,
        "provider_thread_id": "thread-1", "provider_message_id": "message-1",
        "source_reference": "gmail:message-1", "evidence_references": ["gmail:message-1"],
        "created_by_person_id": "person.owner",
    }
    payload.update(overrides)
    return service.create_case("acme", **payload)


def test_case_is_deduplicated_matched_classified_and_preserves_conversation_evidence(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    result = create_case(service)
    case = result["case"]
    assert result["deduplicated"] is False
    assert case["category"] == "status"
    assert case["customer"]["contact_id"]
    assert {row["record_type"] for row in case["linked_records"]} == {"sales_contact", "sales_opportunity"}
    assert case["conversation"][0]["provider_thread_id"] == "thread-1"
    assert case["conversation"][0]["content_hash"].startswith("sha256:")
    duplicate = create_case(service)
    assert duplicate["deduplicated"] is True
    assert duplicate["case"]["case_id"] == case["case_id"]


def test_legal_safety_and_human_requests_fail_closed_to_intervention(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    case = create_case(
        service, subject="Unsafe work and legal action",
        message="This is unsafe. I want a real person and my lawyer will take legal action.",
        source_reference="gmail:message-legal", provider_message_id="message-legal")["case"]
    assert case["priority"] == "critical"
    assert case["status"] == "human_intervention_required"
    assert {"safety", "legal_threat", "consumer_rights", "customer_requests_human"}.issubset(case["risk_flags"])
    assert case["escalation"]["required"] is True


def test_consumer_rights_decision_without_terms_and_law_sources_requires_human(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    case = create_case(service, subject="Refund requested",
                       message="I need a refund for this service.",
                       source_reference="gmail:rights-1", provider_message_id="rights-1")["case"]
    response = service.prepare_response(
        "acme", case["case_id"], proposed_body="We are reviewing the refund request.",
        requested_action="recommend_refund_or_compensation", remedy_amount=25,
        prepared_by_person_id="person.owner")
    assert response["status"] == "human_intervention_required"
    assert set(response["missing_authority"]) >= {
        "applicable_consumer_law_source", "approved_business_terms"}
    assert response["refund_executed"] is False


def test_agent_configuration_forces_refunds_and_legal_conclusions_to_remain_governed(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    current = service.ensure_setup("acme")
    configured = service.configure_agent(
        "acme", expected_setup_hash=current["setup_hash"], configured_by_person_id="person.owner",
        setup={**current, "supported_channels": ["email", "telephone"],
               "remedy_policy": {"automatic_refund_enabled": True, "automatic_refund_limit": 500,
                                   "exact_approval_refund_limit": 250},
               "legal_policy": {"consumer_law_sources_required": False,
                                  "terms_source_required": False,
                                  "legal_conclusion_without_authority": "allowed"}})
    assert configured["remedy_policy"]["automatic_refund_enabled"] is False
    assert configured["remedy_policy"]["automatic_refund_limit"] == 0
    assert configured["legal_policy"]["consumer_law_sources_required"] is True
    assert configured["legal_policy"]["legal_conclusion_without_authority"] == "human_escalation"


def test_refund_response_cites_policy_requires_exact_approval_and_never_executes(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    service.add_knowledge(
        "acme", title="Approved refund policy", source_type="refund_policy",
        content="Verified duplicate charges may be refunded after exact approval up to EUR 250.",
        source_reference="policy:refund:v1", jurisdiction="Spain", effective_from="2026-08-01",
        approved_by_person_id="person.owner")
    service.add_knowledge(
        "acme", title="Approved customer terms", source_type="terms",
        content="Approved customer terms require refunds and remedies to be reviewed against applicable rights.",
        source_reference="terms:customer:v1", jurisdiction="Spain", effective_from="2026-08-01",
        approved_by_person_id="person.owner")
    service.add_knowledge(
        "acme", title="Applicable consumer-rights authority", source_type="consumer_law",
        content="Authoritative consumer-rights source supplied for controlled test evaluation only.",
        source_reference="authority:consumer-rights:test", jurisdiction="Spain", effective_from="2026-08-01",
        approved_by_person_id="person.owner")
    case = create_case(service, subject="Duplicate charge refund",
                       message="I was charged twice and need a refund.",
                       source_reference="gmail:refund-1", provider_message_id="refund-1")["case"]
    response = service.prepare_response(
        "acme", case["case_id"], proposed_body="We found the duplicate charge and have prepared it for review.",
        requested_action="recommend_refund_or_compensation", remedy_amount=25,
        prepared_by_person_id="person.owner")
    assert response["status"] == "exact_approval_required"
    assert {row["source_type"] for row in response["knowledge_citations"]} >= {"refund_policy", "terms", "consumer_law"}
    assert response["external_message_sent"] is False and response["refund_executed"] is False
    approved = service.approve_response(
        "acme", response["response_id"], expected_response_hash=response["response_hash"],
        approved_by_person_id="person.owner")
    assert approved["status"] == "approved_not_sent"
    assert approved["external_message_sent"] is False


def test_resolution_requires_independent_evidence(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    case = create_case(service)["case"]
    with pytest.raises(ValueError, match="independent_support_resolution_authority_required"):
        service.resolve("acme", case["case_id"], outcome="Resolved", evidence_reference="self-score",
                        authority_type="aion_self_assessment", resolved_by_person_id="person.owner")
    resolved = service.resolve("acme", case["case_id"], outcome="Customer confirmed repair completed",
                               evidence_reference="gmail:customer-confirmation-2",
                               authority_type="customer_confirmation",
                               resolved_by_person_id="person.owner")
    assert resolved["status"] == "resolved"
    assert resolved["resolution"]["authority_type"] == "customer_confirmation"


def test_hash_tampering_is_rejected(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    case = create_case(service)["case"]
    path = service._dir("acme", "cases") / f"{case['case_id']}.json"
    payload = json.loads(path.read_text())
    payload["status"] = "resolved"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="support_record_integrity_failed"):
        service.load_case("acme", case["case_id"])


def test_gmail_import_creates_one_case_then_continues_the_same_thread(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    first = service.import_gmail_messages(
        "acme", imported_by_person_id="person.owner", messages=[{
            "id": "gmail-101", "threadId": "thread-support-7",
            "from": "Jamie Customer <jamie@example.test>",
            "subject": "Help with roof repair", "body": "Please give me a status update.",
        }])
    assert first == {"imported": 1, "continued": 0, "deduplicated": 0,
                     "skipped": [], "gmail_mutated": False, "reply_sent": False}
    second = service.import_gmail_messages(
        "acme", imported_by_person_id="person.owner", messages=[{
            "id": "gmail-102", "threadId": "thread-support-7",
            "from": "Jamie Customer <jamie@example.test>",
            "subject": "Re: Help with roof repair",
            "body": "I want a real person because this now feels unsafe.",
        }])
    assert second["continued"] == 1
    cases = service.list_cases("acme")
    assert len(cases) == 1
    assert len(cases[0]["conversation"]) == 2
    assert cases[0]["status"] == "human_intervention_required"
    duplicate = service.import_gmail_messages(
        "acme", imported_by_person_id="person.owner", messages=[{
            "id": "gmail-102", "threadId": "thread-support-7",
            "from": "Jamie Customer <jamie@example.test>", "body": "duplicate",
        }])
    assert duplicate["deduplicated"] == 1


def test_secured_website_intake_is_token_bound_idempotent_and_honeypot_protected(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    endpoint = service.create_intake_endpoint(
        "acme", name="Customer help", created_by_person_id="person.owner")
    assert endpoint["token"] and "token_sha256" not in endpoint
    payload = {"event_id": "web-support-1", "subject": "Service issue",
               "message": "The completed repair is not working.",
               "name": "Jamie Customer", "email": "jamie@example.test"}
    with pytest.raises(PermissionError, match="token_invalid"):
        service.ingest_website_case("acme", endpoint["endpoint_id"], token="wrong",
                                    payload=payload)
    accepted = service.ingest_website_case(
        "acme", endpoint["endpoint_id"], token=endpoint["token"], payload=payload)
    assert accepted["accepted"] is True
    assert accepted["case"]["category"] == "quality_fault"
    duplicate = service.ingest_website_case(
        "acme", endpoint["endpoint_id"], token=endpoint["token"], payload=payload)
    assert duplicate["deduplicated"] is True
    trapped = service.ingest_website_case(
        "acme", endpoint["endpoint_id"], token=endpoint["token"],
        payload={**payload, "event_id": "web-support-bot", "website": "spam.example"})
    assert trapped == {"accepted": False, "reason": "honeypot_triggered"}


def test_approved_email_response_creates_provider_draft_but_never_sends(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    case = create_case(service)["case"]
    response = service.prepare_response(
        "acme", case["case_id"], proposed_body="We have your request and will confirm the next step.",
        requested_action="prepare_reply", remedy_amount=None,
        prepared_by_person_id="person.owner")
    approved = service.approve_response(
        "acme", response["response_id"], expected_response_hash=response["response_hash"],
        approved_by_person_id="person.owner")

    class Runtime:
        def _create_gmail_draft(self, **payload):
            assert payload["thread_id"] == "thread-1"
            return {"draft_id": "draft-1", "message_id": "gmail-out-1",
                    "thread_id": payload["thread_id"], "sent": False}

    import backend.api.local_node_router as router
    monkeypatch.setattr(router, "get_runtime", lambda: Runtime())
    executed = service.execute_response_draft(
        "acme", approved["response_id"], expected_response_hash=approved["response_hash"],
        executed_by_person_id="person.owner")
    assert executed["status"] == "provider_draft_created"
    assert executed["external_message_sent"] is False
    updated = service.load_case("acme", case["case_id"])
    assert updated["conversation"][-1]["direction"] == "outbound_draft"


def test_polling_configuration_is_exact_bound_and_runs_narrow_sources(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    current = service.polling_config("acme")
    configured = service.configure_polling(
        "acme", expected_polling_hash=current["polling_hash"], enabled=True,
        interval_seconds=120, sources={"gmail": True, "website_queue": True},
        gmail_query="in:inbox newer_than:7d subject:support",
        configured_by_person_id="person.owner")
    assert configured["enabled"] is True and configured["actor_person_id"] == "person.owner"

    class Runtime:
        def fetch_gmail_messages_readonly(self, **_): return []
    import backend.api.local_node_router as router
    monkeypatch.setattr(router, "get_runtime", lambda: Runtime())
    monkeypatch.setattr(service, "poll_homefixed_support_queue",
                        lambda *args, **kwargs: {"accepted": 0, "deduplicated": 0})
    result = service.poll_sources("acme", force=True)
    assert result["status"] == "completed" and result["errors"] == {}
    assert service.polling_config("acme")["next_poll_at"]


def test_whatsapp_webhook_is_token_bound_deduplicated_and_media_fail_closed(monkeypatch, tmp_path):
    service = setup_support(monkeypatch, tmp_path)
    current = service.whatsapp_config("acme")
    configured = service.configure_whatsapp(
        "acme", expected_whatsapp_hash=current["whatsapp_hash"], sender="+14150001111",
        sender_verified=False, live_send_enabled=True, configured_by_person_id="person.owner")
    assert configured["live_send_enabled"] is False
    payload = {"MessageSid": "SM-support-1", "From": "whatsapp:+34600123456",
               "Body": "My repair is broken and I need help", "NumMedia": "1",
               "MediaUrl0": "https://attacker.example/file", "MediaContentType0": "image/jpeg"}
    with pytest.raises(PermissionError, match="token_invalid"):
        service.ingest_whatsapp_webhook("acme", configured["endpoint_id"], token="wrong", payload=payload)
    accepted = service.ingest_whatsapp_webhook(
        "acme", configured["endpoint_id"], token=configured["webhook_token"], payload=payload)
    assert accepted["case"]["source_channel"] == "whatsapp"
    assert accepted["attachments"][0]["status"] == "capture_failed"
    duplicate = service.ingest_whatsapp_webhook(
        "acme", configured["endpoint_id"], token=configured["webhook_token"], payload=payload)
    assert duplicate["deduplicated"] is True
