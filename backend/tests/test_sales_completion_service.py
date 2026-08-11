from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import pytest

from backend.modules.aion_business.runtime.sales_completion_service import SalesCompletionService
from backend.tests.test_finance_bookkeeping_service import configure


def setup(monkeypatch, tmp_path: Path):
    repository, _ = configure(monkeypatch, tmp_path)
    service = SalesCompletionService(repository)
    result = service.sales.create_enquiry(
        "acme", name="Jamie Customer", email="jamie@example.test", phone="+34600123456",
        company_name=None, enquiry="Need a roof repair", source="website", source_reference="web-1",
        attribution={"utm_source": "google"}, consent={"contact_permission": "inbound_response"},
        created_by_person_id="person.owner")
    opportunity_id = result["opportunity"]["opportunity_id"]
    service.sales.qualify("acme", opportunity_id,
        answers={"need": "Roof repair", "location": "Mojacar", "urgency": "This month"},
        notes=None, qualified_by_person_id="person.owner")
    return service, opportunity_id


def test_booking_quote_acceptance_and_department_handoffs(monkeypatch, tmp_path):
    service, opportunity_id = setup(monkeypatch, tmp_path)
    availability = service.set_availability("acme", person_id="person.owner", timezone="Europe/Madrid",
        weekly_hours={"monday": [["09:00", "17:00"]]}, buffer_minutes=15,
        changed_by_person_id="person.owner")
    assert availability["availability_hash"].startswith("sha256:")
    starts = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0).isoformat()
    booking = service.prepare_booking("acme", opportunity_id, starts_at=starts, duration_minutes=45,
        assigned_person_id="person.owner", channel="Site visit", prepared_by_person_id="person.owner")
    confirmed = service.approve_booking("acme", booking["booking_id"],
        expected_booking_hash=booking["booking_hash"], approved_by_person_id="person.owner")
    assert confirmed["status"] == "confirmed_internal" and confirmed["external_calendar_write"] is False

    quote = service.prepare_quote("acme", opportunity_id,
        lines=[{"description": "Roof inspection and repair", "quantity": 1,
                "unit_amount": 1000, "tax_rate": 21}], valid_days=14,
        terms="Subject to site inspection", prepared_by_person_id="person.owner")
    assert quote["total"] == 1210
    with pytest.raises(ValueError, match="changed_since_review"):
        service.approve_quote("acme", quote["quote_id"], expected_quote_hash="wrong",
                              approved_by_person_id="person.owner")
    approved = service.approve_quote("acme", quote["quote_id"],
        expected_quote_hash=quote["quote_hash"], approved_by_person_id="person.owner")
    accepted = service.record_quote_acceptance("acme", quote["quote_id"],
        evidence_reference="customer-email:accepted-001", recorded_by_person_id="person.owner")
    assert approved["external_message_sent"] is False and accepted["status"] == "accepted_by_customer"
    handoffs = service.create_handoffs("acme", quote["quote_id"],
        operations_owner_person_id="person.owner", created_by_person_id="person.owner")
    assert handoffs["operations"]["status"] == "ready_for_delivery_planning"
    assert handoffs["finance"]["invoice_id"] == handoffs["invoice"]["invoice_id"]
    assert handoffs["invoice"]["status"] == "exact_internal_approval_required"


def test_messages_campaign_consent_and_outcome_experiment(monkeypatch, tmp_path):
    service, opportunity_id = setup(monkeypatch, tmp_path)
    message = service.prepare_message("acme", opportunity_id, channel="email", purpose="quote_follow_up",
        subject="Your Home Fixed enquiry", body="Thanks for your enquiry. We can arrange a site visit.",
        prepared_by_person_id="person.owner")
    approved = service.approve_message("acme", message["message_id"],
        expected_message_hash=message["message_hash"], approved_by_person_id="person.owner")
    assert approved["status"] == "approved_not_sent" and approved["external_message_sent"] is False
    campaign = service.create_campaign("acme", name="Roof follow-up", channel="email", variant="challenger",
        contacts=[{"name": "Allowed", "email": "yes@example.test", "contact_permission": "explicit_outbound"},
                  {"name": "Blocked", "email": "no@example.test", "contact_permission": "unknown"}],
        created_by_person_id="person.owner")
    assert len(campaign["eligible_contacts"]) == len(campaign["excluded_contacts"]) == 1
    service.record_outcome("acme", opportunity_id, disposition="appointment", value=0,
        reason="Customer booked", variant="challenger", authority_reference="booking:confirmed",
        recorded_by_person_id="person.owner")
    experiment = service.evaluate_experiment("acme", control_variant="control", challenger_variant="challenger",
        minimum_samples=1, evaluated_by_person_id="person.owner")
    assert experiment["status"] == "insufficient_independent_outcomes"
    assert experiment["automatic_promotion"] is False


def test_post_call_confirmation_is_deterministic_goal_bound_and_not_sent(monkeypatch, tmp_path):
    service, opportunity_id = setup(monkeypatch, tmp_path)
    playbook = service.sales.ensure_default_playbook("acme")
    playbook["status"] = "promoted_for_controlled_use"
    service.sales._rehash(playbook, "playbook_hash")
    service.sales._write(service.sales._playbook_path("acme", "inbound-enquiry"), playbook)
    draft = service.sales.prepare_outbound_call(
        "acme", opportunity_id, reason="Qualify the roof enquiry",
        goals={"desired_outcome": "site_visit_request",
               "evidence_route": {"mode": "human_follow_up_required"}},
        prepared_by_person_id="person.owner")
    message = service.prepare_post_call_confirmation(
        "acme", opportunity_id, call_draft_id=draft["draft_id"],
        provider_call_id="call-test", channel="sms",
        captured_fields={"work_required": "Roof repair", "property_location": "Mojacar"},
        missing_fields=["preferred_follow_up_time", "not_a_contract_field"],
        prepared_by_person_id="person.owner")
    assert message["status"] == "exact_approval_required"
    assert message["external_message_sent"] is False
    assert message["call_goal_contract_hash"] == draft["call_goal_contract_hash"]
    assert message["missing_fields"] == ["preferred_follow_up_time"]
    assert "person from the business will confirm the approved route" in message["payload"]["body"]
    assert "No price, appointment or work is confirmed" in message["payload"]["body"]


def test_unanswered_calls_retry_then_continue_same_goals_by_approved_email(monkeypatch, tmp_path):
    service, opportunity_id = setup(monkeypatch, tmp_path)
    playbook = service.sales.ensure_default_playbook("acme")
    playbook["agent_setup"]["contact_sequence"] = {
        "maximum_phone_attempts": 2, "fallback_channel": "email",
        "continue_same_goal_contract": True, "questions_per_written_message": 2,
        "automatic_send": False,
    }
    playbook["status"] = "promoted_for_controlled_use"
    service.sales._rehash(playbook, "playbook_hash")
    service.sales._write(service.sales._playbook_path("acme", "inbound-enquiry"), playbook)

    first = service.sales.prepare_outbound_call(
        "acme", opportunity_id, reason="Respond to the enquiry",
        prepared_by_person_id="person.owner")
    retry = service.prepare_contact_fallback(
        "acme", opportunity_id, call_draft_id=first["draft_id"], provider_call_id="call-1",
        provider_status="not_connected", disconnection_reason="dial_no_answer",
        prepared_by_person_id="person.owner")
    assert retry["status"] == "telephone_retry_requires_approval"
    assert retry["next_attempt_number"] == 2

    second = service.sales.prepare_outbound_call(
        "acme", opportunity_id, reason="Approved second attempt",
        prepared_by_person_id="person.owner")
    fallback = service.prepare_contact_fallback(
        "acme", opportunity_id, call_draft_id=second["draft_id"], provider_call_id="call-2",
        provider_status="not_connected", disconnection_reason="dial_no_answer",
        prepared_by_person_id="person.owner")
    assert second["attempt_number"] == 2
    assert fallback["status"] == "fallback_message_exact_approval_required"
    assert fallback["next_channel"] == "email"
    assert fallback["destination"] == "jamie@example.test"
    assert fallback["automatic_send"] is False
    assert fallback["call_goal_contract_hash"] == second["call_goal_contract_hash"]
    message = service._get("acme", "messages", fallback["message_id"], "message_hash")
    assert message["status"] == "exact_approval_required"
    assert message["external_message_sent"] is False
    assert "without making you repeat information already confirmed" in message["payload"]["body"]
    assert fallback["questions_requested"] == [
        "immediate_safety_risk", "photos_or_documents_available"]

    continued = service.prepare_written_goal_continuation(
        "acme", opportunity_id, call_draft_id=second["draft_id"], channel="email",
        confirmed_fields={"immediate_safety_risk": "No",
                          "photos_or_documents_available": "Yes"},
        prepared_by_person_id="person.owner")
    assert continued["status"] == "next_message_exact_approval_required"
    assert continued["call_goal_contract_hash"] == second["call_goal_contract_hash"]
    assert continued["next_questions"] == [
        "preferred_follow_up_channel", "preferred_follow_up_time"]

    completed = service.prepare_written_goal_continuation(
        "acme", opportunity_id, call_draft_id=second["draft_id"], channel="email",
        confirmed_fields={
            "preferred_follow_up_channel": "Email", "preferred_follow_up_time": "Afternoon",
            "decision_authority": "Owner",
        }, prepared_by_person_id="person.owner")
    assert completed["status"] == "qualification_goals_complete_human_booking_review_required"
    assert completed["booking_created"] is False


def test_workspace_exposes_all_remaining_sales_controls(monkeypatch, tmp_path):
    service, _ = setup(monkeypatch, tmp_path)
    workspace = service.workspace("acme")
    assert set(workspace["external_readiness"]) == {"gmail", "hubspot", "calendar", "sms", "telephone"}
    assert workspace["governance"]["quote_acceptance_requires_customer_evidence"] is True
    assert workspace["governance"]["playbook_promotion_requires_outcomes"] is True


def test_saved_legacy_owner_role_inherits_new_sales_capabilities(monkeypatch, tmp_path):
    service, _ = setup(monkeypatch, tmp_path)
    model = service.authority.get("acme")
    owner = next(role for role in model["roles"] if role["id"] == "role.owner_director")
    owner["capabilities"] = [value for value in owner["capabilities"] if not value.startswith("sales.")]
    service.repository.save_model(
        __import__("backend.modules.aion_business.contracts.business_containers", fromlist=["OrganizationAuthorityContainer"])
        .OrganizationAuthorityContainer(**model)
    )
    decision = service.authority.access_decision("acme", person_id="person.owner", capability="sales.manage")
    assert decision["allowed"] is True


def test_approved_email_executes_as_gmail_draft_and_never_sends(monkeypatch, tmp_path):
    service, opportunity_id = setup(monkeypatch, tmp_path)
    message = service.prepare_message("acme", opportunity_id, channel="email", purpose="follow_up",
        subject="Your enquiry", body="We can help.", prepared_by_person_id="person.owner")
    approved = service.approve_message("acme", message["message_id"],
        expected_message_hash=message["message_hash"], approved_by_person_id="person.owner")

    class Runtime:
        def get_gmail_connector_health(self):
            return {"auth_status": "connected", "connector_health": "available"}
        def _create_gmail_draft(self, **payload):
            assert payload["to"] == "jamie@example.test"
            return {"created": True, "sent": False, "draft_id": "draft-1", "message_id": "msg-1"}

    monkeypatch.setattr("backend.api.local_node_router.get_runtime", lambda: Runtime())
    executed = service.execute_message("acme", message["message_id"],
        expected_message_hash=approved["message_hash"], executed_by_person_id="person.owner")
    assert executed["status"] == "gmail_draft_created"
    assert executed["external_draft_created"] is True
    assert executed["external_message_sent"] is False


def test_message_execution_fails_closed_when_gmail_needs_reauthorization(monkeypatch, tmp_path):
    service, opportunity_id = setup(monkeypatch, tmp_path)
    message = service.prepare_message("acme", opportunity_id, channel="email", purpose="follow_up",
        subject="Your enquiry", body="We can help.", prepared_by_person_id="person.owner")
    approved = service.approve_message("acme", message["message_id"],
        expected_message_hash=message["message_hash"], approved_by_person_id="person.owner")

    class Runtime:
        def get_gmail_connector_health(self):
            return {"auth_status": "reauthorization_required", "connector_health": "not_connected"}

    monkeypatch.setattr("backend.api.local_node_router.get_runtime", lambda: Runtime())
    with pytest.raises(PermissionError, match="gmail_reauthorization_required"):
        service.execute_message("acme", message["message_id"],
            expected_message_hash=approved["message_hash"], executed_by_person_id="person.owner")


def test_confirmed_booking_creates_calendar_event_without_customer_notification(monkeypatch, tmp_path):
    service, opportunity_id = setup(monkeypatch, tmp_path)
    starts = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0).isoformat()
    booking = service.prepare_booking("acme", opportunity_id, starts_at=starts, duration_minutes=30,
        assigned_person_id="person.owner", channel="Site visit", prepared_by_person_id="person.owner")
    confirmed = service.approve_booking("acme", booking["booking_id"],
        expected_booking_hash=booking["booking_hash"], approved_by_person_id="person.owner")

    class Runtime:
        def get_gmail_connector_health(self):
            return {"auth_status": "connected", "connector_health": "available"}
        def _create_google_calendar_event(self, **payload):
            assert payload["summary"].startswith("Home Fixed enquiry")
            return {"created": True, "event_id": "event-1", "html_link": "https://calendar.test/event-1",
                    "attendees_notified": False}

    monkeypatch.setattr("backend.api.local_node_router.get_runtime", lambda: Runtime())
    executed = service.execute_booking("acme", booking["booking_id"],
        expected_booking_hash=confirmed["booking_hash"], executed_by_person_id="person.owner")
    assert executed["status"] == "calendar_event_created"
    assert executed["external_calendar_write"] is True
    assert executed["customer_notification_sent"] is False


def test_approved_sms_fails_closed_without_twilio_configuration(monkeypatch, tmp_path):
    service, opportunity_id = setup(monkeypatch, tmp_path)
    message = service.prepare_message("acme", opportunity_id, channel="sms", purpose="follow_up",
        subject=None, body="We can help.", prepared_by_person_id="person.owner")
    approved = service.approve_message("acme", message["message_id"],
        expected_message_hash=message["message_hash"], approved_by_person_id="person.owner")
    with pytest.raises(PermissionError, match="twilio_sms_provider_not_configured"):
        service.execute_message("acme", message["message_id"],
            expected_message_hash=approved["message_hash"], executed_by_person_id="person.owner")


def test_exact_approved_sms_uses_bounded_provider_receipt(monkeypatch, tmp_path):
    service, opportunity_id = setup(monkeypatch, tmp_path)
    message = service.prepare_message("acme", opportunity_id, channel="sms", purpose="follow_up",
        subject=None, body="We can help.", prepared_by_person_id="person.owner")
    approved = service.approve_message("acme", message["message_id"],
        expected_message_hash=message["message_hash"], approved_by_person_id="person.owner")
    monkeypatch.setattr(service, "_send_twilio_sms", lambda **_: {"sid": "SM-test", "status": "queued"})
    executed = service.execute_message("acme", message["message_id"],
        expected_message_hash=approved["message_hash"], executed_by_person_id="person.owner")
    assert executed["status"] == "sms_submitted"
    assert executed["external_message_sent"] is True
    assert executed["provider_result"]["message_sid"] == "SM-test"
