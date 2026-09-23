from __future__ import annotations

import re
from typing import Any, Callable

from backend.modules.aion_fabric.calendar_planning import GovernedCalendarPlanning
from backend.modules.aion_fabric.communication import GovernedCommunication
from backend.modules.aion_fabric.google_oauth import PersonaGoogleOAuth
from backend.modules.aion_fabric.provider_adapters import PersonaBoundGmailCommunicationAdapter
from backend.modules.aion_fabric.guardian import PilotGuardian
from backend.modules.aion_fabric.pilot_inbox import PilotInbox
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.aion_fabric.private_saves import PrivateProgrammeSaves
from backend.modules.aion_fabric.research import AionTVResearch
from backend.modules.aion_fabric.saved_followthrough import SavedItemFollowThrough
from backend.modules.aion_fabric.services import ServiceExecutionHub

from .pairing import MobilePairingAuthority


class PersonalPilotProjection:
    """Persona-scoped mobile view over existing Personal Pilot authorities."""

    def __init__(
        self,
        *,
        identities: ProductionPrivateIdentity,
        inbox: PilotInbox,
        pairing_authority: MobilePairingAuthority,
        calendar: GovernedCalendarPlanning | None = None,
        google_oauth: PersonaGoogleOAuth | None = None,
        google_access_token_resolver: Callable[[str], str] | None = None,
        communication: GovernedCommunication | None = None,
        service_hub: ServiceExecutionHub | None = None,
        private_saves: PrivateProgrammeSaves | None = None,
        saved_followthrough: SavedItemFollowThrough | None = None,
        researcher: AionTVResearch | None = None,
        device_snapshot_provider: Callable[[], dict[str, Any]] | None = None,
        device_discovery: Callable[[], dict[str, Any]] | None = None,
        device_command_executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        experience_snapshot_provider: Callable[[str], dict[str, Any]] | None = None,
        experience_command_executor: Callable[[str, str, dict[str, Any]], dict[str, Any]] | None = None,
        guardian: PilotGuardian | None = None,
        intelligence_status_provider: Callable[[], dict[str, Any]] | None = None,
        intelligence_command_executor: Callable[[str, str, dict[str, Any]], dict[str, Any]] | None = None,
        tv_presentation_executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        dashboard_action_executor: Callable[[str, str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.identities = identities
        self.inbox = inbox
        self.pairing = pairing_authority
        self.calendar = calendar
        self.google_oauth = google_oauth
        self.communication = communication
        if self.communication is not None and self.google_oauth is not None and google_access_token_resolver is not None:
            self.communication.register_adapter(
                "email",
                PersonaBoundGmailCommunicationAdapter(self.google_oauth, google_access_token_resolver),
            )
        self.service_hub = service_hub
        self.private_saves = private_saves
        self.saved_followthrough = saved_followthrough
        self.researcher = researcher
        self.device_snapshot_provider = device_snapshot_provider
        self.device_discovery = device_discovery
        self.device_command_executor = device_command_executor
        self.experience_snapshot_provider = experience_snapshot_provider
        self.experience_command_executor = experience_command_executor
        self.guardian = guardian
        self.intelligence_status_provider = intelligence_status_provider
        self.intelligence_command_executor = intelligence_command_executor
        self.tv_presentation_executor = tv_presentation_executor
        self.dashboard_action_executor = dashboard_action_executor

    def _calendar_authority(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
        scope: str,
    ) -> str:
        if self.calendar is None:
            raise RuntimeError("Private calendar planning is not active on this mother")
        authority = self.pairing.validate_signed_request(
            certificate=certificate, lease=lease, required_scope=scope,
            request=request, phone_signature=phone_signature,
        )
        persona_id = str(authority["persona_id"])
        if str(request.get("persona_id") or "") != persona_id:
            raise PermissionError("This phone cannot use a different private identity")
        return persona_id

    def snapshot(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        authority = self.pairing.validate_signed_request(
            certificate=certificate,
            lease=lease,
            required_scope="inbox.read",
            request=request,
            phone_signature=phone_signature,
        )
        persona_id = str(authority["persona_id"])
        if request != {"purpose": "read_personal_pilot", "persona_id": persona_id}:
            raise ValueError("The Personal Pilot request is malformed")
        identity = self.identities.snapshot(viewer_persona_id=persona_id)
        profiles = list(identity.get("profiles") or [])
        person = next(
            (dict(item) for item in profiles if item.get("persona_id") == persona_id and item.get("status") == "active"),
            None,
        )
        if person is None:
            raise PermissionError("This phone's private identity is no longer active")
        children = [
            dict(item) for item in profiles
            if item.get("status") == "active" and item.get("role") == "child"
            and item.get("guardian_persona_id") == persona_id
        ]
        location_permissions = [
            {key: item.get(key) for key in ("consent_id", "service", "scopes", "device_id", "status", "granted_at")}
            for item in identity.get("viewer_consents", [])
            if item.get("status") == "granted" and item.get("service") == "pilot_location"
            and "reminder.location" in set(item.get("scopes") or [])
            and item.get("device_id") == authority["device_id"]
        ]
        personal = self.inbox.stream(persona_id=persona_id)
        tasks = list(personal.get("tasks") or [])
        reminders = list(personal.get("reminders") or [])
        return {
            "schema_version": "pilot.personal-mobile.v1",
            "persona_id": persona_id,
            "person": person,
            "guardian_controlled_children": children,
            "location_reminder_permissions": location_permissions,
            "lists": list(personal.get("lists") or []),
            "tasks": tasks,
            "reminders": reminders,
            "contacts": [{
                "contact_id": item.get("contact_id"), "display_name": item.get("display_name"),
                "preferred_route": item.get("preferred_route"),
                "available_routes": [route for route, value in (("pilot", item.get("pilot_persona_id")), ("whatsapp", item.get("whatsapp")), ("email", item.get("email"))) if value],
                "private_route_details_exposed": False,
            } for item in list(personal.get("contacts") or [])],
            "summary": {
                "open_tasks": len([item for item in tasks if item.get("status") in {"open", "accepted", "snoozed"}]),
                "waiting_for_acceptance": int(personal.get("unaccepted_tasks") or 0),
                "due_reminders": len([item for item in reminders if item.get("status") == "due"]),
                "contacts": len(personal.get("contacts") or []),
            },
            "shared_dashboard": self._shared_dashboard_state(persona_id),
            "authority": {
                "source": "existing_personal_pilot",
                "phone_device_id": authority["device_id"],
                "other_adult_private_data_exposed": False,
                "shared_tv_authority_granted": "tv.control" in set(authority.get("scopes") or []),
            },
        }

    def _shared_dashboard_state(self, persona_id: str) -> dict[str, Any]:
        """Return only the caller's shared-dashboard session state."""
        active = dict(self.identities.snapshot().get("active_shared_identity") or {})
        state = "locked"
        if active:
            state = "you" if active.get("persona_id") == persona_id else "another_person"
        return {
            "state": state,
            "display_name": str(active.get("display_name") or "")[:100] if state == "you" else "",
            "expires_at": active.get("expires_at") if state == "you" else None,
            "presence_expires_at": active.get("presence_expires_at") if state == "you" else None,
            "exclusive": True,
        }

    def create_reminder(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        authority = self.pairing.validate_signed_request(
            certificate=certificate, lease=lease, required_scope="task.create",
            request=request, phone_signature=phone_signature,
        )
        persona_id = str(authority["persona_id"])
        trigger = str(request.get("trigger") or "")
        location_permission_id = str(request.get("location_permission_id") or "") or None
        if trigger in {"arrival", "departure", "journey"}:
            identity = self.identities.snapshot(viewer_persona_id=persona_id)
            permission = next((
                item for item in identity.get("viewer_consents", [])
                if item.get("consent_id") == location_permission_id
                and item.get("status") == "granted"
                and item.get("service") == "pilot_location"
                and "reminder.location" in set(item.get("scopes") or [])
                and item.get("device_id") == authority["device_id"]
            ), None)
            if permission is None:
                raise PermissionError("This phone has not granted location reminders")
        return self.inbox.create_mobile_reminder(
            persona_id=persona_id,
            task_id=str(request.get("task_id") or ""),
            trigger=trigger,
            at=str(request.get("at") or "") or None,
            location_label=str(request.get("location_label") or ""),
            repetition=str(request.get("repetition") or "none"),
            location_permission_id=location_permission_id,
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def transition_reminder(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        authority = self.pairing.validate_signed_request(
            certificate=certificate, lease=lease, required_scope="task.create",
            request=request, phone_signature=phone_signature,
        )
        return self.inbox.transition_mobile_reminder(
            persona_id=str(authority["persona_id"]),
            reminder_id=str(request.get("reminder_id") or ""),
            operation=str(request.get("operation") or ""),
            until=str(request.get("until") or "") or None,
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def calendar_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._calendar_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="calendar.read",
        )
        if request != {"purpose": "read_private_calendar", "persona_id": persona_id}:
            raise ValueError("The private calendar request is malformed")
        result = self.calendar.snapshot(persona_id=persona_id) if self.calendar else {}
        account = self.google_oauth.snapshot(persona_id=persona_id) if self.google_oauth else {"bindings": [], "raw_tokens_exposed": False}
        bindings = [item for item in list(account.get("bindings") or []) if "calendar" in set(item.get("services") or []) and item.get("status") == "connected"]
        return {
            "schema_version": "pilot.personal-calendar-mobile.v1",
            "persona_id": persona_id,
            **result,
            "provider": {
                "google_calendar_connected": bool(bindings),
                "bindings": bindings,
                "credentials_on_phone": False,
                "credentials_on_shared_tv": False,
            },
        }

    def calendar_availability(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._calendar_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="calendar.read",
        )
        assert self.calendar is not None
        return self.calendar.availability(
            persona_id=persona_id, start=str(request.get("start") or ""),
            end=str(request.get("end") or ""), slot_minutes=int(request.get("slot_minutes") or 30),
        )

    def prepare_calendar(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._calendar_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="calendar.propose",
        )
        assert self.calendar is not None
        return self.calendar.prepare(
            persona_id=persona_id, action=str(request.get("action") or ""),
            title=str(request.get("title") or ""), start=str(request.get("start") or ""),
            end=str(request.get("end") or ""), provider_event_id=str(request.get("provider_event_id") or ""),
            location=str(request.get("location") or ""), travel_minutes=int(request.get("travel_minutes") or 0),
            reminder_minutes=int(request.get("reminder_minutes") or 0), calendar_id=str(request.get("calendar_id") or "primary"),
            time_zone=str(request.get("time_zone") or "Europe/Madrid"), attendees=list(request.get("attendees") or []),
            description=str(request.get("description") or ""), notify_attendees=bool(request.get("notify_attendees")),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def decide_calendar(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._calendar_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="calendar.approve",
        )
        assert self.calendar is not None
        return self.calendar.decide(
            proposal_id=str(request.get("proposal_id") or ""), persona_id=persona_id,
            scope_hash=str(request.get("scope_hash") or ""), approved=bool(request.get("approved")),
            accept_conflicts=bool(request.get("accept_conflicts")),
        )

    def execute_calendar(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._calendar_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="calendar.execute",
        )
        allowed = {"persona_id", "proposal_id", "scope_hash", "idempotency_key"}
        if set(request) != allowed:
            raise ValueError("The calendar execution request is malformed")
        assert self.calendar is not None
        proposal = next((item for item in self.calendar.snapshot(persona_id=persona_id)["proposals"] if item.get("proposal_id") == request.get("proposal_id")), None)
        if proposal is None or proposal.get("scope_hash") != request.get("scope_hash"):
            raise PermissionError("The calendar scope changed; review it again")
        return self.calendar.execute(proposal_id=str(request["proposal_id"]), persona_id=persona_id)

    def _contact_persona(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str, scope: str,
    ) -> str:
        authority = self.pairing.validate_signed_request(
            certificate=certificate, lease=lease, required_scope=scope,
            request=request, phone_signature=phone_signature,
        )
        persona_id = str(authority["persona_id"])
        if str(request.get("persona_id") or "") != persona_id:
            raise PermissionError("This phone cannot use a different private identity")
        return persona_id

    @staticmethod
    def _contact_projection(item: dict[str, Any], *, expose_routes: bool) -> dict[str, Any]:
        routes = [route for route, value in (
            ("pilot", item.get("pilot_persona_id")), ("whatsapp", item.get("whatsapp")), ("email", item.get("email")),
        ) if value]
        result = {
            "contact_id": item.get("contact_id"), "display_name": item.get("display_name"),
            "preferred_route": item.get("preferred_route"), "available_routes": routes,
            "private_route_details_exposed": expose_routes,
        }
        if expose_routes:
            result.update({
                "email": item.get("email") or "", "whatsapp": item.get("whatsapp") or "",
                "pilot_persona_id": item.get("pilot_persona_id") or "",
                "pilot_mother_id": item.get("pilot_mother_id") or "",
            })
        return result

    def contacts_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._contact_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="contacts.read",
        )
        query = str(request.get("query") or "")
        contacts = self.inbox.search_contacts(owner_persona_id=persona_id, query=query)
        return {
            "schema_version": "pilot.personal-contacts-mobile.v1", "persona_id": persona_id,
            "query": query, "contacts": [self._contact_projection(item, expose_routes=True) for item in contacts],
            "count": len(contacts), "other_person_contacts_exposed": False,
            "shared_tv_contact_details_exposed": False,
        }

    def save_contact(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._contact_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="contacts.write",
        )
        record = self.inbox.save_mobile_contact(
            owner_persona_id=persona_id, contact_id=str(request.get("contact_id") or ""),
            display_name=str(request.get("display_name") or ""), email=str(request.get("email") or ""),
            whatsapp=str(request.get("whatsapp") or ""), pilot_persona_id=str(request.get("pilot_persona_id") or ""),
            pilot_mother_id=str(request.get("pilot_mother_id") or ""), preferred_route=str(request.get("preferred_route") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )
        return self._contact_projection(record, expose_routes=True)

    def remove_contact(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._contact_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="contacts.write",
        )
        return self.inbox.remove_mobile_contact(
            owner_persona_id=persona_id, contact_id=str(request.get("contact_id") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def resolve_contact(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._contact_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="contacts.resolve",
        )
        spoken_name = str(request.get("display_name") or "")
        requested_route = str(request.get("requested_route") or "")
        exact = self.inbox.find_contacts(owner_persona_id=persona_id, display_name=spoken_name)
        matches = exact or self.inbox.resolve_spoken_contacts(owner_persona_id=persona_id, display_name=spoken_name)
        if not matches:
            return {"status": "not_found", "query": spoken_name, "candidates": [], "external_effect": False}
        if len(matches) != 1:
            return {
                "status": "ambiguous", "query": spoken_name,
                "candidates": [self._contact_projection(item, expose_routes=False) for item in matches[:10]],
                "external_effect": False,
            }
        contact = matches[0]
        projected = self._contact_projection(contact, expose_routes=True)
        route = requested_route or str(contact.get("preferred_route") or "")
        if route not in projected["available_routes"]:
            raise ValueError("That contact does not have the requested route")
        return {
            "status": "resolved", "match": "exact" if exact else "unique_phonetic",
            "contact": projected, "selected_route": route,
            "recipient_reference": str(contact.get("pilot_persona_id") if route == "pilot" else contact.get(route) or ""),
            "recipient_mother_id": str(contact.get("pilot_mother_id") or "") if route == "pilot" else "",
            "external_effect": False, "private_confirmation_required_before_use": True,
        }

    def _communication_persona(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str, scope: str,
    ) -> str:
        if self.communication is None:
            raise RuntimeError("Private communication is not active on this mother")
        authority = self.pairing.validate_signed_request(
            certificate=certificate, lease=lease, required_scope=scope,
            request=request, phone_signature=phone_signature,
        )
        persona_id = str(authority["persona_id"])
        if str(request.get("persona_id") or "") != persona_id:
            raise PermissionError("This phone cannot use a different private identity")
        return persona_id

    def communication_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.read",
        )
        if set(request) != {"purpose", "persona_id", "idempotency_key"} or request.get("purpose") != "read_private_communication":
            raise ValueError("The private communication request is malformed")
        assert self.communication is not None
        result = self.communication.snapshot(persona_id=persona_id)
        oauth = self.google_oauth.snapshot(persona_id=persona_id) if self.google_oauth else {"bindings": []}
        email_connected = any(
            item.get("status") == "connected" and "email_send" in set(item.get("services") or [])
            for item in list(oauth.get("bindings") or [])
        )
        return {
            "schema_version": "pilot.personal-communication-mobile.v1",
            "persona_id": persona_id, **result,
            "providers": {
                "email_account_authorized": email_connected,
                "email_adapter_active": "email" in self.communication.adapters,
                "email_send_connected": email_connected and "email" in self.communication.adapters,
                "whatsapp_send_connected": "whatsapp" in self.communication.adapters,
                "pilot_send_connected": "pilot" in self.communication.adapters,
                "credentials_on_phone": False, "credentials_on_shared_tv": False,
            },
            "other_person_communications_exposed": False,
        }

    def prepare_communication(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.draft",
        )
        assert self.communication is not None
        return self.communication.draft_mobile(
            persona_id=persona_id, contact_id=str(request.get("contact_id") or ""),
            channel=str(request.get("channel") or ""), subject=str(request.get("subject") or ""),
            body=str(request.get("body") or ""), reply_to_message_id=str(request.get("reply_to_message_id") or ""),
            attachments=list(request.get("attachments") or []),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def decide_communication(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.approve",
        )
        assert self.communication is not None
        return self.communication.decide_mobile(
            draft_id=str(request.get("draft_id") or ""), persona_id=persona_id,
            content_hash=str(request.get("content_hash") or ""), approved=bool(request.get("approved")),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def execute_communication(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.execute",
        )
        allowed = {"persona_id", "draft_id", "content_hash", "idempotency_key"}
        if set(request) != allowed:
            raise ValueError("The communication execution request is malformed")
        assert self.communication is not None
        draft = next((item for item in self.communication.snapshot(persona_id=persona_id)["drafts"] if item.get("draft_id") == request.get("draft_id")), None)
        if draft is None or draft.get("content_hash") != request.get("content_hash"):
            raise PermissionError("The recipient or message changed; review it again")
        return self.communication.execute(draft_id=str(request["draft_id"]), persona_id=persona_id)

    def convert_received_communication(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.convert",
        )
        assert self.communication is not None
        return self.communication.convert_received_mobile(
            message_id=str(request.get("message_id") or ""), persona_id=persona_id,
            target=str(request.get("target") or ""), idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def create_communication_invitation(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.invite",
        )
        assert self.communication is not None
        return self.communication.create_invitation(
            draft_id=str(request.get("draft_id") or ""), persona_id=persona_id,
            public_base_url=str(request.get("public_base_url") or ""),
        )

    def claim_communication_invitation(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.invite.claim",
        )
        assert self.communication is not None
        return self.communication.claim_invitation(
            token=str(request.get("token") or ""), recipient_persona_id=persona_id,
        )

    def protect_communication_contact(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.protect",
        )
        assert self.communication is not None
        operation = str(request.get("operation") or "")
        if operation == "block":
            return self.communication.block_contact(persona_id=persona_id, contact_id=str(request.get("contact_id") or ""))
        if operation == "report":
            return self.communication.report_contact(
                persona_id=persona_id, contact_id=str(request.get("contact_id") or ""),
                category=str(request.get("category") or ""),
            )
        raise ValueError("Unsupported communication protection action")

    def schedule_communication_follow_up(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.followup",
        )
        assert self.communication is not None
        return self.communication.schedule_mobile_follow_up(
            draft_id=str(request.get("draft_id") or ""), persona_id=persona_id,
            due_at=str(request.get("due_at") or ""), idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def prepare_communication_call(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._communication_persona(
            request, certificate=certificate, lease=lease,
            phone_signature=phone_signature, scope="communication.call",
        )
        assert self.communication is not None
        return self.communication.prepare_mobile_call(
            persona_id=persona_id, contact_id=str(request.get("contact_id") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def _service_persona(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str, scope: str,
    ) -> tuple[str, str, dict[str, Any]]:
        if self.service_hub is None:
            raise RuntimeError("Private service actions are not active on this mother")
        idempotency_key = str(request.get("idempotency_key") or "")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{12,160}", idempotency_key):
            raise ValueError("A valid service idempotency key is required")
        authority = self.pairing.validate_signed_request(
            certificate=certificate, lease=lease, required_scope=scope,
            request=request, phone_signature=phone_signature,
        )
        private_persona_id = str(authority["persona_id"])
        if str(request.get("persona_id") or "") != private_persona_id:
            raise PermissionError("This phone cannot use a different private identity")
        identity = self.identities.snapshot(viewer_persona_id=private_persona_id)
        profile = next((dict(item) for item in identity.get("profiles", []) if item.get("persona_id") == private_persona_id), None)
        if profile is None or profile.get("status") != "active":
            raise PermissionError("This private identity is no longer active")
        active_adults = [item for item in identity.get("profiles", []) if item.get("status") == "active" and item.get("role") == "adult"]
        service_persona = self.service_hub.household.ensure_private_identity_persona(
            private_persona_id=private_persona_id,
            mother_id=self.pairing.mother_id,
            display_name=str(profile.get("display_name") or "Local owner"),
            allow_legacy_adoption=profile.get("role") == "adult" and len(active_adults) == 1,
        )
        return private_persona_id, str(service_persona["persona_id"]), profile

    @staticmethod
    def _service_projection(value: dict[str, Any], *, private_persona_id: str) -> dict[str, Any]:
        projected = dict(value)
        projected["persona_id"] = private_persona_id
        projected["service_persona_id_exposed"] = False
        projected["credential_reference_exposed"] = False
        return projected

    def service_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        private_id, service_id, profile = self._service_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="services.read",
        )
        if request.get("purpose") != "read_private_service_actions":
            raise ValueError("The private service request is malformed")
        assert self.service_hub is not None
        snapshot = self.service_hub.snapshot_for_persona(service_id)
        return {
            **snapshot,
            "schema_version": "pilot.personal-services-mobile.v1",
            "persona_id": private_id,
            "proposals": [self._service_projection(item, private_persona_id=private_id) for item in snapshot["proposals"]],
            "receipts": [self._service_projection(item, private_persona_id=private_id) for item in snapshot["receipts"]],
            "child_requires_guardian": profile.get("role") == "child",
            "service_persona_id_exposed": False,
        }

    def prepare_service_action(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        private_id, service_id, _profile = self._service_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="services.propose",
        )
        assert self.service_hub is not None
        proposal = self.service_hub.prepare(
            persona_id=service_id, service=str(request.get("service") or ""),
            action=str(request.get("action") or ""), parameters=dict(request.get("parameters") or {}),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )
        return self._service_projection(proposal, private_persona_id=private_id)

    def update_service_details(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        private_id, service_id, _profile = self._service_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="services.propose",
        )
        assert self.service_hub is not None
        proposal = self.service_hub.update_details(
            str(request.get("proposal_id") or ""), persona_id=service_id,
            details=dict(request.get("details") or {}),
        )
        return self._service_projection(proposal, private_persona_id=private_id)

    def decide_service_action(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        private_id, service_id, profile = self._service_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="services.approve",
        )
        if profile.get("role") == "child" and bool(request.get("approved")):
            raise PermissionError("A guardian must approve a child's external service action")
        assert self.service_hub is not None
        snapshot = self.service_hub.snapshot_for_persona(service_id)
        proposal = next((item for item in snapshot["proposals"] if item.get("proposal_id") == request.get("proposal_id")), None)
        if proposal is None or proposal.get("parameters_hash") != request.get("parameters_hash"):
            raise PermissionError("The service details changed; review them again")
        decided = self.service_hub.decide(
            str(request["proposal_id"]), persona_id=service_id, approved=bool(request.get("approved")),
            parameters_hash=str(request.get("parameters_hash") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )
        return self._service_projection(decided, private_persona_id=private_id)

    def execute_service_action(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        private_id, service_id, profile = self._service_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="services.execute",
        )
        if profile.get("role") == "child":
            raise PermissionError("A guardian must execute a child's external service action")
        assert self.service_hub is not None
        snapshot = self.service_hub.snapshot_for_persona(service_id)
        proposal = next((item for item in snapshot["proposals"] if item.get("proposal_id") == request.get("proposal_id")), None)
        if proposal is None or proposal.get("parameters_hash") != request.get("parameters_hash"):
            raise PermissionError("The approved service details changed; review them again")
        receipt = self.service_hub.execute(
            str(request["proposal_id"]), persona_id=service_id,
            parameters_hash=str(request.get("parameters_hash") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )
        return self._service_projection(receipt, private_persona_id=private_id)

    def _library_ready(self) -> None:
        if self.private_saves is None or self.saved_followthrough is None:
            raise RuntimeError("Private saved items are not active on this mother")

    @classmethod
    def _library_projection(cls, value: dict[str, Any] | None, *, private_persona_id: str) -> dict[str, Any] | None:
        if value is None:
            return None
        projected = dict(value)
        if projected.get("persona_id"):
            projected["persona_id"] = private_persona_id
        if isinstance(projected.get("service_proposal"), dict):
            projected["service_proposal"] = cls._service_projection(
                dict(projected["service_proposal"]), private_persona_id=private_persona_id,
            )
        projected["service_persona_id_exposed"] = False
        return projected

    def library_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        self._library_ready()
        private_id, service_id, _profile = self._service_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="library.read",
        )
        if request.get("purpose") != "read_private_library":
            raise ValueError("The private library request is malformed")
        assert self.private_saves is not None and self.saved_followthrough is not None
        saves = self.private_saves.snapshot(persona_id=service_id)
        followthrough = self.saved_followthrough.snapshot(persona_id=service_id)
        return {
            "schema_version": "pilot.personal-library-mobile.v1",
            "persona_id": private_id,
            "pending": self._library_projection(saves.get("pending"), private_persona_id=private_id),
            "saved": [self._library_projection(item, private_persona_id=private_id) for item in saves.get("saved", [])],
            "saved_count": saves.get("saved_count", 0),
            "followthrough": [self._library_projection(item, private_persona_id=private_id) for item in followthrough.get("records", [])],
            "files_source": "encrypted_unified_inbox",
            "source_pixels_or_audio_exposed": False,
            "external_effect_inherited": False,
            "service_persona_id_exposed": False,
        }

    def claim_library_item(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        self._library_ready()
        private_id, service_id, _profile = self._service_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="library.write",
        )
        assert self.private_saves is not None
        item = self.private_saves.claim(str(request.get("save_id") or ""), persona_id=service_id)
        return self._library_projection(item, private_persona_id=private_id) or {}

    def delete_library_item(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        self._library_ready()
        private_id, service_id, _profile = self._service_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="library.write",
        )
        assert self.private_saves is not None
        receipt = self.private_saves.delete(
            str(request.get("save_id") or ""), persona_id=service_id,
            idempotency_key=str(request.get("idempotency_key") or ""),
        )
        return self._library_projection(receipt, private_persona_id=private_id) or {}

    def continue_library_item(
        self, request: dict[str, Any], *, certificate: dict[str, Any],
        lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        self._library_ready()
        private_id, service_id, _profile = self._service_persona(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="library.continue",
        )
        assert self.private_saves is not None and self.saved_followthrough is not None
        item = self.private_saves.get_saved(str(request.get("save_id") or ""), persona_id=service_id)
        action = str(request.get("action") or "")
        idempotency_key = str(request.get("idempotency_key") or "")
        if action == "research":
            if self.researcher is None:
                raise RuntimeError("AION research is not active on this mother")
            result = self.saved_followthrough.research(
                item=item, persona_id=service_id, researcher=self.researcher,
                idempotency_key=idempotency_key,
            )
        else:
            assert self.service_hub is not None
            result = self.saved_followthrough.prepare_action(
                item=item, persona_id=service_id, action=action,
                service_hub=self.service_hub, idempotency_key=idempotency_key,
            )
        return self._library_projection(result, private_persona_id=private_id) or {}

    def _device_authority(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str, scope: str,
    ) -> tuple[str, str]:
        idempotency_key = str(request.get("idempotency_key") or "")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{12,160}", idempotency_key):
            raise ValueError("A valid device idempotency key is required")
        authority = self.pairing.validate_signed_request(
            certificate=certificate, lease=lease, required_scope=scope,
            request=request, phone_signature=phone_signature,
        )
        persona_id = str(authority["persona_id"])
        device_id = str(authority["device_id"])
        if str(request.get("persona_id") or "") != persona_id:
            raise PermissionError("This phone cannot use another person's device mesh")
        return persona_id, device_id

    @staticmethod
    def _project_device_mesh(raw: dict[str, Any], *, persona_id: str) -> dict[str, Any]:
        nodes = []
        for source in list(raw.get("nodes") or [])[:128]:
            if not isinstance(source, dict):
                continue
            profile = dict(source.get("profile") or {})
            capabilities = []
            for capability in list(source.get("capabilities") or [])[:64]:
                if isinstance(capability, dict):
                    capabilities.append({
                        key: capability.get(key)
                        for key in ("capability_id", "kind", "description", "risk", "requires_approval")
                    })
            nodes.append({
                "node_id": str(profile.get("node_id") or source.get("node_id") or "")[:200],
                "name": str(profile.get("name") or source.get("name") or "Unknown device")[:160],
                "device_class": str(profile.get("device_class") or source.get("device_class") or "unknown")[:80],
                "platform": str(profile.get("platform") or source.get("platform") or "unknown")[:160],
                "transports": [str(value)[:40] for value in list(profile.get("transports") or source.get("transports") or [])[:12]],
                "controls": [str(value)[:120] for value in list(profile.get("controls") or source.get("controls") or [])[:64]],
                "role": str(source.get("role") or "observer")[:40],
                "enrollment": str(source.get("enrollment") or "discovered")[:40],
                "last_seen_at": str(source.get("last_seen_at") or "")[:80],
                "capabilities": capabilities,
                "is_primary_tv": bool(source.get("is_primary_tv")),
            })
        active = dict(raw.get("active_shared_identity") or {})
        active_state = "locked"
        if active:
            active_state = "you" if active.get("persona_id") == persona_id else "another_person"
        rooms = [
            {
                "node_id": str(item.get("node_id") or "")[:200],
                "room_name": str(item.get("room_name") or "Unnamed room")[:120],
                "device_name": str(item.get("device_name") or "Television")[:160],
                "default": bool(item.get("default")),
            }
            for item in list(raw.get("rooms") or [])[:32] if isinstance(item, dict)
        ]
        climate = dict(raw.get("climate") or {})
        return {
            "schema_version": "pilot.personal-device-mesh-mobile.v1",
            "persona_id": persona_id,
            "nodes": nodes,
            "node_count": len(nodes),
            "rooms": rooms,
            "tv_connection": {
                "status": str(dict(raw.get("tv_connection") or {}).get("status") or "not_verified")[:60],
                "message": str(dict(raw.get("tv_connection") or {}).get("message") or "Refresh the TV to verify its live state.")[:240],
                "last_checked_at": dict(raw.get("tv_connection") or {}).get("last_checked_at"),
            },
            "shared_tv": {
                "state": active_state,
                "display_name": str(active.get("display_name") or "")[:100] if active_state == "you" else "",
                "expires_at": active.get("expires_at") if active_state == "you" else None,
                "presence_expires_at": active.get("presence_expires_at") if active_state == "you" else None,
                "last_presence_at": active.get("last_presence_at") if active_state == "you" else None,
                "idle_timeout_seconds": int(active.get("idle_timeout_seconds") or 300),
                "departure_timeout_seconds": int(active.get("departure_timeout_seconds") or 300),
                "exclusive": True,
            },
            "climate": {
                "connected": bool(climate.get("connected")),
                "learned_presets": [str(item.get("preset") or "")[:60] for item in list(climate.get("learned_presets") or []) if isinstance(item, dict)][:64],
                "last_active_preset": str(climate.get("last_active_preset") or "")[:60],
                "last_sent_at": climate.get("last_sent_at"),
                "state_verified": False,
            },
            "public_keys_or_network_addresses_exposed": False,
            "discovery_grants_control": False,
        }

    def device_mesh_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="devices.read",
        )
        if request.get("purpose") != "read_private_device_mesh" or self.device_snapshot_provider is None:
            raise RuntimeError("The private device mesh is not active on this mother")
        return self._project_device_mesh(self.device_snapshot_provider(), persona_id=persona_id)

    def discover_device_mesh(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="devices.discover",
        )
        if request.get("purpose") != "scan_local_device_advertisements" or self.device_discovery is None or self.device_snapshot_provider is None:
            raise RuntimeError("Safe local device discovery is not active on this mother")
        self.device_discovery()
        result = self._project_device_mesh(self.device_snapshot_provider(), persona_id=persona_id)
        result["scan_safety"] = {"enrollment_changed": False, "control_sent": False, "credential_attempted": False}
        return result

    def control_shared_tv(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        command = str(request.get("command") or "")
        observe = command == "observe"
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="tv.observe" if observe else "tv.control",
        )
        allowed = {
            "observe", "up", "down", "left", "right", "enter", "back", "home",
            "volume_up", "volume_down", "play", "pause", "mute", "unmute",
            "netflix", "youtube", "aion", "games", "god_view",
        }
        if command not in allowed or self.device_command_executor is None:
            raise PermissionError("That television command is outside the mobile control boundary")
        if not observe:
            self.identities.touch_shared_screen(persona_id=persona_id, source="unified_mobile_device_control")
        arguments = dict(request.get("arguments") or {})
        arguments["_request_id"] = str(request.get("idempotency_key") or "")
        result = self.device_command_executor(command, arguments)
        return {
            "schema_version": "pilot.personal-tv-control-mobile.v1",
            "command": command,
            "accepted": bool(result.get("accepted")),
            "spoken_response": str(result.get("spoken_response") or "")[:400],
            "receipt": result.get("receipt"),
            "verified_navigation": result.get("verified_navigation"),
            "button_delivery_alone_is_success": False,
        }

    def change_shared_tv_session(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id, device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="tv.control",
        )
        operation = str(request.get("operation") or "")
        possession_nonce = str(request.get("possession_nonce") or "")
        possession_signature = str(request.get("possession_signature") or "")
        if operation == "acquire":
            result = self.identities.activate_shared_screen(
                persona_id=persona_id, device_id=device_id, nonce=possession_nonce,
                signature=possession_signature, minutes=5,
            )
            return {"state": "you", "display_name": result.get("display_name"), "expires_at": result.get("expires_at"), "exclusive": True}
        if operation == "release":
            result = self.identities.release_shared_screen_signed(
                persona_id=persona_id, device_id=device_id, nonce=possession_nonce,
                signature=possession_signature,
            )
            return {"state": "locked", "released": bool(result.get("released")), "exclusive": True}
        raise ValueError("Choose acquire or release for the shared television")

    def confirm_shared_tv_presence(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str, trusted_local_address: bool = False,
    ) -> dict[str, Any]:
        persona_id, device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="tv.control",
        )
        if request.get("purpose") != "confirm_local_phone_presence":
            raise ValueError("A valid local-presence purpose is required")
        if not trusted_local_address:
            raise PermissionError("Shared-screen presence must be proved directly on the trusted home network")
        # This is an explicit, signed action from the controller, not passive
        # proximity telemetry. Renew both the nearby-phone proof and the
        # bounded shared-dashboard lease so the button labelled "Keep active"
        # does exactly that.
        self.identities.confirm_shared_screen_presence(persona_id=persona_id, device_id=device_id)
        active = self.identities.touch_shared_screen(
            persona_id=persona_id,
            source="explicit_mobile_dashboard_keepalive",
        )
        return {
            "schema_version": "pilot.shared-tv-presence.v1", "state": "you",
            "expires_at": active.get("expires_at"),
            "presence_expires_at": active.get("presence_expires_at"),
            "last_presence_at": active.get("last_presence_at"),
            "idle_timeout_seconds": active.get("idle_timeout_seconds"),
            "departure_timeout_seconds": active.get("departure_timeout_seconds"),
            "passive_presence_counts_as_activity": False,
        }

    def control_shared_tv_presentation(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="tv.control",
        )
        operation = str(request.get("operation") or "")
        if operation not in {"present", "dismiss"} or self.tv_presentation_executor is None:
            raise PermissionError("That shared-screen presentation action is unavailable")
        result = dict(self.tv_presentation_executor(persona_id, request) or {})
        if operation == "present":
            self.identities.touch_shared_screen(persona_id=persona_id, source="deliberate_phone_presentation")
        return {
            "schema_version": "pilot.personal-tv-presentation-mobile.v1",
            "operation": operation,
            "result": result,
            "private_content_persisted_on_tv": False,
            "authority_expires_with_shared_session": True,
        }

    def control_dashboard_action(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        """Open one explicitly allowed Pilot surface from the signed phone."""
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="tv.control",
        )
        command = str(request.get("command") or "")
        allowed = {"games", "aion", "education_start", "tasks", "calendar", "files", "iot", "work"}
        if command not in allowed or self.dashboard_action_executor is None:
            raise PermissionError("That Pilot dashboard action is outside this phone's authority")
        arguments = dict(request.get("arguments") or {})
        if len(str(arguments)) > 2_048:
            raise ValueError("That Pilot dashboard action is too large")
        self.identities.touch_shared_screen(persona_id=persona_id, source="signed_mobile_dashboard_action")
        result = dict(self.dashboard_action_executor(persona_id, command, arguments) or {})
        return {
            "schema_version": "pilot.personal-dashboard-action-mobile.v1",
            "command": command,
            "accepted": bool(result.get("accepted", True)),
            "spoken_response": str(result.get("spoken_response") or "Pilot opened the requested surface.")[:500],
            "receipt": result.get("receipt"),
            "verified_navigation": result.get("verified_navigation"),
        }

    def control_iot_device(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="devices.control",
        )
        command = str(request.get("command") or "")
        if command != "ir_send" or self.device_command_executor is None:
            raise PermissionError("That IoT action is outside the signed mobile capability")
        preset = str(request.get("preset") or "")
        result = self.device_command_executor(command, {"preset": preset, "_request_id": str(request.get("idempotency_key") or "")})
        climate = dict(result.get("infrared_climate") or {})
        return {
            "schema_version": "pilot.personal-iot-control-mobile.v1",
            "command": command, "preset": str(climate.get("preset") or preset),
            "transport_delivered": bool(climate.get("transport_delivered")),
            "device_state_verified": False,
            "spoken_response": str(result.get("spoken_response") or "")[:400],
        }

    def experience_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="experiences.read",
        )
        if request.get("purpose") != "read_private_learning_games_entertainment" or self.experience_snapshot_provider is None:
            raise RuntimeError("Private learning, games and entertainment are not active on this mother")
        snapshot = dict(self.experience_snapshot_provider(persona_id) or {})
        return {
            "schema_version": "pilot.personal-experiences-mobile.v1",
            "persona_id": persona_id,
            "learning": dict(snapshot.get("learning") or {}),
            "games": dict(snapshot.get("games") or {}),
            "entertainment": dict(snapshot.get("entertainment") or {}),
            "claims": {
                "provider_open_is_playing": False,
                "prepared_continuation_is_playing": False,
                "child_open_web_enabled": False,
                "paid_ai_required_for_learning": False,
            },
        }

    def control_experience(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="experiences.control",
        )
        operation = str(request.get("operation") or "")
        allowed = {
            "learning_start", "learning_answer", "learning_next", "learning_repeat",
            "games_open", "games_continue", "entertainment_continue_prepare",
            "entertainment_continue_confirm", "entertainment_continue_execute",
            "entertainment_remember", "entertainment_watchlist_add",
        }
        if operation not in allowed or self.experience_command_executor is None:
            raise PermissionError("That experience action is outside the mobile boundary")
        arguments = dict(request.get("arguments") or {})
        if len(str(arguments)) > 12_000:
            raise ValueError("That experience request is too large")
        if operation in {"games_open", "games_continue", "entertainment_continue_execute"}:
            self.pairing.validate_signed_request(
                certificate=certificate, lease=lease, required_scope="tv.control",
                request=request, phone_signature=phone_signature,
            )
            self.identities.touch_shared_screen(
                persona_id=persona_id, source="unified_mobile_experience_control",
            )
        arguments["_request_id"] = str(request.get("idempotency_key") or "")
        result = dict(self.experience_command_executor(persona_id, operation, arguments) or {})
        return {
            "schema_version": "pilot.personal-experience-action-mobile.v1",
            "operation": operation,
            "accepted": bool(result.get("accepted", True)),
            "state": str(result.get("state") or "recorded")[:100],
            "spoken_response": str(result.get("spoken_response") or "Experience updated.")[:500],
            "learning": result.get("learning"),
            "games": result.get("games"),
            "entertainment": result.get("entertainment"),
            "device_attempt": result.get("device_attempt"),
            "external_effect_verified": bool(result.get("external_effect_verified")),
            "playing_verified": bool(result.get("playing_verified")),
        }

    def _memory_authority(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str, scope: str,
    ) -> tuple[str, str, dict[str, Any]]:
        requester_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope=scope,
        )
        target_id = str(request.get("target_persona_id") or requester_id)
        identity = self.identities.snapshot(viewer_persona_id=requester_id)
        profiles = list(identity.get("profiles") or [])
        requester = next((dict(item) for item in profiles if item.get("persona_id") == requester_id and item.get("status") == "active"), None)
        target = next((dict(item) for item in profiles if item.get("persona_id") == target_id and item.get("status") == "active"), None)
        if requester is None or target is None:
            raise PermissionError("That private identity is not active")
        guardian_access = (
            requester.get("role") == "adult" and target.get("role") == "child"
            and target.get("guardian_persona_id") == requester_id
        )
        if target_id != requester_id and not guardian_access:
            raise PermissionError("This phone cannot inspect or change another person's memory")
        return requester_id, target_id, target

    def memory_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        requester_id, target_id, target = self._memory_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="memory.read",
        )
        if request.get("purpose") != "inspect_private_memory":
            raise ValueError("The private memory request is malformed")
        memories = self.identities.memories(persona_id=target_id, requester_persona_id=requester_id)
        return {
            "schema_version": "pilot.personal-memory-mobile.v1",
            "persona_id": target_id,
            "display_name": str(target.get("display_name") or "Private identity")[:100],
            "guardian_managed": target_id != requester_id,
            "memories": memories,
            "memory_count": len(memories),
            "allowed_scopes": sorted(self.identities.MEMORY_SCOPES),
            "claims": {
                "other_adult_memory_exposed": False,
                "raw_provider_secret_included": False,
                "deletion_recoverable": False,
            },
        }

    def create_memory(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        _requester_id, target_id, _target = self._memory_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="memory.write",
        )
        return self.identities.remember(
            persona_id=target_id, kind=str(request.get("kind") or "preference"),
            summary=str(request.get("summary") or ""), scope=str(request.get("scope") or "private"),
            source_reference="unified_mobile_explicit_entry",
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def update_memory(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        _requester_id, target_id, _target = self._memory_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="memory.write",
        )
        return self.identities.update_memory(
            persona_id=target_id, memory_id=str(request.get("memory_id") or ""),
            summary=request.get("summary"), scope=request.get("scope"),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def delete_memory(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        _requester_id, target_id, _target = self._memory_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="memory.write",
        )
        if request.get("confirm_irrecoverable") is not True:
            raise PermissionError("Confirm permanent deletion of this memory")
        return self.identities.delete_memory(
            persona_id=target_id, memory_id=str(request.get("memory_id") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def export_memory(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        requester_id, target_id, _target = self._memory_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="memory.export",
        )
        exported = self.identities.export(persona_id=target_id, requester_persona_id=requester_id)
        return {
            "schema_version": "pilot.personal-memory-export-envelope.v1",
            "persona_id": target_id,
            "export": exported,
            "recovery_secret_included": False,
            "device_public_key_included": False,
        }

    def _guardian_authority(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str, scope: str,
    ) -> tuple[str, str]:
        if self.guardian is None:
            raise RuntimeError("Pilot Guardian is not active on this mother")
        requester_id, target_id, _profile = self._memory_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope=scope,
        )
        return requester_id, target_id

    def guardian_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        _requester_id, target_id = self._guardian_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="guardian.read",
        )
        if request.get("purpose") != "read_private_guardian":
            raise ValueError("The Guardian request is malformed")
        assert self.guardian is not None
        snapshot = self.guardian.snapshot(persona_id=target_id)
        permissions = list(snapshot.get("permissions") or [])
        incidents = list(snapshot.get("incidents") or [])
        return {
            "schema_version": "pilot.guardian-mobile.v1", "persona_id": target_id,
            "permissions": permissions, "incidents": incidents,
            "sensor_signals": list(snapshot.get("sensor_signals") or []),
            "latest_incident": dict(incidents[-1]) if incidents else None,
            "claims": {
                "medical_diagnosis": False, "automatic_dispatch": False,
                "ambulance_dispatched": False, "ordinary_contact_permission_implied": False,
            },
        }

    def configure_guardian_contact(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        _requester_id, target_id = self._guardian_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="guardian.configure",
        )
        assert self.guardian is not None
        return self.guardian.grant_emergency_contact(
            persona_id=target_id, contact_id=str(request.get("contact_id") or ""),
            channel=str(request.get("channel") or "pilot"), share_location=bool(request.get("share_location")),
            location_permission_receipt=str(request.get("location_permission_receipt") or ""),
            allow_interruption=bool(request.get("allow_interruption", True)),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def control_guardian_incident(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        _requester_id, target_id = self._guardian_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="guardian.alert",
        )
        assert self.guardian is not None
        operation = str(request.get("operation") or "")
        key = str(request.get("idempotency_key") or "")
        if operation == "request":
            result = self.guardian.request_help(
                persona_id=target_id, trigger=str(request.get("trigger") or "Explicit private-phone help request"),
                surface="unified_private_phone", location=dict(request.get("location") or {}),
                idempotency_key=key,
            )
        elif operation == "cancel":
            result = self.guardian.cancel(
                incident_id=str(request.get("incident_id") or ""), persona_id=target_id,
                reason="private_phone_false_alarm", idempotency_key=key,
            )
        elif operation == "confirm":
            confirmed = self.guardian.confirm(
                incident_id=str(request.get("incident_id") or ""), persona_id=target_id,
                idempotency_key=f"{key}:confirm",
            )
            result = self.guardian.deliver_alerts(
                incident_id=str(confirmed.get("incident_id") or ""), persona_id=target_id,
                idempotency_key=f"{key}:deliver",
            )
        else:
            raise ValueError("Choose request, confirm or cancel for Guardian")
        return {
            "schema_version": "pilot.guardian-mobile-action.v1", "operation": operation,
            "result": result, "ambulance_dispatched": False,
            "delivery_verified": bool(result.get("verified_alerts")),
            "fallback_required": result.get("status") == "connectivity_fallback_required",
        }

    def intelligence_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="intelligence.read",
        )
        if request.get("purpose") != "read_private_intelligence_route" or self.intelligence_status_provider is None:
            raise RuntimeError("The AION intelligence route is not active on this mother")
        source = dict(self.intelligence_status_provider() or {})
        return {
            "schema_version": "pilot.intelligence-mobile.v1", "persona_id": persona_id,
            "mode": str(source.get("mode") or "native"), "label": str(source.get("label") or "AION Native"),
            "route": list(source.get("route") or []),
            "gemini_connected": bool(source.get("gemini_connected")),
            "openai_connected": bool(source.get("openai_connected")),
            "gemini_grounding_enabled": bool(source.get("gemini_grounding_enabled")),
            "usage": dict(source.get("usage") or {}), "secrets_projected_to_phone": False,
            "native_core_requires_paid_provider": False,
        }

    def use_intelligence(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="intelligence.use",
        )
        query = " ".join(str(request.get("query") or "").split())[:4000]
        if not query or self.intelligence_command_executor is None:
            raise ValueError("Ask Pilot a private question or action")
        result = dict(self.intelligence_command_executor(persona_id, "ask", {"query": query, "_request_id": str(request.get("idempotency_key") or "")}) or {})
        return {
            "schema_version": "pilot.intelligence-mobile-result.v1", "persona_id": persona_id,
            "accepted": bool(result.get("accepted")), "spoken_response": str(result.get("spoken_response") or "")[:4000],
            "intent": str(dict(result.get("intent") or {}).get("action") or "")[:120],
            "display_label": str(result.get("display_label") or dict(result.get("research") or {}).get("display_label") or "AION Local")[:120],
            "receipt": result.get("receipt"), "proposal": result.get("agent_task") or result.get("research"),
            "external_action_claimed_without_receipt": False,
        }

    def configure_intelligence(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id, _device_id = self._device_authority(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="intelligence.configure",
        )
        mode = str(request.get("mode") or "")
        if mode not in {"native", "gemini", "boost"} or self.intelligence_command_executor is None:
            raise ValueError("Choose AION Native, AION + Gemini or Pilot Boost")
        result = dict(self.intelligence_command_executor(persona_id, "configure", {
            "mode": mode, "gemini_grounding_enabled": bool(request.get("gemini_grounding_enabled")),
            "_request_id": str(request.get("idempotency_key") or ""),
        }) or {})
        result.pop("settings_path", None)
        result["provider_keys_projected_to_phone"] = False
        return result
