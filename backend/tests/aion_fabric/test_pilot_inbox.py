from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.pilot_inbox import PilotInbox
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.aion_fabric.provider_adapters import GoogleTasksAdapter


def _people(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    first = identities.onboard(display_name="First")
    second = identities.onboard(display_name="Second")
    return identities, first["persona_id"], second["persona_id"]


def test_private_lists_block_cross_person_modification_and_delegation_requires_acceptance(tmp_path):
    identities, first, second = _people(tmp_path)
    inbox = PilotInbox(tmp_path, identities=identities)
    private_list = inbox.create_list(owner_persona_id=first, name="My tasks")
    with pytest.raises(PermissionError):
        inbox.create_task(requester_persona_id=second, owner_persona_id=first, title="Intrude", list_id=private_list["list_id"])
    delegated = inbox.create_task(requester_persona_id=first, owner_persona_id=first, assignee_persona_id=second, title="Pick up dry cleaning")
    assert delegated["status"] == "awaiting_recipient_acceptance"
    with pytest.raises(ValueError):
        inbox.complete(task_id=delegated["task_id"], actor_persona_id=second)
    accepted = inbox.respond_to_delegation(task_id=delegated["task_id"], recipient_persona_id=second, accept=True)
    assert accepted["status"] == "open"
    assert inbox.complete(task_id=delegated["task_id"], actor_persona_id=second)["status"] == "completed"


def test_messages_and_external_handoffs_are_distinct(tmp_path):
    identities, first, second = _people(tmp_path)
    inbox = PilotInbox(tmp_path, identities=identities)
    direct = inbox.send_message(sender_persona_id=first, recipient_persona_id=second, body="Can you collect this?")
    assert direct["status"] == "delivered_to_pilot_inbox"
    external = inbox.prepare_external_message(sender_persona_id=first, channel="whatsapp", recipient_reference="contact_ref", body="Can you collect this?")
    assert external["status"] == "prepared_not_sent"
    assert external["private_approval_required"] is True


def test_private_contacts_prepare_external_tasks_without_sending(tmp_path):
    identities, first, _ = _people(tmp_path)
    inbox = PilotInbox(tmp_path, identities=identities)
    contact = inbox.save_contact(
        owner_persona_id=first, display_name="Becca", email="becca@example.com",
        whatsapp="+34600111222", preferred_route="whatsapp",
    )
    assert inbox.find_contacts(owner_persona_id=first, display_name="becca")[0]["contact_id"] == contact["contact_id"]
    assert inbox.resolve_spoken_contacts(owner_persona_id=first, display_name="back")[0]["contact_id"] == contact["contact_id"]
    assert inbox.resolve_spoken_contacts(owner_persona_id=first, display_name="backup")[0]["contact_id"] == contact["contact_id"]
    proposal = inbox.prepare_external_task(
        sender_persona_id=first, contact_id=contact["contact_id"], title="Collect the dry cleaning",
    )
    assert proposal["status"] == "prepared_not_sent"
    assert proposal["channel"] == "whatsapp"
    approved = inbox.approve_external_delivery(proposal_id=proposal["proposal_id"], persona_id=first)
    assert approved["status"] == "approved_pending_adapter"
    stream = inbox.stream(persona_id=first)
    assert stream["external_deliveries"][0]["status"] == "approved_pending_adapter"
    assert stream["external_messages_sent_without_approval"] is False


def test_location_reminders_and_route_stops_require_permission_and_acceptance(tmp_path):
    identities, first, _ = _people(tmp_path)
    inbox = PilotInbox(tmp_path, identities=identities)
    task = inbox.create_task(requester_persona_id=first, owner_persona_id=first, title="Buy milk")
    with pytest.raises(PermissionError):
        inbox.add_reminder(persona_id=first, task_id=task["task_id"], trigger="arrival", location_label="Supermarket")
    reminder = inbox.add_reminder(persona_id=first, task_id=task["task_id"], trigger="arrival", location_label="Supermarket", location_permission_id="permission_local_1")
    assert reminder["raw_location_history_retained"] is False
    suggestion = inbox.suggest_route_stop(persona_id=first, task_id=task["task_id"], accepted_route_id="route_1", reason="Shop is on route")
    assert suggestion["status"] == "suggested_not_added"
    assert inbox.accept_route_stop(suggestion_id=suggestion["suggestion_id"], persona_id=first)["status"] == "accepted_pending_authorized_car_adapter"


def test_google_tasks_adapter_requires_verified_provider_response(tmp_path):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, _limit): return b'{"id":"task_123","title":"Buy milk","status":"needsAction","selfLink":"https://tasks.googleapis.com/task_123"}'

    seen = {}
    def urlopen(request, timeout=0):
        seen["url"] = request.full_url
        return Response()

    adapter = GoogleTasksAdapter(lambda _reference: "x" * 30, urlopen=urlopen)
    receipt = adapter({"title": "Buy milk", "notes": "On the way home"}, "provider://google/tasks-owner")
    assert receipt["verified"] is True
    assert seen["url"].endswith("/tasks/v1/lists/%40default/tasks")
