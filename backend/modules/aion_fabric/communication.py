from __future__ import annotations

import json
import os
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .pilot_inbox import PilotInbox
from .private_identity import ProductionPrivateIdentity


class GovernedCommunication:
    """Persona-private drafts, inbox summaries and verified delivery boundaries."""

    _lock = threading.RLock()
    CHANNELS = {"email", "sms", "messaging", "whatsapp", "pilot", "call"}

    def __init__(
        self, runtime_dir: str | Path, *, identities: ProductionPrivateIdentity | None = None,
        inbox: PilotInbox | None = None,
    ) -> None:
        self.root = Path(runtime_dir) / "communication"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.identities = identities or ProductionPrivateIdentity(runtime_dir)
        self.inbox = inbox or PilotInbox(runtime_dir, identities=self.identities)
        self.adapters: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {
            "schema_version": "pilot.communication.v1", "drafts": [], "received": [],
            "follow_ups": [], "receipts": [], "call_preparations": [], "mobile_requests": [],
            "invitations": [], "blocks": [], "reports": [],
        }

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _write(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    def _profile(self, persona_id: str) -> Dict[str, Any]:
        profile = next((item for item in self.identities.snapshot().get("profiles", []) if item.get("persona_id") == persona_id and item.get("status") == "active"), None)
        if profile is None:
            raise PermissionError("A production private identity is required")
        return dict(profile)

    @staticmethod
    def _text(value: Any, maximum: int) -> str:
        return " ".join(str(value or "").split())[:maximum]

    def register_adapter(self, channel: str, adapter: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        if channel not in self.CHANNELS - {"call"}:
            raise ValueError("Unsupported communication adapter")
        self.adapters[channel] = adapter

    def draft(
        self, *, persona_id: str, contact_id: str, channel: str, body: str,
        subject: str = "", reply_to_message_id: str = "", attachments: list[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        profile = self._profile(persona_id)
        channel = str(channel).lower()
        if channel not in self.CHANNELS - {"call"}:
            raise ValueError("Unsupported communication channel")
        state_inbox = self.inbox._read()  # same private owner boundary; never projected to TV
        contact = next((item for item in state_inbox.get("contacts", []) if item.get("contact_id") == contact_id and item.get("owner_persona_id") == persona_id and item.get("status", "active") == "active"), None)
        if contact is None:
            raise PermissionError("Choose one of this identity's private contacts")
        route_field = "email" if channel == "email" else "sms" if channel == "sms" else "whatsapp" if channel in {"messaging", "whatsapp"} else "pilot_persona_id"
        recipient = str(contact.get(route_field) or "")
        if not recipient:
            raise ValueError(f"That contact has no authorized {channel} route")
        clean_body = self._text(body, 20_000)
        if not clean_body:
            raise ValueError("Message content is required")
        now = datetime.now(timezone.utc)
        recent_contacts = {
            str(item.get("contact_id") or "") for item in self._read().get("drafts", [])
            if item.get("persona_id") == persona_id
            and datetime.fromisoformat(str(item.get("created_at")).replace("Z", "+00:00")) >= now - timedelta(days=1)
        }
        if contact_id not in recent_contacts and len(recent_contacts) >= 50:
            raise PermissionError("Daily new-recipient limit reached; review contacts before continuing")
        blocked = next((item for item in self._read().get("blocks", []) if item.get("persona_id") == persona_id and item.get("contact_id") == contact_id and item.get("status") == "active"), None)
        if blocked:
            raise PermissionError("That contact is blocked for this identity")
        exact_attachments: list[Dict[str, Any]] = []
        for item in list(attachments or [])[:10]:
            if set(item) != {"attachment_id", "name", "media_type", "size", "sha256"}:
                raise ValueError("Attachment metadata is malformed")
            size = int(item.get("size") or 0)
            digest = str(item.get("sha256") or "").lower()
            if size < 1 or size > 20_000_000 or not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("Attachment size or digest is invalid")
            exact_attachments.append({
                "attachment_id": self._text(item.get("attachment_id"), 160),
                "name": self._text(item.get("name"), 240),
                "media_type": self._text(item.get("media_type"), 120),
                "size": size, "sha256": digest,
            })
        if profile.get("role") in {"child", "teen"} and channel != "pilot":
            guardian = str(profile.get("guardian_persona_id") or "")
            if not guardian:
                raise PermissionError("A guardian-controlled identity is required for external communication")
            guardian_state = "guardian_approval_required"
        else:
            guardian, guardian_state = "", "not_required"
        draft = {
            "draft_id": f"communication_draft_{uuid4().hex}", "persona_id": persona_id,
            "contact_id": contact_id, "recipient_name": str(contact.get("display_name") or "Contact"),
            "recipient": recipient, "channel": channel, "subject": self._text(subject, 240),
            "body": clean_body, "reply_to_message_id": self._text(reply_to_message_id, 160),
            "attachments": exact_attachments,
            "drafted_by": "AION Native", "model_provider_required": False,
            "guardian_persona_id": guardian, "guardian_state": guardian_state,
            "status": guardian_state if guardian_state != "not_required" else "awaiting_private_approval",
            "content_hash": canonical_hash({"channel": channel, "recipient": recipient, "subject": subject, "body": clean_body, "attachments": exact_attachments}),
            "external_effect": False, "created_at": utc_now_iso(),
        }
        with self._lock:
            state = self._read(); state["drafts"] = list(state.get("drafts") or [])[-199:] + [draft]; self._write(state)
        return dict(draft)

    def draft_mobile(
        self, *, persona_id: str, contact_id: str, channel: str, body: str,
        subject: str = "", reply_to_message_id: str = "", attachments: list[Dict[str, Any]] | None = None,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Prepare one retry-safe phone draft without producing an external effect."""
        if len(str(idempotency_key)) < 8:
            raise ValueError("A communication request key is required")
        scope = {
            "persona_id": persona_id, "contact_id": contact_id, "channel": channel,
            "subject": subject, "body": body, "reply_to_message_id": reply_to_message_id,
            "attachments": list(attachments or []),
        }
        request_hash = canonical_hash(scope)
        with self._lock:
            state = self._read()
            previous = next((item for item in state.get("mobile_requests", []) if item.get("persona_id") == persona_id and item.get("idempotency_key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash or previous.get("operation") != "communication.draft":
                    raise PermissionError("That communication request key was reused for different content")
                draft = next((item for item in state.get("drafts", []) if item.get("draft_id") == previous.get("object_id")), None)
                if draft is None:
                    raise RuntimeError("Pilot cannot reconcile that earlier communication draft")
                return dict(draft)
            draft = self.draft(
                persona_id=persona_id, contact_id=contact_id, channel=channel,
                subject=subject, body=body, reply_to_message_id=reply_to_message_id,
                attachments=attachments,
            )
            state = self._read()
            state.setdefault("mobile_requests", []).append({
                "persona_id": persona_id, "idempotency_key": str(idempotency_key)[:160],
                "request_hash": request_hash, "object_id": draft["draft_id"],
                "operation": "communication.draft",
            })
            state["mobile_requests"] = state["mobile_requests"][-2048:]
            self._write(state)
            return draft

    def approve(self, *, draft_id: str, persona_id: str, content_hash: str, approved: bool) -> Dict[str, Any]:
        with self._lock:
            state = self._read(); draft = next((item for item in state["drafts"] if item.get("draft_id") == draft_id), None)
            if draft is None: raise KeyError("Communication draft was not found")
            if draft.get("persona_id") != persona_id: raise PermissionError("Only the sender can approve this communication")
            if draft.get("content_hash") != content_hash: raise PermissionError("The recipient or content changed; review it again")
            if draft.get("guardian_state") == "guardian_approval_required": raise PermissionError("Guardian approval is required before the sender can approve this draft")
            if draft.get("status") != "awaiting_private_approval": return dict(draft)
            draft["status"] = "approved_pending_adapter" if approved else "rejected"
            draft["approved_at"] = utc_now_iso(); draft["approved_by_persona"] = persona_id if approved else None
            self._write(state); return dict(draft)

    def decide_mobile(
        self, *, draft_id: str, persona_id: str, content_hash: str,
        approved: bool, idempotency_key: str,
    ) -> Dict[str, Any]:
        if len(str(idempotency_key)) < 8:
            raise ValueError("A communication decision key is required")
        request_hash = canonical_hash({
            "draft_id": draft_id, "persona_id": persona_id,
            "content_hash": content_hash, "approved": bool(approved),
        })
        with self._lock:
            state = self._read()
            previous = next((item for item in state.get("mobile_requests", []) if item.get("persona_id") == persona_id and item.get("idempotency_key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash or previous.get("operation") != "communication.decide":
                    raise PermissionError("That communication decision key was reused for a different decision")
                draft = next((item for item in state.get("drafts", []) if item.get("draft_id") == draft_id), None)
                if draft is None:
                    raise RuntimeError("Pilot cannot reconcile that earlier communication decision")
                return dict(draft)
            result = self.approve(
                draft_id=draft_id, persona_id=persona_id,
                content_hash=content_hash, approved=approved,
            )
            state = self._read()
            state.setdefault("mobile_requests", []).append({
                "persona_id": persona_id, "idempotency_key": str(idempotency_key)[:160],
                "request_hash": request_hash, "object_id": draft_id,
                "operation": "communication.decide",
            })
            state["mobile_requests"] = state["mobile_requests"][-2048:]
            self._write(state)
            return result

    def guardian_decide(self, *, draft_id: str, guardian_persona_id: str, approved: bool) -> Dict[str, Any]:
        self._profile(guardian_persona_id)
        with self._lock:
            state = self._read(); draft = next((item for item in state["drafts"] if item.get("draft_id") == draft_id), None)
            if draft is None: raise KeyError("Communication draft was not found")
            if draft.get("guardian_persona_id") != guardian_persona_id: raise PermissionError("That guardian cannot approve this communication")
            if draft.get("guardian_state") != "guardian_approval_required": return dict(draft)
            draft["guardian_state"] = "approved" if approved else "rejected"
            draft["status"] = "awaiting_private_approval" if approved else "rejected"
            draft["guardian_decided_at"] = utc_now_iso(); self._write(state); return dict(draft)

    def execute(self, *, draft_id: str, persona_id: str) -> Dict[str, Any]:
        with self._lock:
            state = self._read(); draft = next((item for item in state["drafts"] if item.get("draft_id") == draft_id), None)
            if draft is None: raise KeyError("Communication draft was not found")
            if draft.get("persona_id") != persona_id or draft.get("approved_by_persona") != persona_id: raise PermissionError("Exact sender approval is required")
            if draft.get("status") in {"provider_accepted", "delivered"}:
                return dict(next(item for item in state["receipts"] if item.get("draft_id") == draft_id))
            if draft.get("status") != "approved_pending_adapter": raise PermissionError("This communication is not approved for delivery")
            adapter = self.adapters.get(str(draft.get("channel")))
            if adapter is None: raise RuntimeError("An authorized sending account is not connected")
            draft["status"] = "executing"; draft["attempt_id"] = f"communication_attempt_{uuid4().hex}"; self._write(state)
            try: result = adapter(dict(draft))
            except Exception:
                draft["status"] = "delivery_unknown_reconcile_required"; self._write(state); raise
            if not isinstance(result, dict) or not result.get("verified") or not result.get("provider_message_id"):
                draft["status"] = "delivery_unknown_reconcile_required"; self._write(state)
                raise RuntimeError("The provider did not return a verified delivery receipt")
            receipt = {
                "receipt_id": f"communication_receipt_{uuid4().hex}", "draft_id": draft_id,
                "persona_id": persona_id, "channel": draft["channel"], "verified": True,
                "provider_message_id": self._text(result["provider_message_id"], 200),
                "provider_thread_id": self._text(result.get("provider_thread_id"), 200),
                "provider_response_retained": False, "recipient_hash": canonical_hash(draft["recipient"]),
                "provider_state": "provider_accepted", "human_delivery_verified": False,
                "provider_accepted_at": utc_now_iso(),
            }
            draft["status"] = "provider_accepted"; draft["external_effect"] = True
            state["receipts"] = list(state.get("receipts") or [])[-399:] + [receipt]; self._write(state); return dict(receipt)

    def confirm_delivery(self, *, persona_id: str, provider_message_id: str, evidence_id: str) -> Dict[str, Any]:
        """Accept a provider delivery event; a send response alone is never human delivery."""
        if not evidence_id:
            raise ValueError("Authenticated provider delivery evidence is required")
        with self._lock:
            state = self._read()
            receipt = next((item for item in state.get("receipts", []) if item.get("persona_id") == persona_id and item.get("provider_message_id") == provider_message_id), None)
            if receipt is None:
                raise PermissionError("That provider message is unavailable")
            draft = next(item for item in state["drafts"] if item.get("draft_id") == receipt.get("draft_id"))
            receipt.update({"provider_state": "delivered", "human_delivery_verified": False, "delivery_evidence_hash": canonical_hash(evidence_id), "delivered_at": utc_now_iso()})
            draft["status"] = "delivered"
            self._write(state)
            return dict(receipt)

    def ingest_received(
        self, *, persona_id: str, provider_message_id: str, sender_name: str,
        received_at: str, body: str, source: str,
    ) -> Dict[str, Any]:
        self._profile(persona_id)
        when = datetime.fromisoformat(str(received_at).replace("Z", "+00:00"))
        age = max(0, int((datetime.now(timezone.utc) - when.astimezone(timezone.utc)).total_seconds()))
        clean_body = self._text(body, 20_000)
        record = {
            "message_id": f"received_{uuid4().hex}", "persona_id": persona_id,
            "provider_message_id": self._text(provider_message_id, 200), "sender_name": self._text(sender_name, 100),
            "received_at": when.isoformat(), "freshness_seconds_at_ingest": age,
            "summary": self._text(clean_body, 280), "summary_route": "AION Native deterministic",
            "source": self._text(source, 100), "source_provenance_present": bool(source),
            "body_hash": canonical_hash(clean_body), "raw_body_retained": False,
        }
        with self._lock:
            state = self._read(); state["received"] = list(state.get("received") or [])[-399:] + [record]; self._write(state)
        return dict(record)

    def convert_received(self, *, message_id: str, persona_id: str, target: str) -> Dict[str, Any]:
        if target not in {"task", "reminder", "calendar"}: raise ValueError("A message can become a task, reminder or calendar proposal")
        state = self._read(); message = next((item for item in state["received"] if item.get("message_id") == message_id and item.get("persona_id") == persona_id), None)
        if message is None: raise PermissionError("That private message is unavailable")
        if target == "task":
            return self.inbox.create_task(requester_persona_id=persona_id, owner_persona_id=persona_id, title=str(message["summary"]), source={"surface": "communication", "message_id": message_id})
        if target == "reminder":
            return {"kind": "reminder_proposal", "status": "needs_private_time", "persona_id": persona_id, "title": str(message["summary"]), "source_message_id": message_id, "external_effect": False}
        return {"kind": "calendar_proposal", "status": "needs_private_date", "persona_id": persona_id, "title": str(message["summary"]), "source_message_id": message_id, "external_effect": False}

    def create_invitation(self, *, draft_id: str, persona_id: str, public_base_url: str) -> Dict[str, Any]:
        """Create a bearer invitation containing one exact request and no household projection."""
        base = str(public_base_url).rstrip("/")
        if not re.fullmatch(r"https://[^\s]{3,300}", base):
            raise ValueError("Invitation links require a public HTTPS origin")
        with self._lock:
            state = self._read()
            draft = next((item for item in state.get("drafts", []) if item.get("draft_id") == draft_id and item.get("persona_id") == persona_id), None)
            if draft is None:
                raise PermissionError("That exact request is unavailable")
            previous = next((item for item in state.get("invitations", []) if item.get("draft_id") == draft_id and item.get("status") == "active"), None)
            if previous:
                return {key: value for key, value in previous.items() if key != "token_hash"}
            token = secrets.token_urlsafe(32)
            invitation = {
                "invitation_id": f"pilot_invitation_{uuid4().hex}", "persona_id": persona_id,
                "draft_id": draft_id, "token_hash": canonical_hash(token),
                "url": f"{base}/v1/public/invitations/{token}", "channel": draft["channel"],
                "recipient_name": draft["recipient_name"], "request_title": draft.get("subject") or "Pilot request",
                "request_summary": self._text(draft.get("body"), 500), "status": "active",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "created_at": utc_now_iso(), "unrelated_household_data_included": False,
            }
            state["invitations"] = list(state.get("invitations") or [])[-199:] + [invitation]
            self._write(state)
            return {key: value for key, value in invitation.items() if key != "token_hash"}

    def inspect_invitation(self, token: str) -> Dict[str, Any]:
        token_hash = canonical_hash(str(token))
        invitation = next((item for item in self._read().get("invitations", []) if secrets.compare_digest(str(item.get("token_hash") or ""), token_hash)), None)
        if invitation is None or invitation.get("status") != "active" or datetime.fromisoformat(str(invitation["expires_at"])) <= datetime.now(timezone.utc):
            raise PermissionError("This Pilot invitation is invalid or expired")
        return {key: value for key, value in invitation.items() if key not in {"token_hash", "persona_id", "draft_id"}}

    def claim_invitation(self, *, token: str, recipient_persona_id: str) -> Dict[str, Any]:
        self._profile(recipient_persona_id)
        token_hash = canonical_hash(str(token))
        with self._lock:
            state = self._read()
            invitation = next((item for item in state.get("invitations", []) if secrets.compare_digest(str(item.get("token_hash") or ""), token_hash)), None)
            if invitation is None or invitation.get("status") != "active" or datetime.fromisoformat(str(invitation["expires_at"])) <= datetime.now(timezone.utc):
                raise PermissionError("This Pilot invitation is invalid or expired")
            invitation.update({"status": "claimed", "claimed_by_persona_id": recipient_persona_id, "claimed_at": utc_now_iso()})
            self._write(state)
            return {"invitation_id": invitation["invitation_id"], "status": "claimed", "request_title": invitation["request_title"], "request_summary": invitation["request_summary"], "unrelated_sender_data_included": False}

    def block_contact(self, *, persona_id: str, contact_id: str) -> Dict[str, Any]:
        self._profile(persona_id)
        with self._lock:
            state = self._read()
            record = next((item for item in state.get("blocks", []) if item.get("persona_id") == persona_id and item.get("contact_id") == contact_id), None)
            if record is None:
                record = {"block_id": f"communication_block_{uuid4().hex}", "persona_id": persona_id, "contact_id": contact_id, "status": "active", "created_at": utc_now_iso()}
                state["blocks"] = list(state.get("blocks") or [])[-499:] + [record]
            else:
                record["status"] = "active"
            self._write(state)
            return dict(record)

    def report_contact(self, *, persona_id: str, contact_id: str, category: str) -> Dict[str, Any]:
        self._profile(persona_id)
        clean_category = self._text(category, 80)
        if clean_category not in {"spam", "harassment", "unsafe", "other"}:
            raise ValueError("Choose a supported report category")
        with self._lock:
            state = self._read()
            record = {"report_id": f"communication_report_{uuid4().hex}", "persona_id": persona_id, "contact_id": contact_id, "category": clean_category, "status": "recorded_locally", "created_at": utc_now_iso(), "provider_report_claimed": False}
            state["reports"] = list(state.get("reports") or [])[-499:] + [record]
            self._write(state)
            return dict(record)

    def convert_received_mobile(
        self, *, message_id: str, persona_id: str, target: str, idempotency_key: str,
    ) -> Dict[str, Any]:
        if len(str(idempotency_key)) < 8:
            raise ValueError("A communication conversion key is required")
        request_hash = canonical_hash({"message_id": message_id, "persona_id": persona_id, "target": target})
        with self._lock:
            state = self._read()
            previous = next((item for item in state.get("mobile_requests", []) if item.get("persona_id") == persona_id and item.get("idempotency_key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash or previous.get("operation") != "communication.convert":
                    raise PermissionError("That communication conversion key was reused for different content")
                return dict(previous.get("result") or {})
            result = self.convert_received(message_id=message_id, persona_id=persona_id, target=target)
            state = self._read()
            state.setdefault("mobile_requests", []).append({
                "persona_id": persona_id, "idempotency_key": str(idempotency_key)[:160],
                "request_hash": request_hash, "operation": "communication.convert", "result": result,
            })
            state["mobile_requests"] = state["mobile_requests"][-2048:]
            self._write(state)
            return result

    def schedule_no_reply_follow_up(self, *, draft_id: str, persona_id: str, due_at: str) -> Dict[str, Any]:
        due = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
        state = self._read(); draft = next((item for item in state["drafts"] if item.get("draft_id") == draft_id and item.get("persona_id") == persona_id), None)
        if draft is None or draft.get("status") not in {"provider_accepted", "delivered"}: raise PermissionError("A verified provider-accepted message is required")
        follow_up = {"follow_up_id": f"follow_up_{uuid4().hex}", "draft_id": draft_id, "persona_id": persona_id, "due_at": due.isoformat(), "condition": "no_verified_reply", "status": "scheduled", "created_at": utc_now_iso()}
        with self._lock:
            state = self._read(); state["follow_ups"] = list(state.get("follow_ups") or [])[-199:] + [follow_up]; self._write(state)
        return dict(follow_up)

    def schedule_mobile_follow_up(
        self, *, draft_id: str, persona_id: str, due_at: str, idempotency_key: str,
    ) -> Dict[str, Any]:
        if len(str(idempotency_key)) < 8:
            raise ValueError("A communication follow-up key is required")
        request_hash = canonical_hash({"draft_id": draft_id, "persona_id": persona_id, "due_at": due_at})
        with self._lock:
            state = self._read()
            previous = next((item for item in state.get("mobile_requests", []) if item.get("persona_id") == persona_id and item.get("idempotency_key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash or previous.get("operation") != "communication.followup":
                    raise PermissionError("That communication follow-up key was reused for different content")
                result = next((item for item in state.get("follow_ups", []) if item.get("follow_up_id") == previous.get("object_id")), None)
                if result is None:
                    raise RuntimeError("Pilot cannot reconcile that earlier communication follow-up")
                return dict(result)
            result = self.schedule_no_reply_follow_up(draft_id=draft_id, persona_id=persona_id, due_at=due_at)
            state = self._read()
            state.setdefault("mobile_requests", []).append({
                "persona_id": persona_id, "idempotency_key": str(idempotency_key)[:160],
                "request_hash": request_hash, "operation": "communication.followup",
                "object_id": result["follow_up_id"],
            })
            state["mobile_requests"] = state["mobile_requests"][-2048:]
            self._write(state)
            return result

    def prepare_call(self, *, persona_id: str, contact_id: str) -> Dict[str, Any]:
        self._profile(persona_id); state_inbox = self.inbox._read()
        contact = next((item for item in state_inbox.get("contacts", []) if item.get("contact_id") == contact_id and item.get("owner_persona_id") == persona_id and item.get("status", "active") == "active"), None)
        if contact is None or not contact.get("whatsapp"): raise ValueError("That contact has no privately stored phone route")
        call = {"call_id": f"call_{uuid4().hex}", "persona_id": persona_id, "contact_id": contact_id, "recipient_name": contact["display_name"], "phone_reference": contact["whatsapp"], "status": "prepared_not_placed", "explicit_phone_tap_required": True, "created_at": utc_now_iso()}
        with self._lock:
            state = self._read(); state["call_preparations"] = list(state.get("call_preparations") or [])[-99:] + [call]; self._write(state)
        return dict(call)

    def prepare_mobile_call(
        self, *, persona_id: str, contact_id: str, idempotency_key: str,
    ) -> Dict[str, Any]:
        if len(str(idempotency_key)) < 8:
            raise ValueError("A call preparation key is required")
        request_hash = canonical_hash({"persona_id": persona_id, "contact_id": contact_id})
        with self._lock:
            state = self._read()
            previous = next((item for item in state.get("mobile_requests", []) if item.get("persona_id") == persona_id and item.get("idempotency_key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash or previous.get("operation") != "communication.call":
                    raise PermissionError("That call preparation key was reused for a different contact")
                result = next((item for item in state.get("call_preparations", []) if item.get("call_id") == previous.get("object_id")), None)
                if result is None:
                    raise RuntimeError("Pilot cannot reconcile that earlier call preparation")
                return dict(result)
            result = self.prepare_call(persona_id=persona_id, contact_id=contact_id)
            state = self._read()
            state.setdefault("mobile_requests", []).append({
                "persona_id": persona_id, "idempotency_key": str(idempotency_key)[:160],
                "request_hash": request_hash, "operation": "communication.call",
                "object_id": result["call_id"],
            })
            state["mobile_requests"] = state["mobile_requests"][-2048:]
            self._write(state)
            return result

    def snapshot(self, *, persona_id: str) -> Dict[str, Any]:
        self._profile(persona_id); state = self._read()
        return {key: [dict(item) for item in state.get(key, []) if item.get("persona_id") == persona_id] for key in ("drafts", "received", "follow_ups", "receipts", "call_preparations", "invitations", "blocks", "reports")}
