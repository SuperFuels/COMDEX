from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.calendar_planning import GovernedCalendarPlanning
from backend.modules.aion_fabric.communication import GovernedCommunication
from backend.modules.aion_fabric.google_oauth import PersonaGoogleOAuth
from backend.modules.aion_fabric.guardian import PilotGuardian
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.intelligence import PilotIntelligencePolicy
from backend.modules.aion_fabric.pilot_inbox import PilotInbox
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.aion_fabric.private_saves import PrivateProgrammeSaves
from backend.modules.aion_fabric.saved_followthrough import SavedItemFollowThrough
from backend.modules.aion_fabric.services import ServiceExecutionHub
from backend.modules.pilot_unified.pairing import MobilePairingAuthority
from backend.modules.pilot_unified.personal import PersonalPilotProjection


def _paired_personal(root):
    identities = ProductionPrivateIdentity(root)
    adult = identities.onboard(display_name="Alex", role="adult")
    child = identities.onboard(
        display_name="Sam", role="child", guardian_persona_id=adult["persona_id"], age_band="6-9",
    )
    identities.onboard(display_name="Other adult", role="adult")
    inbox = PilotInbox(root, identities=identities)
    inbox.create_list(owner_persona_id=adult["persona_id"], name="Home")
    inbox.create_task(
        requester_persona_id=adult["persona_id"], owner_persona_id=adult["persona_id"], title="Buy milk",
    )
    inbox.add_reminder(
        persona_id=adult["persona_id"], task_id=inbox.stream(persona_id=adult["persona_id"])["tasks"][0]["task_id"],
        trigger="time", at="2030-01-01T09:00:00+00:00",
    )
    inbox.save_contact(owner_persona_id=adult["persona_id"], display_name="Taylor", email="taylor@example.test")
    mother = IdentityStore(root / "mother").load_or_create()
    pairing = MobilePairingAuthority(
        root, mother_id="mother_home", mother_identity=mother, endpoint="https://home.test:8770",
        ca_sha256="ab" * 32, identity_registry=identities,
    )
    phone = IdentityStore(root / "phone").load_or_create()
    challenge = pairing.begin_pairing(
        persona_id=adult["persona_id"], device_label="Alex phone", phone_public_key=phone.public_key_b64,
        requested_scopes=("inbox.read", "task.create", "calendar.read", "calendar.propose", "calendar.approve", "calendar.execute", "contacts.read", "contacts.write", "contacts.resolve", "communication.read", "communication.draft", "communication.approve", "communication.execute", "communication.convert", "communication.followup", "communication.call", "services.read", "services.propose", "services.approve", "services.execute", "library.read", "library.write", "library.continue", "devices.read", "devices.discover", "devices.control", "tv.observe", "tv.control", "experiences.read", "experiences.control", "memory.read", "memory.write", "memory.export", "guardian.read", "guardian.configure", "guardian.alert", "intelligence.read", "intelligence.use", "intelligence.configure"),
    )
    signed = {key: challenge["phone_challenge"][key] for key in (
        "schema_version", "challenge_id", "mother_id", "mother_fingerprint", "mother_descriptor_hash",
        "persona_id", "device_id", "device_label", "requested_scopes", "nonce", "issued_at", "expires_at",
    )}
    paired = pairing.complete_pairing(
        challenge_id=signed["challenge_id"],
        confirmation_code=challenge["local_confirmation"]["confirmation_code"],
        phone_signature=phone.sign(canonical_bytes(signed)),
    )
    communication = GovernedCommunication(root, identities=identities, inbox=inbox)
    service_hub = ServiceExecutionHub(root)
    private_saves = PrivateProgrammeSaves(root)
    saved_followthrough = SavedItemFollowThrough(root)
    class Researcher:
        @staticmethod
        def search(query, mode="general"):
            return {
                "answer": f"Evidence for {query[:40]}", "provider": "test_public_evidence",
                "display_label": "AION + live public evidence",
                "items": [
                    {"title": "Independent evidence", "reason": "Relevant", "detail": "Current comparison", "url": "https://example.test/evidence"},
                    {"title": "Private endpoint", "reason": "Must not cross to the phone", "detail": "Internal", "url": "https://127.0.0.1/private"},
                ],
            }
    projection = PersonalPilotProjection(
        identities=identities, inbox=inbox, pairing_authority=pairing,
        calendar=GovernedCalendarPlanning(root, identities=identities),
        google_oauth=PersonaGoogleOAuth(root, identities=identities),
        communication=communication,
        service_hub=service_hub,
        private_saves=private_saves,
        saved_followthrough=saved_followthrough,
        researcher=Researcher(),
        device_snapshot_provider=lambda: {
            "nodes": [{
                "profile": {"node_id": "node_tv", "name": "Living TV", "device_class": "television", "platform": "webOS", "transports": ["wifi"], "controls": ["volume"] , "metadata": {"webos_host": "192.168.1.9"}},
                "role": "gateway", "enrollment": "enrolled", "last_seen_at": "2030-01-01T00:00:00+00:00", "public_key": "secret", "is_primary_tv": True,
                "capabilities": [{"capability_id": "companion.webos.media.control", "kind": "control", "description": "TV media", "risk": "medium", "requires_approval": True, "schema": {"secret": True}}],
            }],
            "rooms": [{"node_id": "node_tv", "device_name": "Living TV", "room_name": "Living room", "endpoint": "192.168.1.9", "default": True}],
            "tv_connection": {"status": "connected", "message": "TV connected and ready."},
            "active_shared_identity": identities.snapshot().get("active_shared_identity"),
            "climate": {"connected": True, "learned_presets": [{"preset": "cool_22", "sha256": "hidden"}], "last_active_preset": "cool_22"},
        },
        device_discovery=lambda: {"safety": {"control_requests_sent": 0}},
        device_command_executor=lambda command, arguments: {
            "accepted": True, "spoken_response": f"Executed {command}",
            "receipt": {"action": command, "verified": command != "ir_send"},
            "infrared_climate": {"preset": arguments.get("preset"), "transport_delivered": command == "ir_send"},
        },
        experience_snapshot_provider=lambda persona_id: {
            "learning": {"session": {"profile_id": "explorer_a", "prompt": "apple", "phase": "question", "choices": [{"index": 0, "text": "manzana"}]}, "profiles": {"explorer_a": {"stars": 2}}},
            "games": {"latest_session": {"persona_id": persona_id, "state": "provider_surface_prepared", "playing_verified": False}, "controllers": [], "shortcuts": []},
            "entertainment": {"personalization": {"watchlists": [], "private_history": []}, "execution": {"latest": None, "count": 0}},
        },
        experience_command_executor=lambda persona_id, operation, arguments: {
            "accepted": True, "state": "prepared_not_playing" if operation == "games_open" else "updated",
            "spoken_response": f"Completed {operation} for {persona_id}",
            "learning": {"session": {"phase": "feedback", "was_correct": True}} if operation == "learning_answer" else None,
            "games": {"latest_session": {"persona_id": persona_id, "playing_verified": False}} if operation == "games_open" else None,
            "playing_verified": False,
        },
        tv_presentation_executor=lambda persona_id, request: {
            "presented": request.get("operation") == "present",
            "dismissed": request.get("operation") == "dismiss",
            "persona_id": persona_id,
            "content_id": request.get("content_id"),
        },
        guardian=PilotGuardian(root, identities=identities, inbox=inbox),
        intelligence_status_provider=PilotIntelligencePolicy(root).status,
        intelligence_command_executor=lambda persona_id, operation, arguments: (
            PilotIntelligencePolicy(root).set_mode(str(arguments.get("mode") or "native"), gemini_grounding_enabled=False)
            if operation == "configure" else {
                "accepted": True, "spoken_response": f"AION handled {arguments.get('query')}",
                "intent": {"action": "aion_native"}, "display_label": "AION Local",
            }
        ),
    )
    return adult, child, phone, paired, projection


def test_mobile_service_actions_are_persona_bound_exact_and_verified(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    assert projection.service_hub is not None
    prepare = {
        "persona_id": adult["persona_id"], "service": "shopping", "action": "prepare_purchase",
        "parameters": {"item": "extendable ladders", "quantity": 1, "requirements": "uneven ground"},
        "idempotency_key": "service_prepare_1",
    }
    proposal = projection.prepare_service_action(
        prepare, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(prepare)),
    )
    repeated = projection.prepare_service_action(
        prepare, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(prepare)),
    )
    assert repeated["proposal_id"] == proposal["proposal_id"]
    assert proposal["persona_id"] == adult["persona_id"]
    assert proposal["service_persona_id_exposed"] is False
    assert proposal["status"] == "awaiting_private_approval"

    altered_decision = {
        "persona_id": adult["persona_id"], "proposal_id": proposal["proposal_id"],
        "parameters_hash": "changed", "approved": True, "idempotency_key": "service_decide_bad",
    }
    with pytest.raises(PermissionError, match="details changed"):
        projection.decide_service_action(
            altered_decision, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(altered_decision)),
        )

    decision = {**altered_decision, "parameters_hash": proposal["parameters_hash"], "idempotency_key": "service_decide_1"}
    approved = projection.decide_service_action(
        decision, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(decision)),
    )
    assert approved["status"] == "approved_pending_adapter"
    service_persona = projection.service_hub.household.ensure_private_identity_persona(
        private_persona_id=adult["persona_id"], mother_id=projection.pairing.mother_id,
        display_name=adult["display_name"],
    )
    projection.service_hub.household.bind_service(service_persona["persona_id"], "shopping", "vault://alex/shopping")
    projection.service_hub.register_adapter("shopping", lambda item, _credential: {
        "verified": True, "external_reference": f"basket:{item['parameters']['item']}",
    })
    execute = {
        "persona_id": adult["persona_id"], "proposal_id": proposal["proposal_id"],
        "parameters_hash": proposal["parameters_hash"], "idempotency_key": "service_execute_1",
    }
    receipt = projection.execute_service_action(
        execute, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(execute)),
    )
    assert receipt["verified"] is True
    assert receipt["raw_provider_response_retained"] is False

    read = {"purpose": "read_private_service_actions", "persona_id": adult["persona_id"], "idempotency_key": "service_read_1"}
    snapshot = projection.service_snapshot(
        read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(read)),
    )
    assert snapshot["bound_services"] == ["shopping"]
    assert snapshot["raw_credentials_exposed"] is False
    assert snapshot["receipts"][0]["persona_id"] == adult["persona_id"]


def test_mobile_service_actions_reject_payment_secrets(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    request = {
        "persona_id": adult["persona_id"], "service": "shopping", "action": "prepare_purchase",
        "parameters": {"item": "ladders", "quantity": 1, "card_number": "not-allowed"},
        "idempotency_key": "service_secret_1",
    }
    with pytest.raises(ValueError, match="Raw credential field"):
        projection.prepare_service_action(
            request, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(request)),
        )


def test_mobile_library_claim_research_followthrough_and_delete_are_private(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    assert projection.private_saves is not None
    pending = projection.private_saves.prepare(
        category="product", request="save these ladders",
        live_context={"context_hash": "context_1", "recent_transcripts": ["extendable ladders"]},
        screen_understanding={"products": {"candidate_text": "Professional ladders", "prices": ["EUR 120"], "confidence": 0.9}},
        provider_metadata={},
    )
    read = {"purpose": "read_private_library", "persona_id": adult["persona_id"], "idempotency_key": "library_read_0001"}
    before = projection.library_snapshot(
        read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(read)),
    )
    assert before["pending"]["save_id"] == pending["save_id"]
    assert before["external_effect_inherited"] is False

    claim = {"persona_id": adult["persona_id"], "save_id": pending["save_id"], "idempotency_key": "library_claim_0001"}
    saved = projection.claim_library_item(
        claim, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(claim)),
    )
    assert saved["persona_id"] == adult["persona_id"] and saved["status"] == "saved"

    follow = {"persona_id": adult["persona_id"], "save_id": pending["save_id"], "action": "research", "idempotency_key": "library_continue_0001"}
    researched = projection.continue_library_item(
        follow, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(follow)),
    )
    repeated = projection.continue_library_item(
        follow, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(follow)),
    )
    assert repeated["followthrough_id"] == researched["followthrough_id"]
    assert researched["items"][0]["url"] == "https://example.test/evidence"
    assert researched["items"][1]["url"] == ""
    assert researched["external_effect"] is False

    action = {**follow, "action": "shopping", "idempotency_key": "library_continue_0002"}
    shopping = projection.continue_library_item(
        action, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(action)),
    )
    assert shopping["private_approval_created"] is True
    assert shopping["service_proposal"]["status"] == "awaiting_private_approval"
    assert shopping["service_proposal"]["external_effect"] is False

    deletion = {"persona_id": adult["persona_id"], "save_id": pending["save_id"], "idempotency_key": "library_delete_0001"}
    first_delete = projection.delete_library_item(
        deletion, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(deletion)),
    )
    repeat_delete = projection.delete_library_item(
        deletion, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(deletion)),
    )
    assert first_delete["deleted_at"] == repeat_delete["deleted_at"]


def test_mobile_device_mesh_is_sanitized_and_tv_control_requires_exclusive_session(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    read = {"purpose": "read_private_device_mesh", "persona_id": adult["persona_id"], "idempotency_key": "devices_read_0001"}
    snapshot = projection.device_mesh_snapshot(
        read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(read)),
    )
    assert snapshot["nodes"][0]["name"] == "Living TV"
    assert snapshot["nodes"][0]["capabilities"][0]["capability_id"] == "companion.webos.media.control"
    assert "public_key" not in snapshot["nodes"][0]
    assert "metadata" not in snapshot["nodes"][0]
    assert "endpoint" not in snapshot["rooms"][0]
    assert snapshot["climate"]["learned_presets"] == ["cool_22"]
    assert snapshot["public_keys_or_network_addresses_exposed"] is False

    invalid_key = {**read, "idempotency_key": "short"}
    with pytest.raises(ValueError, match="device idempotency key"):
        projection.device_mesh_snapshot(
            invalid_key, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(invalid_key)),
        )

    control = {"persona_id": adult["persona_id"], "command": "volume_up", "arguments": {}, "idempotency_key": "tv_control_0001"}
    with pytest.raises(PermissionError, match="expired|reactivate"):
        projection.control_shared_tv(
            control, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(control)),
        )

    possession_nonce = "shared_screen_nonce_0001"
    possession = {"purpose": "activate_shared_screen", "persona_id": adult["persona_id"], "device_id": paired["certificate"]["device_id"], "nonce": possession_nonce}
    acquire = {
        "persona_id": adult["persona_id"], "operation": "acquire", "possession_nonce": possession_nonce,
        "possession_signature": phone.sign(canonical_bytes(possession)), "idempotency_key": "tv_session_acquire_0001",
    }
    active = projection.change_shared_tv_session(
        acquire, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(acquire)),
    )
    assert active["state"] == "you"
    presence = {
        "purpose": "confirm_local_phone_presence", "persona_id": adult["persona_id"],
        "idempotency_key": "tv_presence_0001",
    }
    with pytest.raises(PermissionError, match="trusted home network"):
        projection.confirm_shared_tv_presence(
            presence, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(presence)), trusted_local_address=False,
        )
    confirmed = projection.confirm_shared_tv_presence(
        presence, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(presence)), trusted_local_address=True,
    )
    assert confirmed["state"] == "you"
    assert confirmed["passive_presence_counts_as_activity"] is False
    result = projection.control_shared_tv(
        control, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(control)),
    )
    assert result["accepted"] is True
    assert result["button_delivery_alone_is_success"] is False

    presentation = {
        "persona_id": adult["persona_id"], "operation": "present",
        "kind": "briefing", "content_id": "personal/today",
        "idempotency_key": "tv_presentation_0001",
    }
    shown = projection.control_shared_tv_presentation(
        presentation, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(presentation)),
    )
    assert shown["result"]["presented"] is True
    assert shown["result"]["persona_id"] == adult["persona_id"]
    assert shown["private_content_persisted_on_tv"] is False

    dismiss = {
        "persona_id": adult["persona_id"], "operation": "dismiss",
        "idempotency_key": "tv_presentation_0002",
    }
    closed = projection.control_shared_tv_presentation(
        dismiss, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(dismiss)),
    )
    assert closed["result"]["dismissed"] is True

    iot = {"persona_id": adult["persona_id"], "command": "ir_send", "preset": "cool_22", "idempotency_key": "iot_control_0001"}
    climate = projection.control_iot_device(
        iot, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(iot)),
    )
    assert climate["transport_delivered"] is True
    assert climate["device_state_verified"] is False


def test_mobile_learning_games_and_entertainment_are_persona_bound(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    read = {
        "purpose": "read_private_learning_games_entertainment",
        "persona_id": adult["persona_id"], "idempotency_key": "experiences_read_0001",
    }
    snapshot = projection.experience_snapshot(
        read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(read)),
    )
    assert snapshot["learning"]["session"]["prompt"] == "apple"
    assert snapshot["games"]["latest_session"]["persona_id"] == adult["persona_id"]
    assert snapshot["claims"]["provider_open_is_playing"] is False
    assert snapshot["claims"]["paid_ai_required_for_learning"] is False

    answer = {
        "persona_id": adult["persona_id"], "operation": "learning_answer",
        "arguments": {"choice_index": 0}, "idempotency_key": "experience_answer_0001",
    }
    result = projection.control_experience(
        answer, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(answer)),
    )
    assert result["learning"]["session"]["was_correct"] is True

    games = {
        "persona_id": adult["persona_id"], "operation": "games_open",
        "arguments": {}, "idempotency_key": "experience_games_0001",
    }
    with pytest.raises(PermissionError, match="expired|reactivate"):
        projection.control_experience(
            games, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(games)),
        )

    possession_nonce = "experience_tv_nonce_0001"
    possession = {"purpose": "activate_shared_screen", "persona_id": adult["persona_id"], "device_id": paired["certificate"]["device_id"], "nonce": possession_nonce}
    acquire = {
        "persona_id": adult["persona_id"], "operation": "acquire", "possession_nonce": possession_nonce,
        "possession_signature": phone.sign(canonical_bytes(possession)), "idempotency_key": "experience_tv_acquire_0001",
    }
    projection.change_shared_tv_session(
        acquire, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(acquire)),
    )
    opened = projection.control_experience(
        games, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(games)),
    )
    assert opened["state"] == "prepared_not_playing"
    assert opened["playing_verified"] is False


def test_mobile_memory_is_inspectable_correctable_exportable_and_persona_bound(tmp_path):
    adult, child, phone, paired, projection = _paired_personal(tmp_path)
    other = next(item for item in projection.identities.snapshot()["profiles"] if item["display_name"] == "Other adult")
    create = {
        "persona_id": adult["persona_id"], "target_persona_id": adult["persona_id"],
        "kind": "preference", "summary": "Prefers quiet mornings", "scope": "private",
        "idempotency_key": "memory_create_0001",
    }
    first = projection.create_memory(
        create, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(create)),
    )
    replay = projection.create_memory(
        create, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(create)),
    )
    assert replay["memory_id"] == first["memory_id"]

    correction = {
        "persona_id": adult["persona_id"], "target_persona_id": adult["persona_id"],
        "memory_id": first["memory_id"], "summary": "Prefers quiet evenings",
        "scope": "household_shared", "idempotency_key": "memory_update_0001",
    }
    corrected = projection.update_memory(
        correction, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(correction)),
    )
    assert corrected["scope"] == "household_shared" and corrected["corrected_at"]

    child_create = {
        "persona_id": adult["persona_id"], "target_persona_id": child["persona_id"],
        "kind": "learning", "summary": "Practising Spanish nouns", "scope": "private",
        "idempotency_key": "memory_child_create_0001",
    }
    projection.create_memory(
        child_create, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(child_create)),
    )
    child_read = {
        "purpose": "inspect_private_memory", "persona_id": adult["persona_id"],
        "target_persona_id": child["persona_id"], "idempotency_key": "memory_child_read_0001",
    }
    assert projection.memory_snapshot(
        child_read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(child_read)),
    )["guardian_managed"] is True

    other_read = {**child_read, "target_persona_id": other["persona_id"], "idempotency_key": "memory_other_read_0001"}
    with pytest.raises(PermissionError, match="another person's memory"):
        projection.memory_snapshot(
            other_read, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(other_read)),
        )

    export = {
        "persona_id": adult["persona_id"], "target_persona_id": adult["persona_id"],
        "idempotency_key": "memory_export_0001",
    }
    exported = projection.export_memory(
        export, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(export)),
    )
    assert exported["export"]["memories"][0]["summary"] == "Prefers quiet evenings"
    assert "recovery_code_hash" not in str(exported["export"])
    assert all("public_key" not in device for device in exported["export"]["devices"])

    delete = {
        "persona_id": adult["persona_id"], "target_persona_id": adult["persona_id"],
        "memory_id": first["memory_id"], "confirm_irrecoverable": True,
        "idempotency_key": "memory_delete_0001",
    }
    deleted = projection.delete_memory(
        delete, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(delete)),
    )
    assert deleted == projection.delete_memory(
        delete, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(delete)),
    )


def test_mobile_guardian_uses_separate_permission_confirmation_and_honest_delivery(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    contact = next(item for item in projection.inbox._read()["contacts"] if item["display_name"] == "Taylor")
    configure = {
        "persona_id": adult["persona_id"], "contact_id": contact["contact_id"],
        "channel": "email", "share_location": False, "allow_interruption": True,
        "idempotency_key": "guardian_configure_0001",
    }
    permission = projection.configure_guardian_contact(
        configure, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(configure)),
    )
    assert permission["ordinary_contact_permission_implied"] is False

    request = {
        "persona_id": adult["persona_id"], "operation": "request",
        "trigger": "Explicit phone help request", "idempotency_key": "guardian_request_0001",
    }
    incident = projection.control_guardian_incident(
        request, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(request)),
    )["result"]
    assert incident["status"] == "awaiting_large_confirmation"
    assert incident["ambulance_dispatched"] is False

    confirm = {
        "persona_id": adult["persona_id"], "operation": "confirm",
        "incident_id": incident["incident_id"], "idempotency_key": "guardian_confirm_0001",
    }
    delivered = projection.control_guardian_incident(
        confirm, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(confirm)),
    )
    assert delivered["fallback_required"] is True
    assert delivered["delivery_verified"] is False
    assert delivered["ambulance_dispatched"] is False
    assert projection.control_guardian_incident(
        confirm, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(confirm)),
    ) == delivered

    snapshot = {
        "purpose": "read_private_guardian", "persona_id": adult["persona_id"],
        "idempotency_key": "guardian_read_0001",
    }
    state = projection.guardian_snapshot(
        snapshot, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(snapshot)),
    )
    assert state["claims"]["automatic_dispatch"] is False
    assert state["latest_incident"]["status"] == "connectivity_fallback_required"


def test_mobile_composer_uses_aion_native_by_default_and_premium_is_explicit(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    read = {
        "purpose": "read_private_intelligence_route", "persona_id": adult["persona_id"],
        "idempotency_key": "intelligence_read_0001",
    }
    status = projection.intelligence_snapshot(
        read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(read)),
    )
    assert status["mode"] == "native" and status["native_core_requires_paid_provider"] is False
    assert "settings_path" not in status and status["secrets_projected_to_phone"] is False

    ask = {
        "persona_id": adult["persona_id"], "query": "add milk to my tasks",
        "idempotency_key": "intelligence_ask_0001",
    }
    result = projection.use_intelligence(
        ask, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(ask)),
    )
    assert result["display_label"] == "AION Local" and result["accepted"] is True

    configure = {
        "persona_id": adult["persona_id"], "mode": "gemini",
        "gemini_grounding_enabled": False, "idempotency_key": "intelligence_configure_0001",
    }
    changed = projection.configure_intelligence(
        configure, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(configure)),
    )
    assert changed["mode"] == "gemini" and changed["provider_keys_projected_to_phone"] is False


def test_personal_projection_reuses_authorities_and_filters_other_adults(tmp_path):
    adult, child, phone, paired, projection = _paired_personal(tmp_path)
    request = {"purpose": "read_personal_pilot", "persona_id": adult["persona_id"]}
    result = projection.snapshot(
        request, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(request)),
    )
    assert result["person"]["display_name"] == "Alex"
    assert [item["persona_id"] for item in result["guardian_controlled_children"]] == [child["persona_id"]]
    assert [item["title"] for item in result["tasks"]] == ["Buy milk"]
    assert result["summary"] == {"open_tasks": 1, "waiting_for_acceptance": 0, "due_reminders": 0, "contacts": 1}
    assert "Other adult" not in str(result)
    assert result["authority"]["other_adult_private_data_exposed"] is False


def test_personal_projection_requires_exact_phone_signature_and_persona(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    request = {"purpose": "read_personal_pilot", "persona_id": adult["persona_id"]}
    altered = {**request, "persona_id": "persona_someone_else"}
    with pytest.raises(PermissionError, match="different private identity"):
        projection.snapshot(
            altered, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(altered)),
        )
    with pytest.raises(PermissionError, match="did not sign"):
        projection.snapshot(
            request, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes({**request, "purpose": "other"})),
        )


def test_mobile_reminders_are_idempotent_manageable_and_location_permission_bound(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    task_id = projection.inbox.stream(persona_id=adult["persona_id"])["tasks"][0]["task_id"]
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    create = {
        "persona_id": adult["persona_id"], "task_id": task_id, "trigger": "time", "at": future,
        "location_label": "", "repetition": "weekly", "location_permission_id": "",
        "idempotency_key": "reminder_create_mobile_1",
    }
    first = projection.create_reminder(
        create, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(create)),
    )
    repeated = projection.create_reminder(
        create, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(create)),
    )
    assert repeated["reminder_id"] == first["reminder_id"]
    assert first["repetition"] == "weekly"

    snooze = {
        "persona_id": adult["persona_id"], "reminder_id": first["reminder_id"], "operation": "snooze",
        "until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "idempotency_key": "reminder_snooze_mobile_1",
    }
    updated = projection.transition_reminder(
        snooze, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(snooze)),
    )
    assert updated["status"] == "snoozed"

    complete = {
        "persona_id": adult["persona_id"], "reminder_id": first["reminder_id"], "operation": "complete",
        "until": "", "idempotency_key": "reminder_complete_mobile_1",
    }
    completed = projection.transition_reminder(
        complete, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(complete)),
    )
    assert completed["status"] == "completed"
    reminders = projection.inbox.stream(persona_id=adult["persona_id"])["reminders"]
    following = next(item for item in reminders if item["reminder_id"] == completed["next_reminder_id"])
    assert following["status"] == "scheduled"
    assert following["recurring_from"] == first["reminder_id"]

    location = {
        "persona_id": adult["persona_id"], "task_id": task_id, "trigger": "arrival", "at": "",
        "location_label": "Supermarket", "repetition": "none", "location_permission_id": "missing",
        "idempotency_key": "reminder_location_mobile_1",
    }
    with pytest.raises(PermissionError, match="has not granted"):
        projection.create_reminder(
            location, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(location)),
        )
    consent = projection.identities.grant_consent(
        persona_id=adult["persona_id"], service="pilot_location", scopes=["reminder.location"],
        device_id=paired["certificate"]["device_id"],
    )
    location["location_permission_id"] = consent["consent_id"]
    location["idempotency_key"] = "reminder_location_mobile_2"
    placed = projection.create_reminder(
        location, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(location)),
    )
    assert placed["trigger"] == "arrival"
    assert placed["raw_location_history_retained"] is False

    wrong_person = {**snooze, "persona_id": "persona_other", "idempotency_key": "reminder_wrong_person_1"}
    with pytest.raises(PermissionError, match="different private identity"):
        projection.transition_reminder(
            wrong_person, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(wrong_person)),
        )


def test_mobile_calendar_is_private_exact_idempotent_and_provider_verified(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    assert projection.calendar is not None
    start = datetime.now(timezone.utc) + timedelta(days=4)
    end = start + timedelta(hours=1)
    projection.calendar.ingest_busy_event(
        persona_id=adult["persona_id"], provider_event_id="private_existing",
        start=start.isoformat(), end=end.isoformat(), title="Private appointment",
    )
    read = {"purpose": "read_private_calendar", "persona_id": adult["persona_id"]}
    snapshot = projection.calendar_snapshot(
        read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(read)),
    )
    assert snapshot["provider"]["credentials_on_phone"] is False
    assert snapshot["provider"]["credentials_on_shared_tv"] is False

    availability_request = {
        "persona_id": adult["persona_id"], "start": (start - timedelta(hours=1)).isoformat(),
        "end": (end + timedelta(hours=1)).isoformat(), "slot_minutes": 30,
        "idempotency_key": "availability_1",
    }
    availability = projection.calendar_availability(
        availability_request, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(availability_request)),
    )
    assert availability["private_event_details_disclosed"] is False
    assert "Private appointment" not in str(availability)

    request = {
        "persona_id": adult["persona_id"], "action": "create", "title": "Granada planning",
        "start": (start + timedelta(minutes=30)).isoformat(), "end": (end + timedelta(minutes=30)).isoformat(),
        "provider_event_id": "", "location": "Granada", "travel_minutes": 20, "reminder_minutes": 30,
        "calendar_id": "primary", "time_zone": "Europe/Madrid", "attendees": ["guest@example.test"],
        "description": "Review the itinerary", "notify_attendees": True, "idempotency_key": "calendar_prepare_1",
    }
    proposal = projection.prepare_calendar(
        request, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(request)),
    )
    repeated = projection.prepare_calendar(
        request, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(request)),
    )
    assert repeated["proposal_id"] == proposal["proposal_id"]
    assert proposal["scope"]["attendees"] == ["guest@example.test"]
    assert proposal["conflict_count"] == 1 and "Private appointment" not in str(proposal["conflicts"])

    decision = {
        "persona_id": adult["persona_id"], "proposal_id": proposal["proposal_id"],
        "scope_hash": proposal["scope_hash"], "approved": True, "accept_conflicts": True,
        "idempotency_key": "calendar_decide_1",
    }
    approved = projection.decide_calendar(
        decision, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(decision)),
    )
    assert approved["status"] == "approved_pending_adapter"
    projection.calendar.register_adapter("create", lambda _proposal: {
        "verified": True, "provider_event_id": "google_mobile_event_1", "provider_status": "confirmed",
    })
    execution = {
        "persona_id": adult["persona_id"], "proposal_id": proposal["proposal_id"],
        "scope_hash": proposal["scope_hash"], "idempotency_key": "calendar_execute_1",
    }
    receipt = projection.execute_calendar(
        execution, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(execution)),
    )
    assert receipt["verified"] is True and receipt["provider_payload_retained"] is False
    assert projection.execute_calendar(
        execution, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(execution)),
    )["receipt_id"] == receipt["receipt_id"]

    altered = {**execution, "scope_hash": "0" * 64}
    with pytest.raises(PermissionError, match="scope changed"):
        projection.execute_calendar(
            altered, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(altered)),
        )


def test_mobile_contacts_are_persona_private_resolvable_and_soft_removed(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    read = {"persona_id": adult["persona_id"], "query": "", "idempotency_key": "contacts_read_1"}
    snapshot = projection.contacts_snapshot(
        read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(read)),
    )
    assert snapshot["count"] == 1 and snapshot["contacts"][0]["email"] == "taylor@example.test"
    assert snapshot["other_person_contacts_exposed"] is False

    save = {
        "persona_id": adult["persona_id"], "contact_id": "", "display_name": "Becca",
        "email": "becca@example.test", "whatsapp": "+34600111222", "pilot_persona_id": "",
        "pilot_mother_id": "", "preferred_route": "whatsapp", "idempotency_key": "contact_save_1",
    }
    first = projection.save_contact(
        save, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(save)),
    )
    repeated = projection.save_contact(
        save, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(save)),
    )
    assert repeated["contact_id"] == first["contact_id"]

    resolve = {
        "persona_id": adult["persona_id"], "display_name": "backup", "requested_route": "",
        "idempotency_key": "contact_resolve_1",
    }
    resolved = projection.resolve_contact(
        resolve, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(resolve)),
    )
    assert resolved["status"] == "resolved" and resolved["match"] == "unique_phonetic"
    assert resolved["selected_route"] == "whatsapp" and resolved["external_effect"] is False

    wrong_route = {**resolve, "requested_route": "pilot", "idempotency_key": "contact_resolve_2"}
    with pytest.raises(ValueError, match="does not have"):
        projection.resolve_contact(
            wrong_route, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(wrong_route)),
        )

    remove = {"persona_id": adult["persona_id"], "contact_id": first["contact_id"], "idempotency_key": "contact_remove_1"}
    removed = projection.remove_contact(
        remove, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(remove)),
    )
    assert removed["status"] == "removed"
    assert projection.remove_contact(
        remove, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(remove)),
    )["already_applied"] is True
    assert projection.contacts_snapshot(
        read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(read)),
    )["count"] == 1

    wrong_person = {**read, "persona_id": "persona_other"}
    with pytest.raises(PermissionError, match="different private identity"):
        projection.contacts_snapshot(
            wrong_person, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(wrong_person)),
        )


def test_mobile_communication_is_exact_retry_safe_and_provider_verified(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    assert projection.communication is not None
    contact = projection.inbox.search_contacts(owner_persona_id=adult["persona_id"], query="Taylor")[0]
    read = {
        "purpose": "read_private_communication", "persona_id": adult["persona_id"],
        "idempotency_key": "communication_read_1",
    }
    snapshot = projection.communication_snapshot(
        read, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(read)),
    )
    assert snapshot["providers"]["credentials_on_phone"] is False
    assert snapshot["other_person_communications_exposed"] is False

    prepare = {
        "persona_id": adult["persona_id"], "contact_id": contact["contact_id"],
        "channel": "email", "subject": "Dry cleaning", "body": "Please collect it tomorrow.",
        "reply_to_message_id": "", "idempotency_key": "communication_prepare_1",
    }
    draft = projection.prepare_communication(
        prepare, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(prepare)),
    )
    repeated = projection.prepare_communication(
        prepare, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(prepare)),
    )
    assert repeated["draft_id"] == draft["draft_id"]
    assert draft["external_effect"] is False and draft["drafted_by"] == "AION Native"

    altered_prepare = {**prepare, "body": "Changed content"}
    with pytest.raises(PermissionError, match="reused for different content"):
        projection.prepare_communication(
            altered_prepare, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(altered_prepare)),
        )

    decide = {
        "persona_id": adult["persona_id"], "draft_id": draft["draft_id"],
        "content_hash": draft["content_hash"], "approved": True,
        "idempotency_key": "communication_decide_1",
    }
    approved = projection.decide_communication(
        decide, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(decide)),
    )
    assert approved["status"] == "approved_pending_adapter"
    execution = {
        "persona_id": adult["persona_id"], "draft_id": draft["draft_id"],
        "content_hash": draft["content_hash"], "idempotency_key": "communication_execute_1",
    }
    with pytest.raises(RuntimeError, match="sending account"):
        projection.execute_communication(
            execution, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(execution)),
        )
    projection.communication.register_adapter("email", lambda _draft: {
        "verified": True, "provider_message_id": "provider_message_1", "provider_thread_id": "thread_1",
    })
    receipt = projection.execute_communication(
        execution, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(execution)),
    )
    assert receipt["verified"] is True and receipt["provider_response_retained"] is False
    assert projection.execute_communication(
        execution, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(execution)),
    )["receipt_id"] == receipt["receipt_id"]

    follow_up = {
        "persona_id": adult["persona_id"], "draft_id": draft["draft_id"],
        "due_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "idempotency_key": "communication_followup_1",
    }
    scheduled = projection.schedule_communication_follow_up(
        follow_up, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(follow_up)),
    )
    assert scheduled["condition"] == "no_verified_reply"
    assert projection.schedule_communication_follow_up(
        follow_up, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(follow_up)),
    )["follow_up_id"] == scheduled["follow_up_id"]

    changed = {**execution, "content_hash": "0" * 64}
    with pytest.raises(PermissionError, match="changed"):
        projection.execute_communication(
            changed, certificate=paired["certificate"], lease=paired["lease"],
            phone_signature=phone.sign(canonical_bytes(changed)),
        )


def test_mobile_received_summary_conversion_and_call_preparation(tmp_path):
    adult, _child, phone, paired, projection = _paired_personal(tmp_path)
    assert projection.communication is not None
    received = projection.communication.ingest_received(
        persona_id=adult["persona_id"], provider_message_id="incoming_1", sender_name="Taylor",
        received_at=datetime.now(timezone.utc).isoformat(), body="Please buy milk on the way home",
        source="gmail.messages.get",
    )
    convert = {
        "persona_id": adult["persona_id"], "message_id": received["message_id"],
        "target": "task", "idempotency_key": "communication_convert_1",
    }
    task = projection.convert_received_communication(
        convert, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(convert)),
    )
    assert "buy milk" in task["title"].lower()
    assert projection.convert_received_communication(
        convert, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(convert)),
    )["task_id"] == task["task_id"]
    assert received["raw_body_retained"] is False and received["source_provenance_present"] is True

    becca = projection.inbox.save_contact(
        owner_persona_id=adult["persona_id"], display_name="Becca", whatsapp="+34600111222",
    )
    call = {
        "persona_id": adult["persona_id"], "contact_id": becca["contact_id"],
        "idempotency_key": "communication_call_1",
    }
    prepared = projection.prepare_communication_call(
        call, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(call)),
    )
    assert prepared["status"] == "prepared_not_placed" and prepared["explicit_phone_tap_required"] is True
    assert projection.prepare_communication_call(
        call, certificate=paired["certificate"], lease=paired["lease"],
        phone_signature=phone.sign(canonical_bytes(call)),
    )["call_id"] == prepared["call_id"]
