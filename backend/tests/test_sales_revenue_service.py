from __future__ import annotations

import json
import hashlib
import hmac
from pathlib import Path
import time
import urllib.request

import pytest

from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.tests.test_finance_bookkeeping_service import configure


def service(monkeypatch, tmp_path: Path) -> tuple[SalesRevenueService, object]:
    repository, authority = configure(monkeypatch, tmp_path)
    return SalesRevenueService(repository, authority), repository


def enquiry(sales: SalesRevenueService, *, source_reference: str = "website-1") -> dict:
    return sales.create_enquiry(
        "acme", name="Jamie Customer", email="Jamie@Example.test", phone="+34 600 123 456",
        company_name=None, enquiry="Boiler stopped working", source="website",
        source_reference=source_reference,
        attribution={"utm_source": "google", "utm_campaign": "boiler-repair", "unsafe": "drop"},
        consent={}, created_by_person_id="person.owner",
    )


def test_marketing_enquiry_is_deduplicated_at_contact_and_source_level(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    first = enquiry(sales)
    same_event = enquiry(sales)
    second_need = enquiry(sales, source_reference="website-2")
    assert first["contact"]["email"] == "jamie@example.test"
    assert first["opportunity"]["attribution"] == {
        "utm_source": "google", "utm_campaign": "boiler-repair",
    }
    assert first["opportunity"]["consent"]["customer_initiated"] is True
    assert first["opportunity"]["consent"]["outbound_campaign_allowed"] is False
    assert same_event["opportunity"]["opportunity_id"] == first["opportunity"]["opportunity_id"]
    assert same_event["duplicate_reason"] == "source_reference"
    assert second_need["contact"]["contact_id"] == first["contact"]["contact_id"]
    assert len(sales.list_contacts("acme")) == 1
    assert len(sales.list_opportunities("acme")) == 2


def test_company_identity_is_canonical_and_shared_across_people(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    first = sales.create_enquiry(
        "acme", name="Jamie", email="jamie@buyer.test", phone=None, company_name="Buyer Limited",
        enquiry="First need", source="referral", source_reference="r1", attribution={}, consent={},
        created_by_person_id="person.owner",
    )
    second = sales.create_enquiry(
        "acme", name="Alex", email="alex@buyer.test", phone=None, company_name="buyer limited",
        enquiry="Second need", source="referral", source_reference="r2", attribution={}, consent={},
        created_by_person_id="person.owner",
    )
    assert first["contact"]["company_id"] == second["contact"]["company_id"]
    assert len(sales.list_companies("acme")) == 1


def test_manual_b2b_enquiry_preserves_contact_role_department_and_extension(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    result = sales.create_enquiry(
        "acme", name="Kevin Robinson", first_name="Kevin", last_name="Robinson",
        customer_type="business", email="kevin@buyer.test", phone="+44 20 7000 0000",
        phone_extension="204", address="10 Business Park, London",
        company_name="Buyer Limited", position_title="Operations Director",
        department="Operations", enquiry="Need a managed service proposal", source="manual",
        source_reference=None, attribution={}, consent={}, created_by_person_id="person.owner",
    )
    contact = result["contact"]
    projected = result["opportunity"]["contact"]
    assert contact["customer_type"] == "business"
    assert contact["first_name"] == "Kevin"
    assert contact["last_name"] == "Robinson"
    assert contact["company_name"] == "Buyer Limited"
    assert contact["position_title"] == "Operations Director"
    assert contact["department"] == "Operations"
    assert contact["phone_extension"] == "204"
    assert contact["address"] == "10 Business Park, London"
    assert projected["position_title"] == "Operations Director"
    assert projected["phone_extension"] == "204"


def test_business_enquiry_requires_a_company(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="sales_business_company_name_required"):
        sales.create_enquiry(
            "acme", name="Kevin Robinson", customer_type="business",
            email="kevin@buyer.test", phone=None, company_name=None,
            enquiry="Need a proposal", source="manual", source_reference=None,
            attribution={}, consent={}, created_by_person_id="person.owner",
        )


def test_owner_can_add_an_existing_deal_at_its_real_commercial_stage(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    result = sales.create_enquiry(
        "acme", name="Morgan Client", email="morgan@example.test", phone=None,
        company_name=None, enquiry="Existing annual support proposal", source="manual",
        source_reference=None, attribution={}, consent={}, created_by_person_id="person.owner",
        entry_mode="existing_deal", initial_stage="proposal", estimated_value=12500,
        currency="GBP", next_action="Manager to approve proposal",
    )
    opportunity = result["opportunity"]
    assert opportunity["stage"] == "proposal"
    assert opportunity["deal"] == {
        "entry_mode": "existing_deal", "estimated_value": 12500.0,
        "currency": "GBP", "imported_as_existing": True,
    }
    assert opportunity["relationship"]["next_action"] == "Manager to approve proposal"
    assert opportunity["work_feed"]["current_stage"] == "quote"
    assert [event["title"] for event in opportunity["work_feed"]["events"]] == [
        "Enquiry received", "Existing deal added",
    ]


def test_customer_relationship_is_native_signed_and_shared_with_the_work_feed(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    created = enquiry(sales)
    opportunity_id = created["opportunity"]["opportunity_id"]

    updated = sales.update_relationship(
        "acme", opportunity_id,
        relationship_status="active_job", priority="priority",
        preferred_channel="whatsapp", next_action="Collect the remaining 50%",
        next_action_due="2026-09-01", tags=["Roofing", "Repeat customer", "roofing"],
        owner_person_id="person.owner", address="12 Example Street, Almeria",
        updated_by_person_id="person.owner",
    )

    assert updated["relationship"]["status"] == "active_job"
    assert updated["relationship"]["priority"] == "priority"
    assert updated["relationship"]["preferred_channel"] == "whatsapp"
    assert updated["relationship"]["next_action"] == "Collect the remaining 50%"
    assert updated["relationship"]["tags"] == ["Roofing", "Repeat customer"]
    assert updated["relationship"]["updated_by_person_id"] == "person.owner"
    assert updated["contact"]["address"] == "12 Example Street, Almeria"
    assert updated["work_feed"]["events"][-1]["title"] == "Relationship details updated"
    assert updated["work_feed"]["events"][-1]["recorded_by_person_id"] == "person.owner"
    assert sales.list_contacts("acme")[0]["address"] == "12 Example Street, Almeria"
    assert sales.workspace("acme")["today_queue"][0]["next_action"] == "Collect the remaining 50%"


def test_customer_relationship_rejects_invalid_owner_and_due_date(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    opportunity_id = enquiry(sales)["opportunity"]["opportunity_id"]
    base = dict(
        relationship_status="lead", priority="normal", preferred_channel="email",
        next_action=None, tags=[], address=None, updated_by_person_id="person.owner",
    )
    with pytest.raises(ValueError, match="valid_customer_next_action_date_required"):
        sales.update_relationship("acme", opportunity_id, owner_person_id="person.owner",
                                  next_action_due="tomorrow", **base)
    with pytest.raises(ValueError, match="customer_relationship_owner_not_active"):
        sales.update_relationship("acme", opportunity_id, owner_person_id="person.unknown",
                                  next_action_due=None, **base)


def test_legacy_underscore_business_alias_remains_inside_same_sales_workspace(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    playbook = sales.ensure_default_playbook("home-fixed")
    playbook["workspace_id"] = "home_fixed"
    sales._rehash(playbook, "playbook_hash")
    sales._write(AIONBusinessPaths.business_container_dir("home-fixed") / "sales/revenue_spine/playbooks/inbound-enquiry.json", playbook)

    workspace = sales.workspace("home-fixed")

    assert workspace["workspace_id"] == "home-fixed"
    assert workspace["playbook"]["workspace_id"] == "home_fixed"


def test_different_business_record_still_fails_sales_workspace_isolation(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    playbook = sales.ensure_default_playbook("home-fixed")
    playbook["workspace_id"] = "another-business"
    sales._rehash(playbook, "playbook_hash")
    sales._write(AIONBusinessPaths.business_container_dir("home-fixed") / "sales/revenue_spine/playbooks/inbound-enquiry.json", playbook)

    with pytest.raises(PermissionError, match="sales_workspace_isolation_violation"):
        sales.workspace("home-fixed")


def test_qualification_handoff_and_booking_are_governed(monkeypatch, tmp_path):
    sales, repository = service(monkeypatch, tmp_path)
    opportunity = enquiry(sales)["opportunity"]
    qualified = sales.qualify(
        "acme", opportunity["opportunity_id"],
        answers={"need": "Repair boiler", "location": "Almeria", "urgency": "Today",
                 "decision_maker": "Jamie"}, notes="Warm inbound lead",
        qualified_by_person_id="person.owner",
    )
    assert qualified["stage"] == "qualified"
    assert qualified["qualification"]["score"] == 95
    booked = sales.prepare_appointment(
        "acme", opportunity["opportunity_id"], starts_at="2026-08-10T10:00:00+02:00",
        duration_minutes=30, assigned_person_id="person.owner", location_or_channel="Phone",
        notes=None, prepared_by_person_id="person.owner",
    )
    assert booked["stage"] == "appointment_proposed"
    assert booked["appointments"][0]["external_calendar_write_performed"] is False
    assert booked["appointments"][0]["customer_notification_sent"] is False
    boardroom = repository.load_dict("acme", "boardroom_snapshot")
    assert boardroom["boardroom"]["runtime"]["sales_revenue_spine"]["summary"]["appointments"] == 1


def test_customer_work_feed_carries_the_job_from_enquiry_to_receipted_action(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    opportunity = enquiry(sales)["opportunity"]
    opportunity_id = opportunity["opportunity_id"]

    initial = sales.get_work_feed("acme", opportunity_id)
    assert initial["current_stage"] == "enquiry"
    assert [event["kind"] for event in initial["events"]] == ["enquiry_received"]

    surveyed = sales.append_work_event(
        "acme", opportunity_id, kind="photo", lifecycle_stage="survey",
        title="Site survey photographs", summary="Customer roof and access photographed.",
        details={"customer_visible": False, "caption": "North elevation and failed flashing"},
        source="pilot", provider="tessaris", source_reference="voice-session-1",
        action={"status": "recorded", "external_action_performed": False},
        recorded_by_person_id="person.owner",
        attachments=[{"name": "north-elevation.jpg", "media_type": "image/jpeg",
                      "sha256": "a" * 64, "size": 2048,
                      "source_reference": "business-file-cabinet/photo-1"}],
    )
    assert surveyed["work_feed"]["current_stage"] == "survey"
    assert surveyed["event"]["attachments"][0]["sha256"] == "a" * 64

    drafted = sales.append_work_event(
        "acme", opportunity_id, kind="quote_draft", lifecycle_stage="quote",
        title="Roof repair quotation", summary="Top-line customer quote prepared with VAT.",
        details={"customer_total": "2400.00", "currency": "GBP",
                 "terms": "50% deposit; balance on completion"},
        source="pilot", provider="tessaris", source_reference=None,
        attachments=[], action={"status": "draft", "external_action_performed": False},
        recorded_by_person_id="person.owner",
    )
    assert drafted["event"]["action"]["external_action_performed"] is False

    with pytest.raises(ValueError, match="executed_external_action_requires_receipt"):
        sales.append_work_event(
            "acme", opportunity_id, kind="quote_sent", lifecycle_stage="quote",
            title="Quotation sent", summary="Sent to customer",
            details={}, source="gmail", provider="google", source_reference=None,
            attachments=[], action={"status": "executed", "external_action_performed": True},
            recorded_by_person_id="person.owner",
        )

    sent = sales.append_work_event(
        "acme", opportunity_id, kind="quote_sent", lifecycle_stage="quote",
        title="Quotation sent", summary="Approved quotation delivered through Gmail.",
        details={"recipient": "jamie@example.test"}, source="gmail", provider="google",
        source_reference="gmail-message-id-123", attachments=[],
        action={"status": "executed", "external_action_performed": True,
                "receipt_reference": "gmail-message-id-123"},
        recorded_by_person_id="person.owner",
    )
    assert sent["event"]["action"]["external_action_performed"] is True
    assert sent["event"]["action"]["receipt_reference"] == "gmail-message-id-123"

    with pytest.raises(ValueError, match="lifecycle_cannot_move_backwards"):
        sales.append_work_event(
            "acme", opportunity_id, kind="note", lifecycle_stage="qualification",
            title="Invalid backwards move", summary="Must fail closed", details={},
            source="sales", provider="tessaris", source_reference=None, attachments=[],
            action={"status": "recorded", "external_action_performed": False},
            recorded_by_person_id="person.owner",
        )

    persisted = sales.load_opportunity("acme", opportunity_id)["work_feed"]
    assert persisted["current_stage"] == "quote"
    assert [event["kind"] for event in persisted["events"]][-3:] == [
        "photo", "quote_draft", "quote_sent",
    ]


def test_customer_work_feed_preserves_generic_business_files(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    created = enquiry(sales)
    opportunity_id = created["opportunity"]["opportunity_id"]

    attachment = sales.store_work_feed_attachment(
        "acme", opportunity_id, filename="Marketing proposal.pdf",
        content=b"%PDF-1.4 proposal", media_type="application/pdf",
        recorded_by_person_id="person.owner",
    )

    assert attachment["name"] == "Marketing proposal.pdf"
    assert attachment["media_type"] == "application/pdf"
    assert attachment["attachment_id"].startswith("customer-file-")
    path, metadata = sales.work_feed_attachment_path("acme", opportunity_id, attachment["attachment_id"])
    assert path.suffix == ".pdf"
    assert path.read_bytes() == b"%PDF-1.4 proposal"
    assert metadata["sha256"] == attachment["sha256"]


def test_voice_session_requires_ai_disclosure_and_records_structured_outcome(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    opportunity = enquiry(sales)["opportunity"]
    with pytest.raises(PermissionError, match="ai_identity_disclosure"):
        sales.start_session(
            "acme", opportunity["opportunity_id"], channel="telephone", provider="retell",
            ai_disclosure=False, recording_consent="not_recorded", started_by_person_id="person.owner",
        )
    active = sales.start_session(
        "acme", opportunity["opportunity_id"], channel="telephone", provider="retell",
        ai_disclosure=True, recording_consent="verbal_consent", started_by_person_id="person.owner",
    )
    assert active["sessions"][0]["external_transport_started"] is False
    completed = sales.complete_session(
        "acme", opportunity["opportunity_id"], "session-1", disposition="qualified",
        summary="Customer needs a boiler repair.", next_action="Book Kevin", human_takeover=True,
        completed_by_person_id="person.owner",
    )
    assert completed["sessions"][0]["status"] == "completed"
    assert completed["sessions"][0]["human_takeover"] is True


def test_hash_tampering_and_invalid_pipeline_transitions_fail_closed(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    opportunity = enquiry(sales)["opportunity"]
    with pytest.raises(ValueError, match="transition_not_allowed"):
        sales.update_stage("acme", opportunity["opportunity_id"], stage="won", reason="Skip",
                           changed_by_person_id="person.owner")
    path = sales._opportunity_path("acme", opportunity["opportunity_id"])
    payload = json.loads(path.read_text()); payload["stage"] = "won"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="hash_mismatch"):
        sales.load_opportunity("acme", opportunity["opportunity_id"])


def test_default_agent_playbook_stays_draft_until_simulated(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    playbook = sales.workspace("acme")["playbook"]
    assert playbook["status"] == "draft_simulation_required"
    assert playbook["simulation"] == {"passed": 0, "required": 11}
    assert playbook["external_deployment_performed"] is False
    assert "unsupported_question" in playbook["required_simulations"]


def test_secured_website_intake_authenticates_deduplicates_and_preserves_attribution(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    endpoint = sales.create_intake_endpoint(
        "acme", name="Quote form", created_by_person_id="person.owner")
    payload = {
        "event_id": "submission-001", "name": "Pat Prospect", "email": "pat@example.test",
        "enquiry": "Need a heat pump quote", "utm_source": "google",
        "utm_campaign": "heat-pump", "landing_page": "/heat-pumps",
    }
    with pytest.raises(PermissionError, match="token_invalid"):
        sales.ingest_website_enquiry("acme", endpoint["endpoint_id"], token="wrong", payload=payload)
    first = sales.ingest_website_enquiry(
        "acme", endpoint["endpoint_id"], token=endpoint["token"], payload=payload)
    second = sales.ingest_website_enquiry(
        "acme", endpoint["endpoint_id"], token=endpoint["token"], payload=payload)
    assert first["opportunity"]["attribution"] == {
        "landing_page": "/heat-pumps", "utm_source": "google", "utm_campaign": "heat-pump"}
    assert first["intake_evidence"]["authenticated"] is True
    assert second["duplicate_reason"] == "source_reference"
    public_endpoint = sales.list_intake_endpoints("acme")[0]
    assert "token_sha256" not in public_endpoint
    assert public_endpoint["receiver_path"].endswith(f"/acme/{endpoint['endpoint_id']}")
    honeypot = sales.ingest_website_enquiry(
        "acme", endpoint["endpoint_id"], token=endpoint["token"], payload={**payload, "website": "spam"})
    assert honeypot["accepted"] is False
    assert len(sales.list_opportunities("acme")) == 1


def test_authenticated_agent_request_enters_human_review_and_has_safe_status(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    endpoint = sales.create_intake_endpoint("acme", name="A2A ingress", created_by_person_id="person.owner")
    payload = {"event_id": "a2a:buyer-agent:req-1", "name": "Pat Principal", "email": "pat@example.test",
        "enquiry": "roofing: inspect a roof leak", "channel": "external_agent",
        "requesting_agent_id": "buyer-agent", "agent_request_id": "req-1",
        "customer_authority_reference": "signed-delegation-1", "requested_service": "roofing",
        "requested_window": "next week", "currency": "EUR"}
    with pytest.raises(PermissionError, match="customer_authority"):
        sales.ingest_website_enquiry("acme", endpoint["endpoint_id"], token=endpoint["token"],
                                     payload={**payload, "customer_authority_reference": None})
    accepted = sales.ingest_website_enquiry("acme", endpoint["endpoint_id"], token=endpoint["token"], payload=payload)
    opportunity = accepted["opportunity"]
    assert opportunity["source"] == "external_agent"
    assert opportunity["consent"]["contact_permission"] == "agent_authorized_response"
    assert accepted["intake_evidence"]["human_review_required"] is True
    status = sales.external_agent_status("acme", endpoint["endpoint_id"], token=endpoint["token"],
                                         requesting_agent_id="buyer-agent", agent_request_id="req-1")
    assert status["status"] == "new" and status["payment_created"] is False


def test_unknown_agent_public_intent_is_review_only_and_has_no_status_authority(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    endpoint = sales.create_intake_endpoint("acme", name="Public agent intent", created_by_person_id="person.owner")
    accepted = sales.ingest_website_enquiry("acme", endpoint["endpoint_id"], token=endpoint["token"], payload={
        "event_id": "public-agent:intent-1", "name": "Unverified requester",
        "email": "requester@example.test", "enquiry": "Need a roof inspection in Mojacar",
        "channel": "public_agent_intent", "requesting_agent_id": "unknown-agent",
        "requested_service": "roofing", "website": "",
    })
    assert accepted["opportunity"]["source"] == "public_agent_intent"
    assert accepted["opportunity"]["consent"]["contact_permission"] == "intent_review_only"
    evidence = accepted["intake_evidence"]
    assert evidence["human_review_required"] is True
    assert evidence["contact_authority_confirmed"] is False
    assert evidence["status_access_granted"] is False


def test_gmail_readonly_messages_become_real_deduplicated_opportunities(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    messages = [{"id": "gmail-1", "from": "Jamie Customer <jamie@example.test>",
                 "subject": "Quote enquiry", "body": "<p>Please quote for a boiler repair.</p>"}]
    first = sales.import_gmail_messages("acme", messages=messages, imported_by_person_id="person.owner")
    second = sales.import_gmail_messages("acme", messages=messages, imported_by_person_id="person.owner")
    assert first["imported"] == 1 and first["gmail_mutated"] is False and first["reply_sent"] is False
    assert second["deduplicated"] == 1
    assert sales.list_opportunities("acme")[0]["source_reference"] == "gmail:gmail-1"


def test_homefixed_queue_acknowledges_only_after_safe_canonical_import(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    endpoint = sales.create_intake_endpoint("acme", name="HomeFixed", created_by_person_id="person.owner")
    acknowledgements = []
    queued = {"ok": True, "has_more": False, "items": [{
        "pathname": "pending/human/web-1.json", "payload": {
            "event_id": "web-1", "name": "Home Owner", "email": "owner@example.test",
            "enquiry": "Need a plumber", "channel": "website", "website": "",
        }}]}

    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self): return json.dumps(self.payload).encode()

    def urlopen(request, timeout=0):
        assert request.headers["Authorization"] == "Bearer queue-secret"
        if request.method == "GET": return Response(queued)
        acknowledgements.extend(json.loads(request.data)["pathnames"])
        return Response({"ok": True, "acknowledged": len(acknowledgements)})

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    result = sales.poll_homefixed_public_queue(
        "acme", imported_by_person_id="person.owner", queue_url="https://homefixed.test/api/queue",
        queue_key="queue-secret", endpoint_id=endpoint["endpoint_id"], intake_token=endpoint["token"])
    assert result["imported"] == result["human_enquiries"] == result["acknowledged"] == 1
    assert acknowledgements == ["pending/human/web-1.json"]
    assert sales.list_opportunities("acme")[0]["source"] == "website"


def test_executable_agent_simulations_gate_hash_bound_promotion_and_call_draft(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    opportunity = enquiry(sales)["opportunity"]
    with pytest.raises(PermissionError, match="promoted_sales_playbook_required"):
        sales.prepare_outbound_call("acme", opportunity["opportunity_id"], reason="Reply",
                                    prepared_by_person_id="person.owner")
    simulated = sales.run_playbook_simulations("acme", run_by_person_id="person.owner")
    assert simulated["run"]["passed"] == simulated["run"]["required"] == 11
    assert simulated["run"]["execution_mode"] == "deterministic_governance_policy"
    with pytest.raises(ValueError, match="changed_since_approval"):
        sales.promote_playbook("acme", expected_playbook_hash="wrong", promoted_by_person_id="person.owner")
    promoted = sales.promote_playbook(
        "acme", expected_playbook_hash=simulated["playbook"]["playbook_hash"],
        promoted_by_person_id="person.owner")
    assert promoted["status"] == "promoted_for_controlled_use"
    draft = sales.prepare_outbound_call("acme", opportunity["opportunity_id"], reason="Reply to web enquiry",
        prepared_by_person_id="person.owner")
    assert draft["call_goal_contract"]["desired_outcome"] == "human_review_request"
    assert "property_location" in draft["call_goal_contract"]["required_fields"]
    assert draft["call_goal_contract_hash"].startswith("sha256:")
    assert draft["external_call_started"] is False and draft["status"] == "exact_approval_required"
    approved = sales.approve_outbound_call(
        "acme", draft["draft_id"], expected_draft_hash=draft["draft_hash"],
        approved_by_person_id="person.owner")
    assert approved["status"] == "approved_not_executed"
    with pytest.raises(PermissionError, match="live_sales_telephony_not_enabled"):
        sales.execute_outbound_call("acme", draft["draft_id"], expected_draft_hash=approved["draft_hash"],
                                    executed_by_person_id="person.owner")


def test_sales_agent_setup_is_generic_goal_driven_and_resets_promotion(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    playbook = sales.ensure_default_playbook("acme")
    configured = sales.configure_sales_agent(
        "acme", expected_playbook_hash=playbook["playbook_hash"],
        configured_by_person_id="person.owner",
        setup={"business_motion": "blended", "lead_temperature": "cold",
               "primary_goal": "site_visit_request",
               "required_fields": ["customer_name", "work_required", "full_property_address",
                                   "customer_email", "photos_or_documents_available"],
               "allowed_actions": ["collect_information", "collect_email_in_writing",
                                   "request_photos", "send_approved_terms_link",
                                   "send_approved_payment_link"],
               "intro_style": "permission_based", "close_strategy": "site_visit_request",
               "contact_sequence": {"maximum_phone_attempts": 2, "fallback_channel": "email",
                                    "questions_per_written_message": 2},
               "sales_script": "Ask permission, understand the issue, present only approved options, and close for review.",
               "evidence_route": {"mode": "approved_email_address", "destination": "photos@example.test"}})
    assert configured["status"] == "draft_simulation_required"
    assert configured["simulation"]["passed"] == 0
    assert configured["agent_setup"]["business_motion"] == "blended"
    assert configured["agent_setup"]["payment_policy"] == "approved_payment_link_only"
    assert "send_approved_payment_link" in configured["agent_setup"]["allowed_actions"]
    assert configured["agent_setup"]["contact_sequence"]["maximum_phone_attempts"] == 2
    assert configured["agent_setup"]["contact_sequence"]["automatic_send"] is False
    assert configured["external_deployment_performed"] is False


def test_call_centre_agent_mints_exact_contract_and_drives_selected_outbound_call(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    opportunity = enquiry(sales)["opportunity"]
    created = sales.create_sales_agent(
        "acme", name="New enquiry follow-up", direction="outbound",
        created_by_person_id="person.owner",
    )
    configured = sales.configure_call_centre_agent(
        "acme", created["agent_id"], expected_agent_hash=created["agent_hash"],
        configured_by_person_id="person.owner",
        setup={
            "name": "New enquiry follow-up", "direction": "outbound",
            "phone_assignment": {"number": "+441234567890", "provider": "retell",
                                 "provider_agent_id": "provider-agent-1"},
            "knowledge": {"business_name": "Acme Services",
                          "business_summary": "Approved repairs for local customers.",
                          "approved_offers": "Boiler repair and assessment.",
                          "service_areas": "Madrid", "approved_facts": "Open weekdays."},
            "objective": {"primary_outcome": "qualify_for_human_review",
                          "success_definition": "Capture the fault and agree a human callback.",
                          "close_strategy": "human_callback"},
            "capture_fields": [
                {"key": "customer_name", "label": "Customer name", "type": "text", "required": True},
                {"key": "fault", "label": "Fault", "type": "long_text", "required": True},
            ],
            "allowed_actions": ["collect_information", "request_human_callback"],
            "conversation": {"opening": "Hello, I am Acme's AI assistant.",
                             "tone": "clear", "guidance": "Ask one question at a time.",
                             "languages": ["en-GB"]},
            "routing": {"human_handoff": "Create a sales task.", "maximum_phone_attempts": 2,
                        "unanswered_action": "prepare_email"},
        },
    )
    checked = sales.test_call_centre_agent(
        "acme", created["agent_id"], run_by_person_id="person.owner")
    assert checked["agent"]["safety"]["all_passed"] is True
    minted = sales.mint_call_centre_contract(
        "acme", created["agent_id"], expected_agent_hash=checked["agent"]["agent_hash"],
        minted_by_person_id="person.owner",
    )
    assert minted["contract"]["schema_version"] == "aion.sales.agent_contract.v1"
    assert minted["contract"]["contract_hash"].startswith("sha256:")
    active = sales.set_call_centre_agent_state(
        "acme", created["agent_id"], state="active",
        expected_agent_hash=minted["agent"]["agent_hash"], changed_by_person_id="person.owner",
    )
    assert active["state"] == "active"
    draft = sales.prepare_outbound_call(
        "acme", opportunity["opportunity_id"], agent_id=created["agent_id"],
        reason="Respond to the boiler enquiry", prepared_by_person_id="person.owner",
    )
    assert draft["sales_agent_name"] == "New enquiry follow-up"
    assert draft["provider_agent_id"] == "provider-agent-1"
    assert draft["call_goal_contract"]["agent_contract_hash"] == minted["contract"]["contract_hash"]
    assert draft["call_goal_contract"]["agent_contract"]["knowledge"]["approved_offers"] == "Boiler repair and assessment."
    assert draft["call_goal_contract"]["required_fields"] == ["customer_name", "fault"]


def test_inbound_call_centre_agent_cannot_claim_active_until_number_routing_is_confirmed(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    created = sales.create_sales_agent(
        "acme", name="Inbound website line", direction="inbound",
        created_by_person_id="person.owner",
    )
    configured = sales.configure_call_centre_agent(
        "acme", created["agent_id"], expected_agent_hash=created["agent_hash"],
        configured_by_person_id="person.owner",
        setup={
            "name": "Inbound website line", "direction": "inbound",
            "phone_assignment": {"number": "+441234567891", "provider": "retell",
                                 "inbound_routing_confirmed": False},
            "knowledge": {"business_name": "Acme", "business_summary": "Local services.",
                          "approved_offers": "Approved appointments."},
            "objective": {"success_definition": "Capture the enquiry for review."},
        },
    )
    checked = sales.test_call_centre_agent(
        "acme", created["agent_id"], run_by_person_id="person.owner")
    minted = sales.mint_call_centre_contract(
        "acme", created["agent_id"], expected_agent_hash=checked["agent"]["agent_hash"],
        minted_by_person_id="person.owner",
    )
    with pytest.raises(PermissionError, match="inbound_phone_routing_confirmation_required"):
        sales.set_call_centre_agent_state(
            "acme", created["agent_id"], state="active",
            expected_agent_hash=minted["agent"]["agent_hash"], changed_by_person_id="person.owner",
        )


def test_retell_webhook_signature_verification_is_replay_bounded(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    monkeypatch.setenv("RETELL_API_KEY", "webhook-secret")
    raw = b'{"event":"call_started","call":{"call_id":"call-1","call_status":"ongoing"}}'
    timestamp = str(int(time.time() * 1000))
    digest = hmac.new(b"webhook-secret", raw + timestamp.encode(), hashlib.sha256).hexdigest()
    event = sales.record_retell_webhook("acme", raw_body=raw, signature=f"v={timestamp},d={digest}")
    assert event["call_id"] == "call-1" and event["event"] == "call_started"
    with pytest.raises(PermissionError, match="signature_invalid"):
        sales.record_retell_webhook("acme", raw_body=raw, signature="v=1,d=00")


def test_retell_call_history_is_agent_scoped_read_only_and_idempotent(monkeypatch, tmp_path):
    sales, _ = service(monkeypatch, tmp_path)
    monkeypatch.setenv("RETELL_API_KEY", "provider-secret")
    monkeypatch.setenv("RETELL_AGENT_ID", "agent-homefixed")
    calls = {"items": [{"call_id": "call-1", "agent_id": "agent-homefixed",
                         "call_status": "ended", "call_type": "phone_call"}],
             "total": 1, "has_more": False}
    detail = {"call_id": "call-1", "agent_id": "agent-homefixed", "agent_version": 3,
              "call_status": "ended", "call_type": "phone_call", "direction": "outbound",
              "duration_ms": 12000, "transcript_object": [{"role": "agent", "content": "Hello"}],
              "call_analysis": {"call_successful": True},
              "metadata": {"opportunity_id": "opportunity-1"},
              "recording_url": "https://signed.example/secret-recording"}

    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self): return json.dumps(self.payload).encode()

    requests = []
    def urlopen(request, timeout=0):
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer provider-secret"
        return Response(calls if request.method == "POST" else detail)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    first = sales.sync_retell_call_history("acme", synced_by_person_id="person.owner")
    second = sales.sync_retell_call_history("acme", synced_by_person_id="person.owner")
    assert first["imported"] == 1 and first["external_call_started"] is False
    assert second["unchanged"] == 1
    assert json.loads(requests[0].data)["filter_criteria"] == {
        "agent": [{"agent_id": "agent-homefixed"}]}
    event = sales.list_telephony_events("acme")[0]
    assert event["provider_authority"] == "authenticated_api_readback"
    assert event["opportunity_id"] == "opportunity-1"
    assert "recording_url" not in event
