from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.calendar_planning import GovernedCalendarPlanning
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity


def test_conflicts_are_private_and_require_explicit_confirmation(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path); owner = identities.onboard(display_name="Owner")
    calendar = GovernedCalendarPlanning(tmp_path, identities=identities)
    start = datetime.now(timezone.utc) + timedelta(days=2); end = start + timedelta(hours=1)
    calendar.ingest_busy_event(persona_id=owner["persona_id"], provider_event_id="existing_1", start=start.isoformat(), end=end.isoformat(), title="Private appointment")
    proposal = calendar.prepare(persona_id=owner["persona_id"], action="create", title="New meeting", start=(start + timedelta(minutes=30)).isoformat(), end=(end + timedelta(minutes=30)).isoformat(), travel_minutes=15, reminder_minutes=30)
    assert proposal["status"] == "awaiting_conflict_confirmation"
    assert proposal["private_event_titles_disclosed"] is False
    assert "title" not in proposal["conflicts"][0]
    with pytest.raises(PermissionError):
        calendar.decide(proposal_id=proposal["proposal_id"], persona_id=owner["persona_id"], scope_hash=proposal["scope_hash"], approved=True)
    assert calendar.decide(proposal_id=proposal["proposal_id"], persona_id=owner["persona_id"], scope_hash=proposal["scope_hash"], approved=True, accept_conflicts=True)["status"] == "approved_pending_adapter"


def test_verified_create_receipt_and_private_availability(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path); owner = identities.onboard(display_name="Owner")
    calendar = GovernedCalendarPlanning(tmp_path, identities=identities)
    start = datetime.now(timezone.utc) + timedelta(days=3); end = start + timedelta(hours=1)
    proposal = calendar.prepare(persona_id=owner["persona_id"], action="create", title="Granada planning", start=start.isoformat(), end=end.isoformat())
    calendar.decide(proposal_id=proposal["proposal_id"], persona_id=owner["persona_id"], scope_hash=proposal["scope_hash"], approved=True)
    with pytest.raises(RuntimeError):
        calendar.execute(proposal_id=proposal["proposal_id"], persona_id=owner["persona_id"])
    calendar.register_adapter("create", lambda _proposal: {"verified": True, "provider_event_id": "google_event_1", "provider_status": "confirmed"})
    receipt = calendar.execute(proposal_id=proposal["proposal_id"], persona_id=owner["persona_id"])
    assert receipt["verified"] is True and receipt["provider_payload_retained"] is False
    available = calendar.availability(persona_id=owner["persona_id"], start=(start - timedelta(hours=1)).isoformat(), end=(end + timedelta(hours=1)).isoformat(), slot_minutes=30)
    assert available["private_event_details_disclosed"] is False


def test_calendar_scope_includes_attendees_and_retry_cannot_change_scope(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path); owner = identities.onboard(display_name="Owner")
    calendar = GovernedCalendarPlanning(tmp_path, identities=identities)
    start = datetime.now(timezone.utc) + timedelta(days=5); end = start + timedelta(hours=1)
    args = dict(
        persona_id=owner["persona_id"], action="create", title="Review", start=start.isoformat(), end=end.isoformat(),
        calendar_id="team", time_zone="Europe/Madrid", attendees=["person@example.test"],
        description="Exact agenda", notify_attendees=True, idempotency_key="calendar_retry_1",
    )
    first = calendar.prepare(**args); repeated = calendar.prepare(**args)
    assert repeated["proposal_id"] == first["proposal_id"]
    assert first["scope"]["calendar_id"] == "team" and first["scope"]["notify_attendees"] is True
    with pytest.raises(PermissionError, match="changed its exact scope"):
        calendar.prepare(**{**args, "title": "Changed"})
