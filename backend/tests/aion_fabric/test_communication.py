from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.communication import GovernedCommunication
from backend.modules.aion_fabric.pilot_inbox import PilotInbox
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity


def _setup(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    owner = identities.onboard(display_name="Owner")
    inbox = PilotInbox(tmp_path, identities=identities)
    contact = inbox.save_contact(owner_persona_id=owner["persona_id"], display_name="Becca", email="becca@example.com", whatsapp="+34600111222", sms="+34600111222", preferred_route="email")
    return identities, owner, inbox, contact


def test_exact_private_approval_and_verified_delivery_receipt(tmp_path):
    identities, owner, inbox, contact = _setup(tmp_path)
    communication = GovernedCommunication(tmp_path, identities=identities, inbox=inbox)
    draft = communication.draft(persona_id=owner["persona_id"], contact_id=contact["contact_id"], channel="email", subject="Dry cleaning", body="Please collect it tomorrow.")
    assert draft["drafted_by"] == "AION Native"
    assert draft["external_effect"] is False
    with pytest.raises(PermissionError):
        communication.approve(draft_id=draft["draft_id"], persona_id=owner["persona_id"], content_hash="changed", approved=True)
    approved = communication.approve(draft_id=draft["draft_id"], persona_id=owner["persona_id"], content_hash=draft["content_hash"], approved=True)
    assert approved["status"] == "approved_pending_adapter"
    with pytest.raises(RuntimeError):
        communication.execute(draft_id=draft["draft_id"], persona_id=owner["persona_id"])
    communication.register_adapter("email", lambda _draft: {"verified": True, "provider_message_id": "msg_verified_1", "provider_thread_id": "thread_1"})
    receipt = communication.execute(draft_id=draft["draft_id"], persona_id=owner["persona_id"])
    assert receipt["verified"] is True
    assert receipt["provider_response_retained"] is False


def test_received_provenance_task_conversion_and_no_reply_follow_up(tmp_path):
    identities, owner, inbox, contact = _setup(tmp_path)
    communication = GovernedCommunication(tmp_path, identities=identities, inbox=inbox)
    received = communication.ingest_received(persona_id=owner["persona_id"], provider_message_id="provider_1", sender_name="Becca", received_at=datetime.now(timezone.utc).isoformat(), body="Please buy milk on the way home", source="gmail.messages.get")
    assert received["source_provenance_present"] is True
    assert received["raw_body_retained"] is False
    task = communication.convert_received(message_id=received["message_id"], persona_id=owner["persona_id"], target="task")
    assert "buy milk" in task["title"].lower()
    draft = communication.draft(persona_id=owner["persona_id"], contact_id=contact["contact_id"], channel="email", subject="Milk", body="I will collect it")
    communication.approve(draft_id=draft["draft_id"], persona_id=owner["persona_id"], content_hash=draft["content_hash"], approved=True)
    communication.register_adapter("email", lambda _draft: {"verified": True, "provider_message_id": "msg_2"})
    communication.execute(draft_id=draft["draft_id"], persona_id=owner["persona_id"])
    follow = communication.schedule_no_reply_follow_up(draft_id=draft["draft_id"], persona_id=owner["persona_id"], due_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
    assert follow["condition"] == "no_verified_reply"


def test_child_external_communication_requires_guardian_then_sender(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    adult = identities.onboard(display_name="Parent")
    child = identities.onboard(display_name="Child", role="child", guardian_persona_id=adult["persona_id"], age_band="8-9")
    inbox = PilotInbox(tmp_path, identities=identities)
    contact = inbox.save_contact(owner_persona_id=child["persona_id"], display_name="Gran", email="gran@example.com")
    communication = GovernedCommunication(tmp_path, identities=identities, inbox=inbox)
    draft = communication.draft(persona_id=child["persona_id"], contact_id=contact["contact_id"], channel="email", subject="Hello", body="Can we call tomorrow?")
    assert draft["status"] == "guardian_approval_required"
    with pytest.raises(PermissionError):
        communication.approve(draft_id=draft["draft_id"], persona_id=child["persona_id"], content_hash=draft["content_hash"], approved=True)
    assert communication.guardian_decide(draft_id=draft["draft_id"], guardian_persona_id=adult["persona_id"], approved=True)["status"] == "awaiting_private_approval"


def test_provider_acceptance_is_not_delivery_and_authenticated_event_can_advance_state(tmp_path):
    identities, owner, inbox, contact = _setup(tmp_path)
    communication = GovernedCommunication(tmp_path, identities=identities, inbox=inbox)
    draft = communication.draft(persona_id=owner["persona_id"], contact_id=contact["contact_id"], channel="email", subject="Status", body="Please confirm.")
    communication.approve(draft_id=draft["draft_id"], persona_id=owner["persona_id"], content_hash=draft["content_hash"], approved=True)
    communication.register_adapter("email", lambda _draft: {"verified": True, "provider_message_id": "msg_state_1"})
    receipt = communication.execute(draft_id=draft["draft_id"], persona_id=owner["persona_id"])
    assert receipt["provider_state"] == "provider_accepted"
    assert receipt["human_delivery_verified"] is False
    delivered = communication.confirm_delivery(persona_id=owner["persona_id"], provider_message_id="msg_state_1", evidence_id="provider-event-123")
    assert delivered["provider_state"] == "delivered"
    assert delivered["human_delivery_verified"] is False


def test_personal_sms_uses_independent_contact_route_and_exact_approval(tmp_path):
    identities, owner, inbox, contact = _setup(tmp_path)
    communication = GovernedCommunication(tmp_path, identities=identities, inbox=inbox)
    draft = communication.draft(
        persona_id=owner["persona_id"], contact_id=contact["contact_id"],
        channel="sms", body="Please collect the dry cleaning.",
    )
    assert draft["recipient"] == "+34600111222"
    assert draft["status"] == "awaiting_private_approval"
    communication.approve(
        draft_id=draft["draft_id"], persona_id=owner["persona_id"],
        content_hash=draft["content_hash"], approved=True,
    )
    communication.register_adapter("sms", lambda item: {
        "verified": True, "provider_message_id": "SM" + "d" * 32,
        "provider_state": "provider_accepted",
    })
    receipt = communication.execute(draft_id=draft["draft_id"], persona_id=owner["persona_id"])
    assert receipt["provider_state"] == "provider_accepted"
    assert receipt["human_delivery_verified"] is False


def test_exact_attachment_scope_reply_proposals_invitation_and_contact_protection(tmp_path):
    identities, owner, inbox, contact = _setup(tmp_path)
    communication = GovernedCommunication(tmp_path, identities=identities, inbox=inbox)
    attachment = {"attachment_id": "attachment_1", "name": "request.pdf", "media_type": "application/pdf", "size": 1200, "sha256": "a" * 64}
    draft = communication.draft(
        persona_id=owner["persona_id"], contact_id=contact["contact_id"], channel="email",
        subject="Request", body="Please review the attached scope.", attachments=[attachment],
    )
    assert draft["attachments"] == [attachment]
    invitation = communication.create_invitation(draft_id=draft["draft_id"], persona_id=owner["persona_id"], public_base_url="https://pilot.example")
    token = invitation["url"].rsplit("/", 1)[-1]
    public = communication.inspect_invitation(token)
    assert public["request_summary"] == "Please review the attached scope."
    assert "persona_id" not in public and public["unrelated_household_data_included"] is False
    recipient = identities.onboard(display_name="Recipient")
    claimed = communication.claim_invitation(token=token, recipient_persona_id=recipient["persona_id"])
    assert claimed["status"] == "claimed" and claimed["unrelated_sender_data_included"] is False

    received = communication.ingest_received(
        persona_id=owner["persona_id"], provider_message_id="reply_1", sender_name="Becca",
        received_at=datetime.now(timezone.utc).isoformat(), body="Please remind me tomorrow", source="provider.webhook",
    )
    reminder = communication.convert_received(message_id=received["message_id"], persona_id=owner["persona_id"], target="reminder")
    assert reminder["status"] == "needs_private_time"
    report = communication.report_contact(persona_id=owner["persona_id"], contact_id=contact["contact_id"], category="spam")
    assert report["provider_report_claimed"] is False
    communication.block_contact(persona_id=owner["persona_id"], contact_id=contact["contact_id"])
    with pytest.raises(PermissionError, match="blocked"):
        communication.draft(persona_id=owner["persona_id"], contact_id=contact["contact_id"], channel="email", subject="Blocked", body="No send")
