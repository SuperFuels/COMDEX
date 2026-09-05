from __future__ import annotations

import secrets
import json
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.household import HouseholdIdentityRegistry, UniversalNodeAuthority
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_fabric.services import ServiceExecutionHub
from backend.modules.aion_fabric import universal_service
from backend.modules.aion_fabric.universal_service import UniversalNodeService


def _identity() -> DeviceIdentity:
    return DeviceIdentity(Ed25519PrivateKey.generate())


def _pair(authority, mother, mother_id):
    started = authority.begin_handshake(mother_id=mother_id, public_key=mother.public_key_b64)
    signature = mother.sign(canonical_bytes(started["challenge"]))
    return authority.complete_handshake(
        handshake_id=started["handshake_id"],
        confirmation_code=started["confirmation_code"],
        mother_signature=signature,
        approved_by="local_owner_confirmation",
    )


def test_one_universal_node_persists_independent_mother_handshakes(tmp_path):
    node = _identity()
    authority = UniversalNodeAuthority(tmp_path, node_id="node_shared_tv", identity=node)
    mother_one, mother_two = _identity(), _identity()
    first = _pair(authority, mother_one, "node_mother_one")
    second = _pair(authority, mother_two, "node_mother_two")
    assert first["relationship_id"] != second["relationship_id"]
    assert authority.snapshot()["trusted_mothers"] == 2
    resumed = authority.begin_handshake(mother_id="node_mother_one", public_key=mother_one.public_key_b64)
    assert resumed["status"] == "recognized"
    assert resumed["confirmation_required"] is False


def test_known_mother_gets_scoped_signed_lease_and_replay_is_blocked(tmp_path):
    node, mother = _identity(), _identity()
    authority = UniversalNodeAuthority(tmp_path, node_id="node_shared_tv", identity=node)
    relationship = _pair(authority, mother, "node_mother_one")
    request = {
        "mother_id": "node_mother_one",
        "node_id": "node_shared_tv",
        "persona_id": relationship["persona_id"],
        "capabilities": ["tv.navigation.control", "tv.volume.read"],
        "nonce": secrets.token_urlsafe(20),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    signature = mother.sign(canonical_bytes(request))
    lease = authority.accept_lease_request(request, signature)
    assert lease["node_signature"]
    assert lease["capabilities"] == ["tv.navigation.control", "tv.volume.read"]
    with pytest.raises(PermissionError, match="replay"):
        authority.accept_lease_request(request, signature)


def test_service_approval_and_credentials_are_persona_isolated(tmp_path):
    household = HouseholdIdentityRegistry(tmp_path)
    first = household.ensure_local_persona(mother_id="node_mother_one", display_name="Person one")
    second = household.ensure_local_persona(mother_id="node_mother_two", display_name="Person two")
    household.bind_service(second["persona_id"], "calendar", "provider://calendar/person-two")
    hub = ServiceExecutionHub(tmp_path, household=household)
    proposal = hub.prepare(
        persona_id=second["persona_id"],
        service="calendar",
        action="create_event",
        parameters={"title": "Granada trip", "start": "2026-09-12T09:00:00+02:00", "end": "2026-09-12T10:00:00+02:00"},
    )
    with pytest.raises(PermissionError, match="bound household persona"):
        hub.decide(proposal["proposal_id"], persona_id=first["persona_id"], approved=True)
    hub.decide(proposal["proposal_id"], persona_id=second["persona_id"], approved=True)
    seen = {}
    hub.register_adapter("calendar", lambda value, credential: seen.update({"credential": credential}) or {"verified": True, "external_reference": "calendar-event-1"})
    receipt = hub.execute(proposal["proposal_id"], persona_id=second["persona_id"])
    assert receipt["verified"] is True
    assert seen["credential"] == "provider://calendar/person-two"


def test_production_private_identities_preserve_first_owner_and_isolate_later_people(tmp_path):
    household = HouseholdIdentityRegistry(tmp_path)
    legacy = household.ensure_local_persona(mother_id="node_home", display_name="Local owner")
    household.bind_service(legacy["persona_id"], "shopping", "vault://owner/shopping")
    first = household.ensure_private_identity_persona(
        private_persona_id="persona_privatealex", mother_id="node_home", display_name="Alex",
        allow_legacy_adoption=True,
    )
    second = household.ensure_private_identity_persona(
        private_persona_id="persona_privatesam", mother_id="node_home", display_name="Sam",
    )
    assert first["persona_id"] == legacy["persona_id"]
    assert first["service_bindings"] == {"shopping": "vault://owner/shopping"}
    assert second["persona_id"] != first["persona_id"]
    assert second["service_bindings"] == {}
    assert household.ensure_private_identity_persona(
        private_persona_id="persona_privatesam", mother_id="node_home", display_name="Sam",
    )["persona_id"] == second["persona_id"]


def test_service_proposals_reject_raw_payment_credentials(tmp_path):
    household = HouseholdIdentityRegistry(tmp_path)
    persona = household.ensure_local_persona(mother_id="node_mother")
    hub = ServiceExecutionHub(tmp_path, household=household)
    with pytest.raises(ValueError, match="Raw credential"):
        hub.prepare(persona_id=persona["persona_id"], service="shopping", action="checkout", parameters={"card_number": "4111111111111111"})


def test_incomplete_service_scope_cannot_be_approved(tmp_path):
    household = HouseholdIdentityRegistry(tmp_path)
    persona = household.ensure_local_persona(mother_id="node_mother")
    hub = ServiceExecutionHub(tmp_path, household=household)
    proposal = hub.prepare(persona_id=persona["persona_id"], service="calendar", action="create_event", parameters={"title": "Trip"})
    assert proposal["status"] == "needs_details"
    assert proposal["missing_fields"] == ["start", "end"]
    with pytest.raises(PermissionError, match="missing required"):
        hub.decide(proposal["proposal_id"], persona_id=persona["persona_id"], approved=True)


def test_owner_cancel_closes_only_reversible_service_work(tmp_path):
    household = HouseholdIdentityRegistry(tmp_path)
    persona = household.ensure_local_persona(mother_id="node_mother")
    hub = ServiceExecutionHub(tmp_path, household=household)
    proposal = hub.prepare(
        persona_id=persona["persona_id"],
        service="calendar",
        action="create_event",
        parameters={"title": "Granada weekend"},
    )

    result = hub.cancel_pending(persona_id=persona["persona_id"])

    assert result["cancelled"] == [proposal["proposal_id"]]
    assert result["in_flight_not_claimed_cancelled"] == []
    assert hub.snapshot()["pending_private_approval"] == 0


def test_private_details_complete_scope_before_approval(tmp_path):
    household = HouseholdIdentityRegistry(tmp_path)
    persona = household.ensure_local_persona(mother_id="node_mother")
    hub = ServiceExecutionHub(tmp_path, household=household)
    proposal = hub.prepare(
        persona_id=persona["persona_id"],
        service="calendar",
        action="create_event",
        parameters={"title": "Granada weekend"},
    )
    completed = hub.update_details(
        proposal["proposal_id"],
        persona_id=persona["persona_id"],
        details={"start": "2026-09-12T09:00:00+02:00", "end": "2026-09-12T10:00:00+02:00"},
    )
    assert completed["missing_fields"] == []
    assert completed["status"] == "awaiting_private_approval"
    assert completed["approval"]["state"] == "pending"
    approved = hub.decide(completed["proposal_id"], persona_id=persona["persona_id"], approved=True)
    assert approved["status"] == "approved_pending_adapter"


def test_private_details_cannot_be_supplied_by_another_persona(tmp_path):
    household = HouseholdIdentityRegistry(tmp_path)
    owner = household.ensure_local_persona(mother_id="node_owner")
    other = household.ensure_local_persona(mother_id="node_other")
    hub = ServiceExecutionHub(tmp_path, household=household)
    proposal = hub.prepare(persona_id=owner["persona_id"], service="email", action="send", parameters={})
    with pytest.raises(PermissionError, match="bound household persona"):
        hub.update_details(
            proposal["proposal_id"],
            persona_id=other["persona_id"],
            details={"to": "person@example.com", "subject": "Hello", "body": "Message"},
        )


def test_universal_node_handshake_is_available_over_bounded_lan_api(tmp_path, monkeypatch):
    monkeypatch.setattr(universal_service, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    authority = UniversalNodeAuthority(tmp_path, node_id="node_shared_device", identity=_identity())
    service = UniversalNodeService(authority, port=0)
    service.start()
    try:
        with urllib.request.urlopen(service.public_url + "/identity", timeout=2) as response:
            identity = json.loads(response.read())
        assert identity["node_id"] == "node_shared_device"
        assert identity["policy"]["new_mother_requires_local_confirmation"] is True
        mother = _identity()
        request = urllib.request.Request(
            service.public_url + "/handshake/begin",
            data=json.dumps({"mother_id": "node_new_mother", "public_key": mother.public_key_b64}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            started = json.loads(response.read())
        assert started["confirmation_required"] is True
        assert len(started["confirmation_code"]) == 6
    finally:
        service.stop()
