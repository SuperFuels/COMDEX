from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.modules.aion_fabric.contextual_companion import ContextualCompanion
from backend.modules.aion_fabric.voice import parse_voice_intent


def test_companion_is_opt_in_frequency_limited_and_quiet_by_default(tmp_path):
    service = ContextualCompanion(tmp_path)
    service.configure(
        persona_id="owner",
        enabled=True,
        frequency="balanced",
        quiet_start="21:00",
        quiet_end="08:00",
        interests=["space", "history"],
        humour_preferences=["dry"],
    )

    assert service.may_offer(persona_id="owner", now=datetime(2026, 8, 30, 22, 0, tzinfo=timezone.utc))["allowed"] is False
    first = service.record_offer(persona_id="owner", kind="advert_quiz", now=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc))
    second = service.record_offer(persona_id="owner", kind="discussion", now=datetime(2026, 8, 30, 12, 5, tzinfo=timezone.utc))

    assert first["allowed"] is True
    assert second == {"allowed": False, "reason": "frequency interval has not elapsed", "profile": second["profile"]}
    assert first["profile"]["dependency_controls"]["engagement_optimization"] is False


def test_loneliness_support_is_transparent_and_shared_tv_cannot_choose_persona(tmp_path):
    service = ContextualCompanion(tmp_path)
    support = service.prepare_wellbeing(statement="I am feeling lonely and need company", channel="shared_tv")

    assert support["category"] == "wellbeing_support"
    assert support["status"] == "awaiting_private_claim"
    assert "AI system rather than a person" in support["response"]
    assert support["human_or_conscious_claimed"] is False
    claimed = service.claim_support(support["support_id"], persona_id="owner")
    assert claimed["persona_id"] == "owner"
    assert claimed["statement"] == ""


def test_guardian_boundary_never_claims_dispatch_or_medical_diagnosis(tmp_path):
    support = ContextualCompanion(tmp_path).prepare_wellbeing(statement="I fell over, call an ambulance", channel="private_phone")

    assert support["category"] == "guardian_escalation_required"
    assert support["emergency_service_contacted"] is False
    assert support["medical_diagnosis_made"] is False
    assert "cannot confirm that help has been dispatched" in support["response"]


def test_trusted_call_and_cross_surface_handoff_require_private_identity_and_acceptance(tmp_path):
    service = ContextualCompanion(tmp_path)
    with pytest.raises(PermissionError):
        service.prepare_call(persona_id="owner", contact={"contact_id": "c1", "trusted": False})
    call = service.prepare_call(persona_id="owner", contact={"contact_id": "c1", "trusted": True, "display_name": "Becca"})
    handoff = service.prepare_handoff(persona_id="owner", source="shared_tv", destination="private_phone", objective="Discuss this programme", summary="The programme raised a history question.")

    assert call["call_placed"] is False
    with pytest.raises(PermissionError):
        service.accept_handoff(handoff["handoff_id"], persona_id="other", destination="private_phone")
    accepted = service.accept_handoff(handoff["handoff_id"], persona_id="owner", destination="private_phone")
    assert accepted["status"] == "accepted"
    assert accepted["raw_transcript_transferred"] is False


def test_wellbeing_and_emergency_voice_route_to_safe_companion_layers_not_planning():
    lonely = parse_voice_intent("Pilot, I am feeling lonely")
    emergency = parse_voice_intent("Pilot, I fell over, call an ambulance")

    assert lonely.action == "contextual_companion"
    assert emergency.action == "guardian_help"
    assert emergency.device == "companion"


def test_advert_activity_requires_evidence_and_remains_dismissible(tmp_path):
    service = ContextualCompanion(tmp_path)
    service.configure(persona_id="owner", enabled=True, frequency="active", quiet_start="23:00", quiet_end="06:00", interests=["science"])
    blocked = service.prepare_activity(persona_id="owner", kind="advert_quiz", programme_context={"title": "Example"}, advert_break_evidence=False, now=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc))
    activity = service.prepare_activity(persona_id="owner", kind="advert_quiz", programme_context={"title": "Example", "observed_summary": "A rocket launched."}, advert_break_evidence=True, now=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc))

    assert blocked["prepared"] is False
    assert activity["prepared"] is True
    assert activity["dismissible"] is True
    assert activity["interrupts_playback"] is False
