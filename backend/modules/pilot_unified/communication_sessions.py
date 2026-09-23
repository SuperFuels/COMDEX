from __future__ import annotations

import json
import os
import base64
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity


SESSION_VERSION = "pilot.communication-sessions.v1"
CALL_TRANSITIONS = {
    "invited": {"ringing", "declined", "cancelled"},
    "ringing": {"answered", "declined", "cancelled"},
    "answered": {"connected", "ended"},
    "connected": {"reconnecting", "ended"},
    "reconnecting": {"connected", "ended"},
}
TERMINAL_CALL_STATES = frozenset({"declined", "cancelled", "ended"})
GROUP_ROLES = frozenset({"owner", "admin", "member", "child"})
_DTLS_FINGERPRINT = re.compile(r"^(?:[0-9A-F]{2}:){31}[0-9A-F]{2}$")


class CommunicationSessionAuthority:
    """Authenticated call signalling and privacy-scoped group state.

    Media encryption remains the responsibility of the native WebRTC stack and is
    not represented here as independently audited.
    """

    MAX_ATTACHMENT_BYTES = 1_000_000
    MAX_ACTIONS_PER_MINUTE = 60

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "pilot_communication_sessions"
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.path = self.root / "state.json"

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": SESSION_VERSION, "calls": [], "groups": [], "events": [], "blocks": [], "reports": []}
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("schema_version") != SESSION_VERSION:
            raise RuntimeError("Communication session state has an unsupported format")
        return state

    def _write(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    @staticmethod
    def _verify(persona_id: str, public_key: str, payload: dict[str, Any], signature: str) -> None:
        if payload.get("actor_persona_id") != persona_id or not DeviceIdentity.verify(public_key, canonical_bytes(payload), signature):
            raise PermissionError("Pilot could not verify the communication participant")

    def _rate(self, state: dict[str, Any], persona_id: str) -> None:
        now = datetime.now(timezone.utc)
        recent = [
            item for item in state["events"]
            if item.get("actor_persona_id") == persona_id
            and datetime.fromisoformat(item["recorded_at"]) > now - timedelta(minutes=1)
        ]
        if len(recent) >= self.MAX_ACTIONS_PER_MINUTE:
            raise PermissionError("Communication action rate limit reached")

    def create_call(self, *, caller_persona_id: str, caller_public_key: str, callee_persona_id: str) -> dict[str, Any]:
        state = self._read()
        if any(item for item in state["blocks"] if {item["owner_persona_id"], item["blocked_persona_id"]} == {caller_persona_id, callee_persona_id}):
            raise PermissionError("That contact relationship is blocked")
        call = {
            "schema_version": "pilot.call-session.v1", "call_id": f"call_{uuid4().hex}",
            "caller_persona_id": caller_persona_id, "callee_persona_id": callee_persona_id,
            "participant_keys": {caller_persona_id: caller_public_key}, "state": "invited",
            "key_epoch": 0, "negotiation_epoch": 1, "transport_epochs": [],
            "used_transport_nonces": [], "used_transition_nonces": [], "created_at": utc_now_iso(),
            "media_audit_status": "not_independently_audited",
        }
        state["calls"].append(call)
        self._write(state)
        return dict(call)

    def register_participant_key(
        self, *, call_id: str, persona_id: str, public_key: str,
        proof_payload: dict[str, Any], signature: str,
    ) -> None:
        state = self._read()
        call = next((item for item in state["calls"] if item["call_id"] == call_id), None)
        if not call or persona_id not in {call["caller_persona_id"], call["callee_persona_id"]}:
            raise PermissionError("That person is not a call participant")
        required = {"purpose", "call_id", "actor_persona_id", "nonce"}
        if set(proof_payload) != required or proof_payload.get("purpose") != "register_call_participant":
            raise ValueError("Call participant proof is malformed")
        if proof_payload.get("call_id") != call_id or proof_payload.get("actor_persona_id") != persona_id:
            raise PermissionError("Call participant proof targets another call")
        if not DeviceIdentity.verify(public_key, canonical_bytes(proof_payload), signature):
            raise PermissionError("Call participant key possession was not proved")
        call["participant_keys"][persona_id] = public_key
        self._write(state)

    def register_webrtc_transport(
        self, *, call_id: str, payload: dict[str, Any], signature: str,
    ) -> dict[str, Any]:
        required = {
            "purpose", "call_id", "actor_persona_id", "epoch", "transport_public_key",
            "dtls_fingerprint", "nonce",
        }
        if set(payload) != required or payload.get("purpose") != "register_webrtc_transport":
            raise ValueError("WebRTC transport proof is malformed")
        state = self._read()
        call = next((item for item in state["calls"] if item["call_id"] == call_id), None)
        if not call or call.get("state") in TERMINAL_CALL_STATES:
            raise PermissionError("That call cannot negotiate media")
        actor = str(payload.get("actor_persona_id") or "")
        public_key = call.get("participant_keys", {}).get(actor)
        if not public_key:
            raise PermissionError("Call participant key is not registered")
        self._verify(actor, public_key, payload, signature)
        if payload.get("call_id") != call_id or int(payload.get("epoch") or 0) != int(call.get("negotiation_epoch") or 0):
            raise PermissionError("WebRTC transport proof targets another call epoch")
        nonce = str(payload.get("nonce") or "")
        if nonce in call.get("used_transport_nonces", []):
            raise PermissionError("WebRTC transport proof replay detected")
        try:
            transport_key = base64.b64decode(str(payload["transport_public_key"]), validate=True)
        except (TypeError, ValueError):
            raise ValueError("WebRTC transport public key is invalid") from None
        if len(transport_key) != 32 or not _DTLS_FINGERPRINT.fullmatch(str(payload["dtls_fingerprint"])):
            raise ValueError("WebRTC transport identity is invalid")
        epoch = int(payload["epoch"])
        record = next((item for item in call["transport_epochs"] if item["epoch"] == epoch), None)
        if record is None:
            record = {"epoch": epoch, "participants": {}, "created_at": utc_now_iso()}
            call["transport_epochs"].append(record)
        record["participants"][actor] = {
            "transport_public_key": payload["transport_public_key"],
            "dtls_fingerprint": payload["dtls_fingerprint"],
            "proof_hash": canonical_hash(payload), "registered_at": utc_now_iso(),
        }
        call["used_transport_nonces"] = list(call.get("used_transport_nonces") or [])[-255:] + [nonce]
        expected = {call["caller_persona_id"], call["callee_persona_id"]}
        ready = set(record["participants"]) == expected
        if ready:
            record["handshake_commitment"] = canonical_hash({
                "call_id": call_id, "epoch": epoch,
                "participants": {key: record["participants"][key] for key in sorted(record["participants"])},
            })
        self._write(state)
        return {
            "call_id": call_id, "epoch": epoch, "participant_authenticated": True,
            "both_participants_ready": ready,
            "handshake_commitment": record.get("handshake_commitment"),
            "server_session_key_held": False,
        }

    def transition_call(self, *, call_id: str, payload: dict[str, Any], signature: str) -> dict[str, Any]:
        state = self._read()
        call = next((item for item in state["calls"] if item["call_id"] == call_id), None)
        if not call:
            raise KeyError("Call is not available")
        actor = str(payload.get("actor_persona_id") or "")
        if set(payload) != {"actor_persona_id", "target_state", "nonce"} or not str(payload.get("nonce") or ""):
            raise ValueError("Call transition proof is malformed")
        key = call["participant_keys"].get(actor)
        if not key:
            raise PermissionError("Call participant key is not registered")
        self._verify(actor, key, payload, signature)
        nonce = str(payload["nonce"])
        if nonce in call.get("used_transition_nonces", []):
            raise PermissionError("Call transition replay detected")
        self._rate(state, actor)
        target = str(payload.get("target_state") or "")
        if target not in CALL_TRANSITIONS.get(call["state"], set()):
            raise PermissionError("That call transition is not permitted")
        if target in {"ringing", "answered", "declined"} and actor != call["callee_persona_id"]:
            raise PermissionError("Only the recipient can perform that call transition")
        if target == "cancelled" and actor != call["caller_persona_id"]:
            raise PermissionError("Only the caller can cancel before answer")
        if target in {"connected", "reconnecting", "ended"} and actor not in {call["caller_persona_id"], call["callee_persona_id"]}:
            raise PermissionError("Only a participant can control the active call")
        if target == "connected":
            epoch = int(call.get("negotiation_epoch") or 0)
            transport = next((item for item in call.get("transport_epochs", []) if item.get("epoch") == epoch), None)
            expected = {call["caller_persona_id"], call["callee_persona_id"]}
            if not transport or set(transport.get("participants", {})) != expected or not transport.get("handshake_commitment"):
                raise PermissionError("Both authenticated participants must negotiate a fresh WebRTC epoch")
            call["key_epoch"] = epoch
            call["session_key_commitment"] = transport["handshake_commitment"]
        call["state"] = target
        call["updated_at"] = utc_now_iso()
        if target == "reconnecting":
            call["negotiation_epoch"] = int(call["key_epoch"]) + 1
            call.pop("session_key_commitment", None)
        call["used_transition_nonces"] = list(call.get("used_transition_nonces") or [])[-255:] + [nonce]
        if target in TERMINAL_CALL_STATES:
            call["ended_at"] = call["updated_at"]
            call.pop("session_key_commitment", None)
        event = {"event_id": f"event_{uuid4().hex}", "call_id": call_id, "actor_persona_id": actor, "state": target, "recorded_at": call["updated_at"]}
        state["events"].append(event)
        self._write(state)
        result = {key_: call[key_] for key_ in ("call_id", "state", "key_epoch", "updated_at", "media_audit_status")}
        result["transport_authenticated"] = target == "connected"
        result["server_session_key_held"] = False
        return result

    def create_group(self, *, owner_persona_id: str, name: str, owner_public_key: str) -> dict[str, Any]:
        clean = " ".join(name.split())[:80]
        if len(clean) < 2:
            raise ValueError("Enter a group name")
        group = {
            "schema_version": "pilot.private-group.v1", "group_id": f"group_{uuid4().hex}",
            "name": clean, "members": [{"persona_id": owner_persona_id, "role": "owner", "public_key": owner_public_key, "status": "active"}],
            "key_epoch": 1, "history_epoch_start": 1, "created_at": utc_now_iso(), "events": [], "messages": [],
            "used_message_nonces": [],
        }
        state = self._read()
        state["groups"].append(group)
        self._write(state)
        return self._public_group(group)

    @staticmethod
    def _public_group(group: dict[str, Any]) -> dict[str, Any]:
        return {
            "group_id": group["group_id"], "name": group["name"], "key_epoch": group["key_epoch"],
            "members": [{key: member[key] for key in ("persona_id", "role", "status")} for member in group["members"]],
            "message_count": len(group["messages"]),
        }

    def change_member(
        self, *, group_id: str, actor_persona_id: str, target_persona_id: str,
        operation: str, role: str = "member", target_public_key: str | None = None,
        guardian_approved: bool = False,
    ) -> dict[str, Any]:
        state = self._read()
        group = next((item for item in state["groups"] if item["group_id"] == group_id), None)
        if not group:
            raise KeyError("Group is not available")
        actor = next((item for item in group["members"] if item["persona_id"] == actor_persona_id and item["status"] == "active"), None)
        if not actor or actor["role"] not in {"owner", "admin"}:
            raise PermissionError("Only a group owner or administrator can change membership")
        if operation == "add":
            if role not in GROUP_ROLES or role == "owner" or not target_public_key:
                raise ValueError("Group membership request is invalid")
            if role == "child" and not guardian_approved:
                raise PermissionError("A guardian must approve a child group contact")
            if any(item for item in state["blocks"] if item["owner_persona_id"] == target_persona_id and item["blocked_persona_id"] == actor_persona_id):
                raise PermissionError("That person has blocked this group contact")
            group["members"] = [item for item in group["members"] if item["persona_id"] != target_persona_id]
            group["members"].append({"persona_id": target_persona_id, "role": role, "public_key": target_public_key, "status": "active", "joined_epoch": group["key_epoch"] + 1})
        elif operation == "remove":
            target = next((item for item in group["members"] if item["persona_id"] == target_persona_id and item["status"] == "active"), None)
            if not target or target["role"] == "owner":
                raise PermissionError("That member cannot be removed")
            target["status"] = "removed"
            target["removed_at"] = utc_now_iso()
        else:
            raise ValueError("Choose add or remove")
        group["key_epoch"] += 1
        group["events"].append({"operation": operation, "actor_persona_id": actor_persona_id, "target_persona_id": target_persona_id, "key_epoch": group["key_epoch"], "recorded_at": utc_now_iso()})
        self._write(state)
        return self._public_group(group)

    def add_group_message(
        self, *, payload: dict[str, Any], signature: str,
    ) -> dict[str, Any]:
        required = {"purpose", "group_id", "actor_persona_id", "body_hash", "reply_to", "mentions", "attachment", "key_epoch", "nonce"}
        if set(payload) != required or payload.get("purpose") != "post_group_message":
            raise ValueError("Group message proof is malformed")
        group_id = str(payload.get("group_id") or "")
        actor_persona_id = str(payload.get("actor_persona_id") or "")
        body_hash = str(payload.get("body_hash") or "")
        reply_to = payload.get("reply_to")
        mentions = list(payload.get("mentions") or [])
        attachment = payload.get("attachment")
        state = self._read()
        group = next((item for item in state["groups"] if item["group_id"] == group_id), None)
        member = next((item for item in group["members"] if item["persona_id"] == actor_persona_id and item["status"] == "active"), None) if group else None
        if not member:
            raise PermissionError("Only an active group member can post")
        self._verify(actor_persona_id, str(member.get("public_key") or ""), payload, signature)
        if int(payload.get("key_epoch") or 0) != int(group["key_epoch"]):
            raise PermissionError("Group message uses a stale membership key epoch")
        nonce = str(payload.get("nonce") or "")
        if len(nonce) < 8 or nonce in group.get("used_message_nonces", []):
            raise PermissionError("Group message nonce is invalid or replayed")
        self._rate(state, actor_persona_id)
        active = {item["persona_id"] for item in group["members"] if item["status"] == "active"}
        mentioned = sorted(set(mentions or []))
        if any(persona not in active for persona in mentioned):
            raise PermissionError("A mention targets someone outside the group")
        if reply_to and not any(item["message_id"] == reply_to for item in group["messages"]):
            raise ValueError("Reply target is not in this group")
        attachment_ref = None
        if attachment:
            if int(attachment.get("byte_length") or 0) > self.MAX_ATTACHMENT_BYTES or not str(attachment.get("content_hash") or ""):
                raise ValueError("Group attachment is outside the supported bound")
            attachment_ref = {key: attachment[key] for key in ("attachment_id", "byte_length", "content_hash")}
        message = {
            "message_id": f"group_message_{uuid4().hex}", "actor_persona_id": actor_persona_id,
            "body_hash": body_hash, "reply_to": reply_to, "mentions": mentioned,
            "attachment": attachment_ref, "key_epoch": group["key_epoch"], "created_at": utc_now_iso(), "reactions": [],
        }
        group["messages"].append(message)
        group["used_message_nonces"] = list(group.get("used_message_nonces") or [])[-1023:] + [nonce]
        state["events"].append({"actor_persona_id": actor_persona_id, "recorded_at": message["created_at"], "kind": "group_message"})
        self._write(state)
        return dict(message)

    def react(self, *, group_id: str, message_id: str, actor_persona_id: str, reaction: str) -> dict[str, Any]:
        if reaction not in {"like", "love", "laugh", "acknowledged"}:
            raise ValueError("Choose a supported reaction")
        state = self._read()
        group = next((item for item in state["groups"] if item["group_id"] == group_id), None)
        active = {item["persona_id"] for item in group["members"] if item["status"] == "active"} if group else set()
        message = next((item for item in group["messages"] if item["message_id"] == message_id), None) if group else None
        if actor_persona_id not in active or not message:
            raise PermissionError("That group reaction is not permitted")
        message["reactions"] = [item for item in message["reactions"] if item["persona_id"] != actor_persona_id]
        message["reactions"].append({"persona_id": actor_persona_id, "reaction": reaction})
        self._write(state)
        return {"message_id": message_id, "reactions": list(message["reactions"])}

    def block(self, *, owner_persona_id: str, blocked_persona_id: str, reason: str = "user_blocked") -> dict[str, Any]:
        state = self._read()
        record = {"owner_persona_id": owner_persona_id, "blocked_persona_id": blocked_persona_id, "reason": reason, "recorded_at": utc_now_iso()}
        state["blocks"] = [item for item in state["blocks"] if not (item["owner_persona_id"] == owner_persona_id and item["blocked_persona_id"] == blocked_persona_id)] + [record]
        self._write(state)
        return record

    def report(self, *, reporter_persona_id: str, reported_persona_id: str, category: str, evidence_hash: str) -> dict[str, Any]:
        if category not in {"spam", "harassment", "unsafe_child_contact", "impersonation", "other"}:
            raise ValueError("Choose a supported report category")
        record = {
            "report_id": f"report_{uuid4().hex}", "reporter_persona_id": reporter_persona_id,
            "reported_persona_id": reported_persona_id, "category": category,
            "evidence_hash": evidence_hash, "recorded_at": utc_now_iso(),
            "provider_report_submitted": False,
        }
        state = self._read()
        state["reports"].append(record)
        self._write(state)
        return record
