from __future__ import annotations

import pytest

from backend.modules.aion_fabric.guardian import PilotGuardian
from backend.modules.aion_fabric.pilot_inbox import PilotInbox
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.aion_fabric.voice import parse_voice_intent


def _guardian(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path); owner = identities.onboard(display_name="Owner")
    inbox = PilotInbox(tmp_path, identities=identities)
    contact = inbox.save_contact(owner_persona_id=owner["persona_id"], display_name="Trusted person", whatsapp="+34600111222")
    return PilotGuardian(tmp_path, identities=identities, inbox=inbox), owner, contact


def test_spoken_help_confirmation_verified_contact_alert_and_no_dispatch_claim(tmp_path):
    guardian, owner, contact = _guardian(tmp_path)
    with pytest.raises(PermissionError):
        guardian.grant_emergency_contact(persona_id=owner["persona_id"], contact_id=contact["contact_id"], channel="whatsapp", share_location=True)
    permission = guardian.grant_emergency_contact(persona_id=owner["persona_id"], contact_id=contact["contact_id"], channel="whatsapp", share_location=True, location_permission_receipt="explicit_location_permission_1")
    assert permission["ordinary_contact_permission_implied"] is False
    incident = guardian.request_help(persona_id=owner["persona_id"], trigger="I fell over", surface="shared_tv", location={"label": "Home"})
    assert incident["status"] == "awaiting_large_confirmation" and incident["ambulance_dispatched"] is False
    guardian.confirm(incident_id=incident["incident_id"], persona_id=owner["persona_id"])
    fallback = guardian.deliver_alerts(incident_id=incident["incident_id"], persona_id=owner["persona_id"])
    assert fallback["status"] == "connectivity_fallback_required" and fallback["ambulance_dispatched"] is False

    second = guardian.request_help(persona_id=owner["persona_id"], trigger="Help", surface="private_phone", location={"label": "Home"})
    guardian.confirm(incident_id=second["incident_id"], persona_id=owner["persona_id"])
    guardian.register_alert_adapter("whatsapp", lambda payload: {"verified": bool(payload["urgent"]), "provider_alert_id": "alert_1"})
    delivered = guardian.deliver_alerts(incident_id=second["incident_id"], persona_id=owner["persona_id"])
    assert delivered["status"] == "alerts_verified" and delivered["verified_alerts"]
    response = guardian.record_response(response_token=second["response_token"], responder_name="Trusted person", message="I am calling you now")
    assert response["incident_id"] == second["incident_id"]


def test_false_positive_and_sensor_signal_never_diagnose_or_dispatch(tmp_path):
    guardian, owner, _ = _guardian(tmp_path)
    incident = guardian.request_help(persona_id=owner["persona_id"], trigger="Possible fall", surface="wearable")
    assert guardian.cancel(incident_id=incident["incident_id"], persona_id=owner["persona_id"])["status"] == "cancelled"
    signal = guardian.ingest_sensor_signal(persona_id=owner["persona_id"], source="authorized_wearable", kind="possible_fall", confidence=.82)
    assert signal["medical_diagnosis"] is False and signal["automatic_dispatch"] is False


@pytest.mark.parametrize("phrase,action", [
    ("Pilot, I fell over", "guardian_help"),
    ("Pilot, call an ambulance", "guardian_help"),
    ("Pilot, confirm emergency alert", "guardian_confirm"),
    ("Pilot, false alarm", "guardian_cancel"),
])
def test_guardian_voice_never_falls_into_planning(phrase, action):
    assert parse_voice_intent(phrase).action == action
