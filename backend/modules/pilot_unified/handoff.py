from __future__ import annotations

from typing import Any

from .adoption import TrustedNetworkAuthority
from .inbox import UnifiedInbox


HANDOFF_TYPES = frozenset({"message", "task", "reminder", "file", "moment"})


class TrustedHandoffAuthority:
    """One relationship-gated entry point for private Pilot-to-Pilot objects.

    The authority deliberately delegates encryption, replay protection and phone
    possession checks to ``UnifiedInbox``.  It adds the missing relationship
    boundary and a stable cross-type contract; it is not a second message store.
    """

    def __init__(self, *, network: TrustedNetworkAuthority, inbox: UnifiedInbox) -> None:
        self.network = network
        self.inbox = inbox

    def snapshot(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self.inbox._authorize(  # noqa: SLF001 - shared authority boundary
            certificate=certificate,
            lease=lease,
            scope="inbox.read",
            request=request,
            phone_signature=phone_signature,
        )
        relationships = self.network.relationships_for(persona_id)
        return {
            "schema_version": "pilot.trusted-handoffs.v1",
            "persona_id": persona_id,
            "supported_types": sorted(HANDOFF_TYPES),
            "relationships": relationships,
            "delivery_semantics": {
                "encrypted_packet_ready": "Encrypted for the recipient mother; transport has not yet proved receipt.",
                "awaiting_private_approval": "Prepared on this phone; nothing has been sent.",
                "recipient_mother_received": "The destination mother verified and stored the packet.",
                "recipient_accepted": "The recipient explicitly accepted the item.",
            },
        }

    def _relationship(self, request: dict[str, Any], persona_id: str) -> tuple[str, str]:
        relationship_id = str(request.get("relationship_id") or "")
        recipient_persona_id = str(request.get("recipient_persona_id") or "")
        if not relationship_id or not recipient_persona_id:
            raise ValueError("Choose one trusted Pilot relationship")
        if not self.network.authorize_contact(
            relationship_id=relationship_id,
            sender_persona_id=persona_id,
            recipient_persona_id=recipient_persona_id,
        ):
            raise PermissionError("That Pilot relationship is not active for these people")
        return relationship_id, recipient_persona_id

    @staticmethod
    def _validate_moment(request: dict[str, Any]) -> None:
        moment = request
        rights = dict(moment.get("rights") or {})
        if not str(moment.get("moment_id") or "").startswith("moment_"):
            raise ValueError("Choose one prepared Pilot Moment")
        if not str(moment.get("context_hash") or moment.get("payload_hash") or ""):
            raise ValueError("That Moment has no verifiable context hash")
        if rights.get("protected_audio_copied") is not False or rights.get("protected_video_copied") is not False:
            raise PermissionError("Pilot-to-Pilot Moments cannot copy protected audio or video")

    def send(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        handoff_type = str(request.get("handoff_type") or "")
        if handoff_type not in HANDOFF_TYPES:
            raise ValueError("Choose message, task, reminder, file or Moment")
        required_scope = "task.create" if handoff_type == "task" else "message.send"
        persona_id = self.inbox._authorize(  # noqa: SLF001 - shared authority boundary
            certificate=certificate,
            lease=lease,
            scope=required_scope,
            request=request,
            phone_signature=phone_signature,
        )
        relationship_id, _ = self._relationship(request, persona_id)

        if handoff_type == "message":
            result = self.inbox.send_text(request, certificate=certificate, lease=lease, phone_signature=phone_signature)
        elif handoff_type == "task":
            result = self.inbox.prepare_task(request, certificate=certificate, lease=lease, phone_signature=phone_signature)
            return {
                "schema_version": "pilot.trusted-handoff-result.v1",
                "handoff_type": handoff_type,
                "relationship_id": relationship_id,
                "transport_state": "awaiting_private_approval",
                "result": result,
                "external_effect_verified": False,
            }
        elif handoff_type == "reminder":
            if request.get("card_type") != "reminder":
                raise ValueError("Reminder handoffs require a reminder card")
            result = self.inbox.send_structured_card(request, certificate=certificate, lease=lease, phone_signature=phone_signature)
        elif handoff_type == "file":
            result = self.inbox.send_attachment(request, certificate=certificate, lease=lease, phone_signature=phone_signature)
        else:
            if request.get("card_type") != "moment":
                raise ValueError("Moment handoffs require a Moment card")
            self._validate_moment(request)
            result = self.inbox.send_structured_card(request, certificate=certificate, lease=lease, phone_signature=phone_signature)

        return {
            "schema_version": "pilot.trusted-handoff-result.v1",
            "handoff_type": handoff_type,
            "relationship_id": relationship_id,
            "transport_state": "encrypted_packet_ready",
            "result": result,
            "external_effect_verified": False,
        }

    def approve_task(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self.inbox._authorize(  # noqa: SLF001 - shared authority boundary
            certificate=certificate,
            lease=lease,
            scope="message.send",
            request=request,
            phone_signature=phone_signature,
        )
        relationship_id, _ = self._relationship(request, persona_id)
        packet = self.inbox.approve_and_export_task(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
        )
        return {
            "schema_version": "pilot.trusted-handoff-result.v1",
            "handoff_type": "task",
            "relationship_id": relationship_id,
            "transport_state": "encrypted_packet_ready",
            "delivery_packet": packet,
            "external_effect_verified": False,
        }
