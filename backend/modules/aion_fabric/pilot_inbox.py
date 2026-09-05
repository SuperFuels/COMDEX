from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .private_identity import ProductionPrivateIdentity


class PilotInbox:
    """Persona-private agent inbox, tasks, lists, delegation and reminders."""

    REMINDER_TRIGGERS = {"time", "arrival", "departure", "journey", "closing_time"}
    LIST_SCOPES = {"private", "household_shared"}

    def __init__(self, runtime_dir: str | Path, *, identities: ProductionPrivateIdentity | None = None) -> None:
        self.root = Path(runtime_dir) / "pilot_inbox"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.identities = identities or ProductionPrivateIdentity(runtime_dir)
        self.adapters: Dict[str, Callable[[Dict[str, Any], str], Dict[str, Any]]] = {}
        self._mobile_lock = threading.RLock()

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {"schema_version": "pilot.inbox.v1", "lists": [], "tasks": [], "messages": [], "reminders": [], "contacts": [], "external_deliveries": [], "route_suggestions": [], "provider_receipts": [], "mobile_requests": []}

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

    def _known(self, persona_id: str) -> Dict[str, Any]:
        profile = next((item for item in self.identities.snapshot().get("profiles", []) if item.get("persona_id") == persona_id and item.get("status") == "active"), None)
        if profile is None:
            raise PermissionError("A production private identity is required")
        return profile

    @staticmethod
    def _clean_text(value: str, maximum: int = 500) -> str:
        return " ".join(str(value).split())[:maximum]

    def create_list(self, *, owner_persona_id: str, name: str, scope: str = "private") -> Dict[str, Any]:
        self._known(owner_persona_id)
        if scope not in self.LIST_SCOPES:
            raise ValueError("List scope must be private or household_shared")
        clean_name = self._clean_text(name, 100)
        if len(clean_name) < 2:
            raise ValueError("List name is required")
        record = {"list_id": f"list_{uuid4().hex}", "owner_persona_id": owner_persona_id, "name": clean_name, "scope": scope, "created_at": utc_now_iso()}
        record["record_hash"] = canonical_hash(record)
        state = self._read()
        state["lists"].append(record)
        self._write(state)
        return record

    def create_task(
        self,
        *,
        requester_persona_id: str,
        owner_persona_id: str,
        title: str,
        assignee_persona_id: str | None = None,
        list_id: str | None = None,
        notes: str = "",
        source: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._known(requester_persona_id)
        self._known(owner_persona_id)
        assignee = assignee_persona_id or owner_persona_id
        self._known(assignee)
        if requester_persona_id != owner_persona_id:
            raise PermissionError("One identity cannot create inside another person's private list")
        state = self._read()
        target_list = None
        if list_id:
            target_list = next((item for item in state.get("lists", []) if item.get("list_id") == list_id), None)
            if target_list is None or target_list.get("owner_persona_id") != owner_persona_id:
                raise PermissionError("The selected list does not belong to this identity")
        clean_title = self._clean_text(title, 240)
        if len(clean_title) < 2:
            raise ValueError("Task title is required")
        cross_person = assignee != owner_persona_id
        task = {
            "task_id": f"task_{uuid4().hex}", "owner_persona_id": owner_persona_id,
            "requester_persona_id": requester_persona_id, "assignee_persona_id": assignee,
            "list_id": list_id, "list_scope": str((target_list or {}).get("scope") or "private"),
            "title": clean_title, "notes": self._clean_text(notes, 1000),
            "status": "awaiting_recipient_acceptance" if cross_person else "open",
            "recipient_acceptance_required": cross_person, "recipient_accepted_at": None,
            "source": dict(source or {}), "created_at": utc_now_iso(), "completed_at": None,
            "continuation_surfaces": ["private_phone", "shared_tv_summary", "authorized_car"],
        }
        task["record_hash"] = canonical_hash(task)
        state["tasks"].append(task)
        if cross_person:
            state["messages"].append(self._message_record(
                sender=requester_persona_id, recipient=assignee,
                body=f"Task request: {clean_title}", kind="task_request", object_id=task["task_id"],
            ))
        self._write(state)
        return task

    def import_pilot_delegation(
        self,
        *,
        recipient_persona_id: str,
        sender_persona_id: str,
        title: str,
        external_task_ref: str,
        source_receipt_hash: str,
    ) -> Dict[str, Any]:
        """Import one verified inter-mother proposal without trusting a remote persona locally."""
        self._known(recipient_persona_id)
        clean_title = self._clean_text(title, 240)
        external_task_ref = self._clean_text(external_task_ref, 200)
        if len(clean_title) < 2 or len(external_task_ref) < 3:
            raise ValueError("The incoming Pilot task is incomplete")
        if not re.fullmatch(r"[0-9a-f]{64}", str(source_receipt_hash)):
            raise ValueError("The incoming Pilot task requires a verified source hash")
        state = self._read()
        existing = next(
            (item for item in state.get("tasks", []) if item.get("external_task_ref") == external_task_ref),
            None,
        )
        if existing:
            if existing.get("assignee_persona_id") != recipient_persona_id:
                raise PermissionError("That incoming task belongs to another identity")
            return dict(existing)
        task = {
            "task_id": f"task_{uuid4().hex}",
            "owner_persona_id": recipient_persona_id,
            "requester_persona_id": self._clean_text(sender_persona_id, 200),
            "assignee_persona_id": recipient_persona_id,
            "list_id": None,
            "list_scope": "private",
            "title": clean_title,
            "notes": "",
            "status": "awaiting_recipient_acceptance",
            "recipient_acceptance_required": True,
            "recipient_accepted_at": None,
            "external_task_ref": external_task_ref,
            "source": {
                "surface": "pilot_to_pilot",
                "verified_transport": True,
                "source_receipt_hash": source_receipt_hash,
            },
            "created_at": utc_now_iso(),
            "completed_at": None,
            "continuation_surfaces": ["private_phone", "shared_tv_summary", "authorized_car"],
        }
        task["record_hash"] = canonical_hash(task)
        state.setdefault("tasks", []).append(task)
        state.setdefault("messages", []).append(self._message_record(
            sender=sender_persona_id,
            recipient=recipient_persona_id,
            body=f"Task request: {clean_title}",
            kind="task_request",
            object_id=task["task_id"],
        ))
        self._write(state)
        return dict(task)

    @staticmethod
    def _message_record(*, sender: str, recipient: str, body: str, kind: str = "direct", object_id: str = "") -> Dict[str, Any]:
        record = {
            "message_id": f"message_{uuid4().hex}", "sender_persona_id": sender,
            "recipient_persona_id": recipient, "body": " ".join(str(body).split())[:2000],
            "kind": kind, "object_id": object_id or None, "status": "delivered_to_pilot_inbox",
            "created_at": utc_now_iso(), "read_at": None,
        }
        record["record_hash"] = canonical_hash(record)
        return record

    def send_message(self, *, sender_persona_id: str, recipient_persona_id: str, body: str) -> Dict[str, Any]:
        self._known(sender_persona_id)
        self._known(recipient_persona_id)
        clean = self._clean_text(body, 2000)
        if not clean:
            raise ValueError("Message body is required")
        record = self._message_record(sender=sender_persona_id, recipient=recipient_persona_id, body=clean)
        state = self._read()
        state["messages"].append(record)
        state["messages"] = state["messages"][-2000:]
        self._write(state)
        return record

    def prepare_external_message(self, *, sender_persona_id: str, channel: str, recipient_reference: str, body: str) -> Dict[str, Any]:
        self._known(sender_persona_id)
        if channel not in {"email", "whatsapp", "sms"}:
            raise ValueError("Unsupported external message handoff")
        clean_body = self._clean_text(body, 2000)
        clean_recipient = self._clean_text(recipient_reference, 180)
        if not clean_body or not clean_recipient:
            raise ValueError("Recipient and message are required")
        return {
            "proposal_id": f"external_message_{uuid4().hex}", "sender_persona_id": sender_persona_id,
            "channel": channel, "recipient_reference": clean_recipient, "body": clean_body,
            "status": "prepared_not_sent", "private_approval_required": True,
            "authorized_delivery_adapter_required": True, "created_at": utc_now_iso(),
        }

    def save_contact(
        self, *, owner_persona_id: str, display_name: str, email: str = "",
        whatsapp: str = "", sms: str = "", pilot_persona_id: str = "", pilot_mother_id: str = "",
        preferred_route: str = "", contact_id: str = "",
    ) -> Dict[str, Any]:
        self._known(owner_persona_id)
        name = self._clean_text(display_name, 100)
        email = self._clean_text(email, 180).lower()
        whatsapp = re.sub(r"[^+0-9]", "", self._clean_text(whatsapp, 40))
        sms = re.sub(r"[^+0-9]", "", self._clean_text(sms, 40))
        pilot_persona_id = self._clean_text(pilot_persona_id, 100)
        pilot_mother_id = self._clean_text(pilot_mother_id, 200)
        if len(name) < 2:
            raise ValueError("Contact name is required")
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Enter a valid email address")
        if whatsapp and not re.fullmatch(r"\+?[0-9]{7,15}", whatsapp):
            raise ValueError("Enter a WhatsApp number including its country code")
        if sms and not re.fullmatch(r"\+[1-9][0-9]{6,14}", sms):
            raise ValueError("Enter an SMS number in international E.164 format")
        if pilot_persona_id:
            if pilot_mother_id:
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,199}", pilot_mother_id):
                    raise ValueError("Pilot mother identity is invalid")
            else:
                self._known(pilot_persona_id)
        routes = [route for route, value in (("pilot", pilot_persona_id), ("whatsapp", whatsapp), ("sms", sms), ("email", email)) if value]
        if not routes:
            raise ValueError("Add a Pilot identity, WhatsApp number, or email address")
        if preferred_route not in routes:
            preferred_route = routes[0]
        state = self._read()
        contacts = state.setdefault("contacts", [])
        record = next((item for item in contacts if item.get("contact_id") == contact_id and item.get("owner_persona_id") == owner_persona_id), None) if contact_id else None
        if contact_id and record is None:
            raise PermissionError("That contact does not belong to this identity")
        if record is None:
            record = next((item for item in contacts if item.get("owner_persona_id") == owner_persona_id and item.get("status", "active") == "active" and str(item.get("display_name") or "").casefold() == name.casefold()), None)
        values = {
            "owner_persona_id": owner_persona_id, "display_name": name, "email": email,
            "whatsapp": whatsapp, "sms": sms, "pilot_persona_id": pilot_persona_id,
            "pilot_mother_id": pilot_mother_id,
            "preferred_route": preferred_route, "status": "active", "removed_at": None,
            "updated_at": utc_now_iso(),
        }
        if record is None:
            record = {"contact_id": f"contact_{uuid4().hex}", "created_at": utc_now_iso(), **values}
            contacts.append(record)
        else:
            record.update(values)
        record.pop("record_hash", None)
        record["record_hash"] = canonical_hash(record)
        self._write(state)
        return dict(record)

    def find_contacts(self, *, owner_persona_id: str, display_name: str) -> list[Dict[str, Any]]:
        self._known(owner_persona_id)
        wanted = self._clean_text(display_name, 100).casefold()
        state = self._read()
        return [dict(item) for item in state.get("contacts", []) if item.get("owner_persona_id") == owner_persona_id and item.get("status", "active") == "active" and str(item.get("display_name") or "").casefold() == wanted]

    def search_contacts(self, *, owner_persona_id: str, query: str = "") -> list[Dict[str, Any]]:
        self._known(owner_persona_id)
        wanted = self._clean_text(query, 100).casefold()
        contacts = [dict(item) for item in self._read().get("contacts", []) if item.get("owner_persona_id") == owner_persona_id and item.get("status", "active") == "active"]
        if wanted:
            contacts = [item for item in contacts if wanted in str(item.get("display_name") or "").casefold()]
        contacts.sort(key=lambda item: (0 if str(item.get("display_name") or "").casefold() == wanted else 1, str(item.get("display_name") or "").casefold()))
        return contacts[:100]

    @staticmethod
    def _spoken_name_key(value: str) -> str:
        """Return a small English phonetic key for private contact resolution."""
        letters = re.sub(r"[^a-z]", "", str(value).casefold())
        if not letters:
            return ""
        first = letters[0]
        groups = {
            **{letter: "1" for letter in "bfpv"},
            **{letter: "2" for letter in "cgjkqsxz"},
            **{letter: "3" for letter in "dt"},
            "l": "4",
            **{letter: "5" for letter in "mn"},
            "r": "6",
        }
        tail: list[str] = []
        previous = groups.get(first, "")
        for letter in letters[1:]:
            code = groups.get(letter, "")
            if code and code != previous:
                tail.append(code)
            previous = code
        return (first.upper() + "".join(tail) + "000")[:4]

    def resolve_spoken_contacts(self, *, owner_persona_id: str, display_name: str) -> list[Dict[str, Any]]:
        """Resolve an exact or uniquely phonetic contact name for noisy local ASR.

        More than one phonetic match is deliberately returned as ambiguous so
        the caller can fail closed and ask the person to choose privately.
        """
        exact = self.find_contacts(owner_persona_id=owner_persona_id, display_name=display_name)
        if exact:
            return exact
        phrase = self._clean_text(display_name, 100).casefold()
        tokens = [token for token in re.findall(r"[a-z]+", phrase) if token not in {"in", "at", "to", "the"}]
        variants = set(tokens)
        # Whisper commonly emits "backup" for the name "Becca". Treat the
        # acoustic suffix as a variant, but only accept one unique contact.
        variants.update(token[:-2] for token in tokens if token.endswith("up") and len(token) > 4)
        keys = {self._spoken_name_key(token) for token in variants} - {""}
        state = self._read()
        matches = []
        for item in state.get("contacts", []):
            if item.get("owner_persona_id") != owner_persona_id:
                continue
            if item.get("status", "active") != "active":
                continue
            name_token = next(iter(re.findall(r"[a-z]+", str(item.get("display_name") or "").casefold())), "")
            if self._spoken_name_key(name_token) in keys:
                matches.append(dict(item))
        return matches

    def save_mobile_contact(
        self, *, owner_persona_id: str, display_name: str, email: str = "",
        whatsapp: str = "", sms: str = "", pilot_persona_id: str = "", pilot_mother_id: str = "",
        preferred_route: str = "", contact_id: str = "", idempotency_key: str,
    ) -> Dict[str, Any]:
        if len(str(idempotency_key)) < 8:
            raise ValueError("A contact request key is required")
        request_scope = {
            "owner_persona_id": owner_persona_id, "contact_id": contact_id,
            "display_name": display_name, "email": email, "whatsapp": whatsapp, "sms": sms,
            "pilot_persona_id": pilot_persona_id, "pilot_mother_id": pilot_mother_id,
            "preferred_route": preferred_route,
        }
        request_hash = canonical_hash(request_scope)
        with self._mobile_lock:
            state = self._read()
            previous = next((item for item in state.get("mobile_requests", []) if item.get("persona_id") == owner_persona_id and item.get("idempotency_key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash:
                    raise PermissionError("That contact request key was reused for different content")
                record = next((item for item in state.get("contacts", []) if item.get("contact_id") == previous.get("object_id")), None)
                if record is None: raise RuntimeError("Pilot cannot reconcile that earlier contact request")
                return dict(record)
            record = self.save_contact(
                owner_persona_id=owner_persona_id, contact_id=contact_id,
                display_name=display_name, email=email, whatsapp=whatsapp, sms=sms,
                pilot_persona_id=pilot_persona_id, pilot_mother_id=pilot_mother_id,
                preferred_route=preferred_route,
            )
            state = self._read()
            state.setdefault("mobile_requests", []).append({
                "persona_id": owner_persona_id, "idempotency_key": str(idempotency_key)[:160],
                "request_hash": request_hash, "object_id": record["contact_id"], "operation": "contact.save",
            })
            state["mobile_requests"] = state["mobile_requests"][-2048:]
            self._write(state)
            return record

    def remove_mobile_contact(self, *, owner_persona_id: str, contact_id: str, idempotency_key: str) -> Dict[str, Any]:
        self._known(owner_persona_id)
        if len(str(idempotency_key)) < 8: raise ValueError("A contact request key is required")
        request_hash = canonical_hash({"owner_persona_id": owner_persona_id, "contact_id": contact_id, "operation": "remove"})
        with self._mobile_lock:
            state = self._read()
            previous = next((item for item in state.get("mobile_requests", []) if item.get("persona_id") == owner_persona_id and item.get("idempotency_key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash: raise PermissionError("That contact request key was reused for different content")
                return {"contact_id": contact_id, "status": "removed", "already_applied": True}
            record = next((item for item in state.get("contacts", []) if item.get("contact_id") == contact_id and item.get("owner_persona_id") == owner_persona_id), None)
            if record is None: raise PermissionError("That contact does not belong to this identity")
            record["status"] = "removed"; record["removed_at"] = utc_now_iso(); record.pop("record_hash", None); record["record_hash"] = canonical_hash(record)
            state.setdefault("mobile_requests", []).append({
                "persona_id": owner_persona_id, "idempotency_key": str(idempotency_key)[:160],
                "request_hash": request_hash, "object_id": contact_id, "operation": "contact.remove",
            })
            state["mobile_requests"] = state["mobile_requests"][-2048:]; self._write(state)
            return {"contact_id": contact_id, "status": "removed", "already_applied": False}

    def prepare_external_task(self, *, sender_persona_id: str, contact_id: str, title: str) -> Dict[str, Any]:
        self._known(sender_persona_id)
        state = self._read()
        contact = next((item for item in state.get("contacts", []) if item.get("contact_id") == contact_id and item.get("owner_persona_id") == sender_persona_id), None)
        if contact is None:
            raise PermissionError("That contact does not belong to this identity")
        channel = str(contact.get("preferred_route") or "")
        if channel not in {"email", "whatsapp"}:
            raise ValueError("This contact needs an external email or WhatsApp route")
        clean_title = self._clean_text(title, 240)
        if len(clean_title) < 2:
            raise ValueError("Task title is required")
        task = {
            "task_id": f"task_{uuid4().hex}", "owner_persona_id": sender_persona_id,
            "requester_persona_id": sender_persona_id, "assignee_persona_id": None,
            "external_contact_id": contact_id, "title": clean_title, "notes": "",
            "status": "pending_external_delivery_approval", "recipient_acceptance_required": True,
            "source": {"surface": "shared_tv", "explicit_voice": True}, "created_at": utc_now_iso(),
            "completed_at": None, "continuation_surfaces": ["private_phone"],
        }
        task["record_hash"] = canonical_hash(task)
        proposal = {
            "proposal_id": f"external_task_{uuid4().hex}", "task_id": task["task_id"],
            "sender_persona_id": sender_persona_id, "contact_id": contact_id,
            "recipient_name": str(contact.get("display_name") or "Contact"), "channel": channel,
            "recipient_reference": str(contact.get(channel) or ""), "body": clean_title,
            "status": "prepared_not_sent", "private_approval_required": True,
            "authorized_delivery_adapter_required": True, "created_at": utc_now_iso(),
        }
        state.setdefault("tasks", []).append(task)
        state.setdefault("external_deliveries", []).append(proposal)
        self._write(state)
        return dict(proposal)

    def approve_external_delivery(self, *, proposal_id: str, persona_id: str) -> Dict[str, Any]:
        state = self._read()
        proposal = next((item for item in state.get("external_deliveries", []) if item.get("proposal_id") == proposal_id and item.get("sender_persona_id") == persona_id), None)
        if proposal is None:
            raise PermissionError("No prepared delivery belongs to this identity")
        if proposal.get("status") != "prepared_not_sent":
            raise ValueError("This delivery is no longer waiting for approval")
        proposal["status"] = "approved_pending_adapter"
        proposal["approved_at"] = utc_now_iso()
        task = next((item for item in state.get("tasks", []) if item.get("task_id") == proposal.get("task_id")), None)
        if task:
            task["status"] = "awaiting_external_delivery_adapter"
        self._write(state)
        return dict(proposal)

    def respond_to_delegation(self, *, task_id: str, recipient_persona_id: str, accept: bool) -> Dict[str, Any]:
        state = self._read()
        task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id and item.get("assignee_persona_id") == recipient_persona_id), None)
        if task is None or task.get("status") != "awaiting_recipient_acceptance":
            raise PermissionError("No task delegation is waiting for this recipient")
        task["status"] = "open" if accept else "declined"
        task["recipient_accepted_at"] = utc_now_iso() if accept else None
        task["recipient_declined_at"] = None if accept else utc_now_iso()
        self._write(state)
        return dict(task)

    def complete(self, *, task_id: str, actor_persona_id: str) -> Dict[str, Any]:
        state = self._read()
        task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id), None)
        if task is None or actor_persona_id not in {task.get("owner_persona_id"), task.get("assignee_persona_id")}:
            raise PermissionError("This identity cannot complete that task")
        if task.get("status") not in {"open", "snoozed"}:
            raise ValueError("Only an accepted task can be completed")
        task["status"] = "completed"
        task["completed_at"] = utc_now_iso()
        task["completed_by_persona_id"] = actor_persona_id
        self._write(state)
        return dict(task)

    def revise_title(self, *, task_id: str, actor_persona_id: str, title: str) -> Dict[str, Any]:
        state = self._read()
        task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id), None)
        if task is None or actor_persona_id not in {task.get("owner_persona_id"), task.get("requester_persona_id")}:
            raise PermissionError("This identity cannot correct that task")
        if task.get("status") in {"completed", "cancelled", "declined"}:
            raise ValueError("That task can no longer be corrected")
        clean_title = self._clean_text(title, 240)
        if len(clean_title) < 2:
            raise ValueError("Task title is required")
        task["title"] = clean_title
        task["corrected_at"] = utc_now_iso()
        task["record_hash"] = canonical_hash({key: value for key, value in task.items() if key != "record_hash"})
        self._write(state)
        return dict(task)

    def cancel(self, *, task_id: str, actor_persona_id: str) -> Dict[str, Any]:
        state = self._read()
        task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id), None)
        if task is None or actor_persona_id not in {task.get("owner_persona_id"), task.get("requester_persona_id"), task.get("assignee_persona_id")}:
            raise PermissionError("This identity cannot cancel that task")
        if task.get("status") in {"completed", "cancelled", "declined"}:
            raise ValueError("That task is already closed")
        task["status"] = "cancelled"
        task["cancelled_at"] = utc_now_iso()
        task["cancelled_by_persona_id"] = actor_persona_id
        self._write(state)
        return dict(task)

    def snooze(self, *, task_id: str, actor_persona_id: str, until: str) -> Dict[str, Any]:
        state = self._read()
        task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id and actor_persona_id in {item.get("owner_persona_id"), item.get("assignee_persona_id")}), None)
        if task is None:
            raise PermissionError("This identity cannot snooze that task")
        when = datetime.fromisoformat(str(until).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when <= datetime.now(timezone.utc):
            raise ValueError("Snooze time must be in the future")
        task["snoozed_until"] = when.isoformat()
        task["status"] = "snoozed"
        self._write(state)
        return dict(task)

    def add_reminder(
        self,
        *,
        persona_id: str,
        task_id: str,
        trigger: str,
        at: str | None = None,
        location_label: str = "",
        repetition: str = "none",
        location_permission_id: str | None = None,
    ) -> Dict[str, Any]:
        self._known(persona_id)
        if trigger not in self.REMINDER_TRIGGERS:
            raise ValueError("Unsupported reminder trigger")
        state = self._read()
        task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id and persona_id in {item.get("owner_persona_id"), item.get("assignee_persona_id")}), None)
        if task is None:
            raise PermissionError("Reminder task does not belong to this identity")
        when = None
        if trigger in {"time", "journey", "closing_time"}:
            when_value = datetime.fromisoformat(str(at or "").replace("Z", "+00:00"))
            if when_value.tzinfo is None:
                when_value = when_value.replace(tzinfo=timezone.utc)
            if when_value <= datetime.now(timezone.utc):
                raise ValueError("Reminder time must be in the future")
            when = when_value.isoformat()
        if trigger in {"arrival", "departure", "journey"} and not location_permission_id:
            raise PermissionError("Location reminders require explicit location permission")
        reminder = {
            "reminder_id": f"reminder_{uuid4().hex}", "persona_id": persona_id,
            "task_id": task_id, "trigger": trigger, "at": when,
            "location_label": self._clean_text(location_label, 160),
            "location_permission_id": str(location_permission_id or "") or None,
            "repetition": re.sub(r"[^a-z0-9_ -]+", "", str(repetition).lower())[:80],
            "status": "scheduled", "created_at": utc_now_iso(), "raw_location_history_retained": False,
        }
        reminder["record_hash"] = canonical_hash(reminder)
        state["reminders"].append(reminder)
        self._write(state)
        return reminder

    def create_mobile_reminder(
        self,
        *,
        persona_id: str,
        task_id: str,
        trigger: str,
        at: str | None,
        location_label: str,
        repetition: str,
        location_permission_id: str | None,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Create one reminder atomically for a signed mobile request."""
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,159}", str(idempotency_key or "")):
            raise ValueError("A valid reminder request key is required")
        request_scope = {
            "persona_id": persona_id, "task_id": task_id, "trigger": trigger, "at": at,
            "location_label": location_label, "repetition": repetition,
            "location_permission_id": location_permission_id,
        }
        request_hash = canonical_hash(request_scope)
        with self._mobile_lock:
            state = self._read()
            previous = next((item for item in state.get("mobile_requests", []) if item.get("idempotency_key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash:
                    raise PermissionError("That reminder request key was reused for different content")
                reminder = next((item for item in state.get("reminders", []) if item.get("reminder_id") == previous.get("object_id")), None)
                if reminder is None:
                    raise RuntimeError("Pilot cannot reconcile that earlier reminder request")
                return dict(reminder)
            self._known(persona_id)
            if trigger not in self.REMINDER_TRIGGERS:
                raise ValueError("Unsupported reminder trigger")
            repetition = str(repetition or "none").lower()
            if repetition not in {"none", "daily", "weekly", "weekdays"}:
                raise ValueError("Choose once, daily, weekdays or weekly")
            if repetition != "none" and trigger not in {"time", "closing_time"}:
                raise ValueError("Repeating reminders currently require an exact time")
            task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id and persona_id in {item.get("owner_persona_id"), item.get("assignee_persona_id")}), None)
            if task is None:
                raise PermissionError("Reminder task does not belong to this identity")
            when = None
            if trigger in {"time", "journey", "closing_time"}:
                when_value = datetime.fromisoformat(str(at or "").replace("Z", "+00:00"))
                if when_value.tzinfo is None:
                    when_value = when_value.replace(tzinfo=timezone.utc)
                if when_value <= datetime.now(timezone.utc):
                    raise ValueError("Reminder time must be in the future")
                when = when_value.isoformat()
            if trigger in {"arrival", "departure", "journey"} and not location_permission_id:
                raise PermissionError("Location reminders require explicit location permission")
            reminder = {
                "reminder_id": f"reminder_{uuid4().hex}", "persona_id": persona_id,
                "task_id": task_id, "trigger": trigger, "at": when,
                "location_label": self._clean_text(location_label, 160),
                "location_permission_id": str(location_permission_id or "") or None,
                "repetition": repetition,
                "status": "scheduled", "created_at": utc_now_iso(), "raw_location_history_retained": False,
                "source": "signed_mobile_request",
            }
            reminder["record_hash"] = canonical_hash(reminder)
            state.setdefault("reminders", []).append(reminder)
            state.setdefault("mobile_requests", []).append({
                "idempotency_key": idempotency_key, "request_hash": request_hash,
                "object_id": reminder["reminder_id"], "operation": "reminder.create",
            })
            state["mobile_requests"] = state["mobile_requests"][-2048:]
            self._write(state)
            return dict(reminder)

    def transition_mobile_reminder(
        self,
        *,
        persona_id: str,
        reminder_id: str,
        operation: str,
        until: str | None,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        if operation not in {"snooze", "complete", "cancel"}:
            raise ValueError("Choose a supported reminder action")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,159}", str(idempotency_key or "")):
            raise ValueError("A valid reminder request key is required")
        request_scope = {"persona_id": persona_id, "reminder_id": reminder_id, "operation": operation, "until": until}
        request_hash = canonical_hash(request_scope)
        with self._mobile_lock:
            state = self._read()
            previous = next((item for item in state.get("mobile_requests", []) if item.get("idempotency_key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash:
                    raise PermissionError("That reminder request key was reused for different content")
                reminder = next((item for item in state.get("reminders", []) if item.get("reminder_id") == reminder_id), None)
                if reminder is None:
                    raise RuntimeError("Pilot cannot reconcile that earlier reminder request")
                return dict(reminder)
            reminder = next((item for item in state.get("reminders", []) if item.get("reminder_id") == reminder_id and item.get("persona_id") == persona_id), None)
            if reminder is None:
                raise PermissionError("That reminder belongs to a different identity")
            if reminder.get("status") in {"completed", "cancelled"}:
                raise ValueError("That reminder is already closed")
            if operation == "snooze":
                snooze_until = datetime.fromisoformat(str(until or "").replace("Z", "+00:00"))
                if snooze_until.tzinfo is None:
                    snooze_until = snooze_until.replace(tzinfo=timezone.utc)
                if snooze_until <= datetime.now(timezone.utc):
                    raise ValueError("Snooze time must be in the future")
                reminder["status"] = "snoozed"
                reminder["snoozed_until"] = snooze_until.isoformat()
            else:
                reminder["status"] = "completed" if operation == "complete" else "cancelled"
                reminder[f"{reminder['status']}_at"] = utc_now_iso()
                if operation == "complete" and reminder.get("repetition") in {"daily", "weekly", "weekdays"} and reminder.get("at"):
                    next_at = datetime.fromisoformat(str(reminder["at"]).replace("Z", "+00:00"))
                    step = timedelta(days=7 if reminder["repetition"] == "weekly" else 1)
                    next_at += step
                    while next_at <= datetime.now(timezone.utc) or (reminder["repetition"] == "weekdays" and next_at.weekday() >= 5):
                        next_at += step
                    next_reminder = {
                        **{key: value for key, value in reminder.items() if key not in {"reminder_id", "record_hash", "completed_at", "cancelled_at", "snoozed_until", "status"}},
                        "reminder_id": f"reminder_{uuid4().hex}", "at": next_at.isoformat(), "status": "scheduled",
                        "created_at": utc_now_iso(), "recurring_from": reminder_id,
                    }
                    next_reminder["record_hash"] = canonical_hash(next_reminder)
                    state["reminders"].append(next_reminder)
                    reminder["next_reminder_id"] = next_reminder["reminder_id"]
            reminder["record_hash"] = canonical_hash({key: value for key, value in reminder.items() if key != "record_hash"})
            state.setdefault("mobile_requests", []).append({
                "idempotency_key": idempotency_key, "request_hash": request_hash,
                "object_id": reminder_id, "operation": f"reminder.{operation}",
            })
            state["mobile_requests"] = state["mobile_requests"][-2048:]
            self._write(state)
            return dict(reminder)

    def suggest_route_stop(self, *, persona_id: str, task_id: str, accepted_route_id: str, reason: str) -> Dict[str, Any]:
        self._known(persona_id)
        state = self._read()
        task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id and persona_id in {item.get("owner_persona_id"), item.get("assignee_persona_id")}), None)
        if task is None:
            raise PermissionError("Route suggestion task does not belong to this identity")
        suggestion = {
            "suggestion_id": f"route_stop_{uuid4().hex}", "persona_id": persona_id,
            "task_id": task_id, "accepted_route_id": self._clean_text(accepted_route_id, 160),
            "reason": self._clean_text(reason, 300), "status": "suggested_not_added",
            "explicit_acceptance_required": True, "created_at": utc_now_iso(),
        }
        state["route_suggestions"].append(suggestion)
        self._write(state)
        return suggestion

    def accept_route_stop(self, *, suggestion_id: str, persona_id: str) -> Dict[str, Any]:
        state = self._read()
        suggestion = next((item for item in state.get("route_suggestions", []) if item.get("suggestion_id") == suggestion_id and item.get("persona_id") == persona_id), None)
        if suggestion is None:
            raise PermissionError("Route-stop suggestion does not belong to this identity")
        suggestion["status"] = "accepted_pending_authorized_car_adapter"
        suggestion["accepted_at"] = utc_now_iso()
        self._write(state)
        return dict(suggestion)

    def register_provider_adapter(self, provider: str, adapter: Callable[[Dict[str, Any], str], Dict[str, Any]]) -> None:
        self.adapters[str(provider)] = adapter

    def execute_provider_task(self, *, task_id: str, persona_id: str, provider: str, credential_reference: str) -> Dict[str, Any]:
        state = self._read()
        task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id and item.get("owner_persona_id") == persona_id), None)
        if task is None or task.get("status") not in {"open", "snoozed"}:
            raise PermissionError("Only this identity's accepted task can be synchronized")
        adapter = self.adapters.get(provider)
        if adapter is None:
            raise RuntimeError("The authorized task provider adapter is not connected")
        receipt = adapter(task, credential_reference)
        if not receipt.get("verified") or not receipt.get("external_reference"):
            raise RuntimeError("Task provider did not return a verified receipt")
        record = {"receipt_id": f"task_provider_{uuid4().hex}", "task_id": task_id, "persona_id": persona_id, "provider": provider, **receipt, "recorded_at": utc_now_iso()}
        record["record_hash"] = canonical_hash(record)
        state["provider_receipts"].append(record)
        task["provider_sync"] = {"provider": provider, "receipt_id": record["receipt_id"], "verified": True}
        self._write(state)
        return record

    def stream(self, *, persona_id: str) -> Dict[str, Any]:
        self._known(persona_id)
        state = self._read()
        tasks = [dict(item) for item in state.get("tasks", []) if persona_id in {item.get("owner_persona_id"), item.get("assignee_persona_id")}]
        messages = [dict(item) for item in state.get("messages", []) if persona_id in {item.get("sender_persona_id"), item.get("recipient_persona_id")}]
        reminders = [dict(item) for item in state.get("reminders", []) if item.get("persona_id") == persona_id]
        lists = [dict(item) for item in state.get("lists", []) if item.get("owner_persona_id") == persona_id or item.get("scope") == "household_shared"]
        contacts = [dict(item) for item in state.get("contacts", []) if item.get("owner_persona_id") == persona_id and item.get("status", "active") == "active"]
        external_deliveries = [dict(item) for item in state.get("external_deliveries", []) if item.get("sender_persona_id") == persona_id]
        return {"persona_id": persona_id, "lists": lists[-100:], "tasks": tasks[-300:], "messages": messages[-300:], "reminders": reminders[-200:], "contacts": contacts[-300:], "external_deliveries": external_deliveries[-200:], "unaccepted_tasks": len([item for item in tasks if item.get("assignee_persona_id") == persona_id and item.get("status") == "awaiting_recipient_acceptance"]), "external_messages_sent_without_approval": False}

    def shared_summary(self, *, persona_id: str) -> Dict[str, Any]:
        stream = self.stream(persona_id=persona_id)
        return {
            "persona_id": persona_id,
            "open_tasks": len([item for item in stream["tasks"] if item.get("status") == "open"]),
            "waiting_for_acceptance": stream["unaccepted_tasks"],
            "due_reminders": len([item for item in stream["reminders"] if item.get("status") == "due"]),
            "private_titles_exposed": False,
        }

    def snapshot(self, *, persona_id: str | None = None) -> Dict[str, Any]:
        state = self._read()
        if persona_id:
            return self.stream(persona_id=persona_id)
        return {
            "schema_version": state.get("schema_version", "pilot.inbox.v1"),
            "list_count": len(state.get("lists", [])), "task_count": len(state.get("tasks", [])),
            "message_count": len(state.get("messages", [])), "reminder_count": len(state.get("reminders", [])),
            "pending_recipient_acceptance": len([item for item in state.get("tasks", []) if item.get("status") == "awaiting_recipient_acceptance"]),
            "private_content_exposed": False,
        }
