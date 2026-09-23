from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_fabric.pilot_inbox import PilotInbox

from .pairing import MobilePairingAuthority
from .proof_rail import SelectiveProofRail


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,199}$")


class UnifiedInbox:
    """Encrypted Pilot/GlyphNet bridge with possession-bound actions and durable replay state."""

    _lock = threading.RLock()
    MAX_ATTACHMENT_BYTES = 1_000_000
    MAX_VOICE_NOTE_BYTES = 1_500_000
    ALLOWED_ATTACHMENT_TYPES = frozenset({
        "application/pdf", "image/gif", "image/heic", "image/heif", "image/jpeg", "image/png",
        "text/csv", "text/markdown", "text/plain",
    })
    ALLOWED_VOICE_TYPES = frozenset({"audio/mp4", "audio/ogg", "audio/wav", "audio/webm"})
    STRUCTURED_CARD_TYPES = frozenset({"reminder", "follow_up", "calendar", "document_review", "moment"})

    def __init__(
        self,
        runtime_dir: str | Path,
        *,
        mother_id: str,
        mother_identity: DeviceIdentity,
        pairing_authority: MobilePairingAuthority,
        pilot_inbox: PilotInbox,
        proof_rail: SelectiveProofRail | None = None,
    ) -> None:
        if not _ID.fullmatch(mother_id):
            raise ValueError("mother_id is invalid")
        self.root = Path(runtime_dir) / "pilot_unified_inbox"
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.path = self.root / "state.json"
        self.content_key_path = self.root / "content.key"
        self.transport_key_path = self.root / "transport.key"
        self.mother_id = mother_id
        self.identity = mother_identity
        self.pairing = pairing_authority
        self.pilot_inbox = pilot_inbox
        self.proof_rail = proof_rail
        self._content_key = self._load_key(self.content_key_path)
        self._transport_private = self._load_transport_key()

    def _proof(
        self,
        *,
        event: str,
        action: dict[str, Any],
        outcome: str,
        private_record: dict[str, Any],
        idempotency_key: str,
        previous_commitment_id: str | None = None,
    ) -> str | None:
        """Emit a best-effort proof without making the action depend on chain health."""
        if self.proof_rail is None:
            return None
        try:
            proof = self.proof_rail.commit(
                event=event,
                object_id=str(action["action_id"]),
                scope_hash=str(action["scope_hash"]),
                policy_version="pilot-inbox-policy-v1",
                outcome=outcome,
                private_record=private_record,
                idempotency_key=idempotency_key,
                previous_commitment_id=previous_commitment_id,
                publication_policy="best_effort",
            )
        except (ValueError, PermissionError, RuntimeError):
            return None
        action.setdefault("proof_commitment_ids", []).append(proof["commitment_id"])
        return str(proof["commitment_id"])

    @staticmethod
    def _initial() -> dict[str, Any]:
        return {
            "schema_version": "pilot.unified-inbox.v1",
            "revision": 0,
            "peers": [],
            "actions": [],
            "messages": [],
            "attachments": [],
            "ptt_floors": [],
            "ptt_events": [],
            "receipts": [],
            "used_requests": [],
            "received_packets": [],
        }

    @staticmethod
    def _load_key(path: Path) -> bytes:
        if path.exists():
            raw = path.read_bytes()
            if len(raw) != 32:
                raise RuntimeError("Pilot inbox key is invalid")
            os.chmod(path, 0o600)
            return raw
        raw = secrets.token_bytes(32)
        path.write_bytes(raw)
        os.chmod(path, 0o600)
        return raw

    def _load_transport_key(self) -> X25519PrivateKey:
        if self.transport_key_path.exists():
            raw = self.transport_key_path.read_bytes()
            os.chmod(self.transport_key_path, 0o600)
            return X25519PrivateKey.from_private_bytes(raw)
        key = X25519PrivateKey.generate()
        raw = key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        self.transport_key_path.write_bytes(raw)
        os.chmod(self.transport_key_path, 0o600)
        return key

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise RuntimeError("Pilot inbox state could not be verified") from None
        if not isinstance(value, dict) or value.get("schema_version") != "pilot.unified-inbox.v1":
            raise RuntimeError("Pilot inbox state has an unsupported format")
        return value

    def _write(self, state: dict[str, Any]) -> None:
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    @staticmethod
    def _clean(value: str, maximum: int) -> str:
        return " ".join(str(value).split())[:maximum]

    def descriptor(self) -> dict[str, Any]:
        public = self._transport_private.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        payload = {
            "schema_version": "pilot.inbox-peer.v1",
            "mother_id": self.mother_id,
            "signing_public_key": self.identity.public_key_b64,
            "transport_public_key": base64.b64encode(public).decode("ascii"),
            "issued_at": utc_now_iso(),
        }
        return {**payload, "signature": self.identity.sign(canonical_bytes(payload))}

    def trust_peer(self, descriptor: dict[str, Any]) -> dict[str, Any]:
        required = {"schema_version", "mother_id", "signing_public_key", "transport_public_key", "issued_at", "signature"}
        if set(descriptor) != required or descriptor.get("schema_version") != "pilot.inbox-peer.v1":
            raise ValueError("Pilot peer descriptor is malformed")
        payload = {key: descriptor[key] for key in required if key != "signature"}
        if not DeviceIdentity.verify(str(descriptor["signing_public_key"]), canonical_bytes(payload), str(descriptor["signature"])):
            raise PermissionError("Pilot could not verify the other mother brain")
        try:
            transport = base64.b64decode(str(descriptor["transport_public_key"]), validate=True)
            X25519PublicKey.from_public_bytes(transport)
        except (ValueError, TypeError):
            raise ValueError("Pilot peer transport key is invalid") from None
        with self._lock:
            state = self._read()
            peer = {
                "mother_id": str(descriptor["mother_id"]),
                "signing_public_key": str(descriptor["signing_public_key"]),
                "transport_public_key": str(descriptor["transport_public_key"]),
                "descriptor_hash": canonical_hash(payload),
                "trusted_at": utc_now_iso(),
                "status": "trusted",
            }
            state["peers"] = [item for item in state.get("peers", []) if item.get("mother_id") != peer["mother_id"]] + [peer]
            self._write(state)
            return {key: peer[key] for key in ("mother_id", "descriptor_hash", "trusted_at", "status")}

    def resolve_pilot_contact(
        self,
        *,
        persona_id: str,
        display_name: str,
        certificate: dict[str, Any],
        lease: dict[str, Any],
    ) -> dict[str, Any]:
        verified = self.pairing.validate(certificate=certificate, lease=lease, required_scope="inbox.read")
        if verified["persona_id"] != persona_id:
            raise PermissionError("This phone cannot resolve another person's contacts")
        matches = self.pilot_inbox.resolve_spoken_contacts(
            owner_persona_id=persona_id,
            display_name=display_name,
        )
        pilot_matches = [item for item in matches if item.get("pilot_persona_id") and item.get("pilot_mother_id")]
        if len(pilot_matches) != 1:
            raise PermissionError("Choose one exact Pilot contact privately")
        contact = pilot_matches[0]
        state = self._read()
        if not any(item.get("mother_id") == contact["pilot_mother_id"] and item.get("status") == "trusted" for item in state["peers"]):
            raise PermissionError("That contact's Pilot is not trusted by this mother")
        return {
            "contact_id": contact["contact_id"],
            "display_name": contact["display_name"],
            "recipient_persona_id": contact["pilot_persona_id"],
            "recipient_mother_id": contact["pilot_mother_id"],
            "route": "pilot",
            "external_contact_details_exposed": False,
        }

    def _authorize(
        self,
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        scope: str,
        request: dict[str, Any],
        phone_signature: str,
    ) -> str:
        verified = self.pairing.validate(certificate=certificate, lease=lease, required_scope=scope)
        if request.get("persona_id") != verified["persona_id"]:
            raise PermissionError("The request identity does not match this phone")
        if not DeviceIdentity.verify(str(certificate["phone_public_key"]), canonical_bytes(request), phone_signature):
            raise PermissionError("This phone did not sign the inbox request")
        return str(verified["persona_id"])

    def _encrypt_local(self, content: dict[str, Any], aad: dict[str, Any]) -> dict[str, str]:
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self._content_key).encrypt(nonce, canonical_bytes(content), canonical_bytes(aad))
        return {"nonce": base64.b64encode(nonce).decode("ascii"), "ciphertext": base64.b64encode(ciphertext).decode("ascii")}

    def _decrypt_local(self, record: dict[str, Any], aad: dict[str, Any]) -> dict[str, Any]:
        raw = AESGCM(self._content_key).decrypt(
            base64.b64decode(record["nonce"]),
            base64.b64decode(record["ciphertext"]),
            canonical_bytes(aad),
        )
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise RuntimeError("Pilot inbox content is invalid")
        return value

    def _store_attachment(self, *, attachment_id: str, raw: bytes, aad: dict[str, Any]) -> str:
        nonce = secrets.token_bytes(12)
        encrypted = AESGCM(self._content_key).encrypt(nonce, raw, canonical_bytes(aad))
        path = self.root / f"{attachment_id}.blob"
        path.write_bytes(nonce + encrypted)
        os.chmod(path, 0o600)
        return path.name

    def _read_attachment_bytes(self, record: dict[str, Any]) -> bytes:
        expires_at = str(record.get("expires_at") or "")
        if expires_at and datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            path = self.root / str(record.get("storage_ref") or "")
            if path.is_file():
                path.unlink()
            raise PermissionError("That private recording has expired")
        path = self.root / str(record["storage_ref"])
        payload = path.read_bytes()
        if len(payload) < 13:
            raise RuntimeError("Pilot attachment storage is invalid")
        aad = {
            "attachment_id": record["attachment_id"],
            "owner_persona_id": record["owner_persona_id"],
            "content_hash": record["content_hash"],
        }
        try:
            raw = AESGCM(self._content_key).decrypt(payload[:12], payload[12:], canonical_bytes(aad))
        except (InvalidTag, OSError):
            raise RuntimeError("Pilot attachment integrity could not be verified") from None
        if not secrets.compare_digest(hashlib.sha256(raw).hexdigest(), str(record["content_hash"])):
            raise RuntimeError("Pilot attachment integrity could not be verified")
        return raw

    @classmethod
    def _decode_attachment(cls, request: dict[str, Any]) -> tuple[str, str, bytes, str]:
        filename = cls._clean(str(request.get("filename") or ""), 180)
        media_type = cls._clean(str(request.get("media_type") or ""), 100).lower()
        if not filename or "/" in filename or "\\" in filename or media_type not in cls.ALLOWED_ATTACHMENT_TYPES:
            raise ValueError("Choose a supported attachment")
        try:
            raw = base64.b64decode(str(request.get("content_base64") or ""), validate=True)
        except (ValueError, TypeError):
            raise ValueError("Pilot could not read that attachment") from None
        if not raw or len(raw) > cls.MAX_ATTACHMENT_BYTES:
            raise ValueError("Attachment size is outside the supported bound")
        return filename, media_type, raw, hashlib.sha256(raw).hexdigest()

    @classmethod
    def _decode_voice_note(cls, request: dict[str, Any]) -> tuple[str, str, bytes, str, int]:
        media_type = cls._clean(str(request.get("media_type") or ""), 100).lower().split(";", 1)[0]
        if media_type not in cls.ALLOWED_VOICE_TYPES:
            raise ValueError("Choose a supported voice recording")
        try:
            raw = base64.b64decode(str(request.get("content_base64") or ""), validate=True)
        except (ValueError, TypeError):
            raise ValueError("Pilot could not read that voice recording") from None
        duration_ms = int(request.get("duration_ms") or 0)
        if not raw or len(raw) > cls.MAX_VOICE_NOTE_BYTES or duration_ms < 100 or duration_ms > 120_000:
            raise ValueError("Voice recording is outside the supported bound")
        extension = {"audio/mp4": "m4a", "audio/ogg": "ogg", "audio/wav": "wav", "audio/webm": "webm"}[media_type]
        return f"Pilot voice note.{extension}", media_type, raw, hashlib.sha256(raw).hexdigest(), duration_ms

    @staticmethod
    def _request_key(request: dict[str, Any]) -> tuple[str, str]:
        key = str(request.get("idempotency_key") or "")
        if not _ID.fullmatch(key):
            raise ValueError("A bounded idempotency key is required")
        return key, canonical_hash(request)

    def prepare_task(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="task.create",
            request=request, phone_signature=phone_signature,
        )
        key, request_hash = self._request_key(request)
        title = self._clean(str(request.get("title") or ""), 240)
        recipient_persona_id = self._clean(str(request.get("recipient_persona_id") or ""), 200)
        recipient_mother_id = self._clean(str(request.get("recipient_mother_id") or ""), 200)
        if len(title) < 2 or not _ID.fullmatch(recipient_persona_id) or not _ID.fullmatch(recipient_mother_id):
            raise ValueError("Choose one Pilot recipient and a task")
        scope = {
            "sender_persona_id": persona_id,
            "recipient_persona_id": recipient_persona_id,
            "recipient_mother_id": recipient_mother_id,
            "title": title,
            "space_id": f"personal/{persona_id}",
        }
        with self._lock:
            state = self._read()
            used = next((item for item in state.get("used_requests", []) if item.get("idempotency_key") == key), None)
            if used:
                if used.get("request_hash") != request_hash:
                    raise PermissionError("That request key was already used for different content")
                action = next(item for item in state["actions"] if item["action_id"] == used["object_id"])
                return self._public_action(action)
            action_id = f"action_{uuid4().hex}"
            aad = {"action_id": action_id, "owner_persona_id": persona_id, "kind": "task_proposal"}
            action = {
                **aad,
                "space_id": f"personal/{persona_id}",
                "privacy": "private",
                "recipient_persona_id": recipient_persona_id,
                "recipient_mother_id": recipient_mother_id,
                "scope_hash": canonical_hash(scope),
                "status": "awaiting_approval",
                "created_at": utc_now_iso(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                **self._encrypt_local({"title": title}, aad),
            }
            state["actions"].append(action)
            state["used_requests"].append({"idempotency_key": key, "request_hash": request_hash, "object_id": action_id})
            state["used_requests"] = state["used_requests"][-4096:]
            self._write(state)
            return self._public_action(action)

    def send_text(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="message.send",
            request=request, phone_signature=phone_signature,
        )
        key, request_hash = self._request_key(request)
        body = self._clean(str(request.get("body") or ""), 2000)
        recipient_persona_id = self._clean(str(request.get("recipient_persona_id") or ""), 200)
        recipient_mother_id = self._clean(str(request.get("recipient_mother_id") or ""), 200)
        if not body or not _ID.fullmatch(recipient_persona_id) or not _ID.fullmatch(recipient_mother_id):
            raise ValueError("Choose one Pilot recipient and write a message")
        with self._lock:
            state = self._read()
            used = next((item for item in state.get("used_requests", []) if item.get("idempotency_key") == key), None)
            if used:
                if used.get("request_hash") != request_hash:
                    raise PermissionError("That request key was already used for different content")
                record = next(item for item in state["messages"] if item["message_id"] == used["object_id"])
                return {**self._public_message(record), "delivery_packet": dict(record["delivery_packet"])}
            peer = next((item for item in state["peers"] if item.get("mother_id") == recipient_mother_id and item.get("status") == "trusted"), None)
            if not peer:
                raise PermissionError("The recipient's Pilot is not trusted by this mother")
            message_id = f"message_{uuid4().hex}"
            conversation_id = f"conversation/{min(persona_id, recipient_persona_id)}--{max(persona_id, recipient_persona_id)}"
            payload = {
                "type": "text",
                "message_id": message_id,
                "conversation_id": conversation_id,
                "sender_persona_id": persona_id,
                "recipient_persona_id": recipient_persona_id,
                "sender_space_id": f"personal/{persona_id}",
                "recipient_space_id": f"personal/{recipient_persona_id}",
                "privacy": "private",
                "body": body,
                "created_at": utc_now_iso(),
                "content_hash": canonical_hash(body),
            }
            packet = self._encrypt_packet(peer=peer, payload=payload, recipient_persona_id=recipient_persona_id)
            aad = {"message_id": message_id, "sender_persona_id": persona_id, "recipient_persona_id": recipient_persona_id}
            record = {
                **aad,
                "conversation_id": conversation_id,
                "sender_mother_id": self.mother_id,
                "recipient_mother_id": recipient_mother_id,
                "kind": "text",
                "space_id": payload["sender_space_id"],
                "privacy": payload["privacy"],
                "status": "delivered_to_recipient_mother",
                "created_at": payload["created_at"],
                "content_hash": payload["content_hash"],
                "delivery_packet": packet,
                **self._encrypt_local({"body": body}, aad),
            }
            state["messages"].append(record)
            state["used_requests"].append({"idempotency_key": key, "request_hash": request_hash, "object_id": message_id})
            state["used_requests"] = state["used_requests"][-4096:]
            state["receipts"].append(self._receipt(message_id, persona_id, "delivered", packet["packet_hash"]))
            self._write(state)
            return {**self._public_message(record), "delivery_packet": packet}

    def send_structured_card(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="message.send",
            request=request, phone_signature=phone_signature,
        )
        key, request_hash = self._request_key(request)
        card_type = str(request.get("card_type") or "")
        title = self._clean(str(request.get("title") or ""), 240)
        detail = self._clean(str(request.get("detail") or ""), 1000)
        recipient_persona_id = self._clean(str(request.get("recipient_persona_id") or ""), 200)
        recipient_mother_id = self._clean(str(request.get("recipient_mother_id") or ""), 200)
        if card_type not in self.STRUCTURED_CARD_TYPES or len(title) < 2:
            raise ValueError("Choose a supported structured Inbox card")
        if not _ID.fullmatch(recipient_persona_id) or not _ID.fullmatch(recipient_mother_id):
            raise ValueError("Choose one Pilot recipient")
        schedule: dict[str, str] = {}
        for field in ("due_at", "starts_at", "ends_at"):
            value = str(request.get(field) or "")
            if value:
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    raise ValueError(f"{field} must be an ISO timestamp") from None
                schedule[field] = value
        if card_type == "calendar" and not {"starts_at", "ends_at"}.issubset(schedule):
            raise ValueError("Calendar cards require a start and end")
        if card_type in {"reminder", "follow_up"} and "due_at" not in schedule:
            raise ValueError("That card requires a due time")
        card = {"card_type": card_type, "title": title, "detail": detail, **schedule, "state": "proposed"}
        if card_type == "moment":
            moment_id = self._clean(str(request.get("moment_id") or ""), 200)
            context_hash = self._clean(str(request.get("context_hash") or ""), 128)
            share_mode = self._clean(str(request.get("share_mode") or "context_card"), 80)
            provider_url = self._clean(str(request.get("provider_url") or ""), 1000)
            rights = dict(request.get("rights") or {})
            if not moment_id.startswith("moment_") or not context_hash:
                raise ValueError("Moment cards require an exact Moment and context hash")
            if provider_url and not provider_url.startswith("https://"):
                raise ValueError("Moment provider links must use HTTPS")
            if rights.get("protected_audio_copied") is not False or rights.get("protected_video_copied") is not False:
                raise PermissionError("Moment cards cannot include protected programme media")
            card.update({
                "moment_id": moment_id,
                "context_hash": context_hash,
                "share_mode": share_mode,
                "provider_url": provider_url,
                "rights": {
                    "protected_audio_copied": False,
                    "protected_video_copied": False,
                    "card_contains_context_only": True,
                },
            })
        with self._lock:
            state = self._read()
            used = next((item for item in state.get("used_requests", []) if item.get("idempotency_key") == key), None)
            if used:
                if used.get("request_hash") != request_hash:
                    raise PermissionError("That request key was already used for different content")
                record = next(item for item in state["messages"] if item["message_id"] == used["object_id"])
                return {**self._public_message(record), "delivery_packet": dict(record["delivery_packet"])}
            peer = next((item for item in state["peers"] if item.get("mother_id") == recipient_mother_id and item.get("status") == "trusted"), None)
            if not peer:
                raise PermissionError("The recipient's Pilot is not trusted by this mother")
            message_id = f"message_{uuid4().hex}"
            conversation_id = f"conversation/{min(persona_id, recipient_persona_id)}--{max(persona_id, recipient_persona_id)}"
            created_at = utc_now_iso()
            payload = {
                "type": "structured_card", "message_id": message_id, "conversation_id": conversation_id,
                "sender_persona_id": persona_id, "recipient_persona_id": recipient_persona_id,
                "recipient_space_id": f"personal/{recipient_persona_id}", "privacy": "private",
                "card": card, "created_at": created_at, "content_hash": canonical_hash(card),
            }
            packet = self._encrypt_packet(peer=peer, payload=payload, recipient_persona_id=recipient_persona_id)
            aad = {"message_id": message_id, "sender_persona_id": persona_id, "recipient_persona_id": recipient_persona_id}
            record = {
                **aad, "conversation_id": conversation_id, "sender_mother_id": self.mother_id,
                "recipient_mother_id": recipient_mother_id, "kind": card_type, "space_id": f"personal/{persona_id}",
                "privacy": "private", "status": "delivered_to_recipient_mother", "created_at": created_at,
                "content_hash": payload["content_hash"], "delivery_packet": packet,
                **self._encrypt_local({"body": detail, "card": card}, aad),
            }
            state["messages"].append(record)
            state["used_requests"].append({"idempotency_key": key, "request_hash": request_hash, "object_id": message_id})
            state["used_requests"] = state["used_requests"][-4096:]
            state["receipts"].append(self._receipt(message_id, persona_id, "delivered", packet["packet_hash"]))
            self._write(state)
            return {**self._public_message(record), "delivery_packet": packet}

    def send_attachment(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="message.send",
            request=request, phone_signature=phone_signature,
        )
        key, request_hash = self._request_key(request)
        filename, media_type, raw, content_hash = self._decode_attachment(request)
        recipient_persona_id = self._clean(str(request.get("recipient_persona_id") or ""), 200)
        recipient_mother_id = self._clean(str(request.get("recipient_mother_id") or ""), 200)
        if not _ID.fullmatch(recipient_persona_id) or not _ID.fullmatch(recipient_mother_id):
            raise ValueError("Choose one Pilot recipient")
        with self._lock:
            state = self._read()
            used = next((item for item in state.get("used_requests", []) if item.get("idempotency_key") == key), None)
            if used:
                if used.get("request_hash") != request_hash:
                    raise PermissionError("That request key was already used for different content")
                record = next(item for item in state["messages"] if item["message_id"] == used["object_id"])
                return {**self._public_message(record), "delivery_packet": dict(record["delivery_packet"])}
            peer = next((item for item in state["peers"] if item.get("mother_id") == recipient_mother_id and item.get("status") == "trusted"), None)
            if not peer:
                raise PermissionError("The recipient's Pilot is not trusted by this mother")
            message_id = f"message_{uuid4().hex}"
            attachment_id = f"attachment_{uuid4().hex}"
            created_at = utc_now_iso()
            conversation_id = f"conversation/{min(persona_id, recipient_persona_id)}--{max(persona_id, recipient_persona_id)}"
            payload = {
                "type": "attachment", "message_id": message_id, "conversation_id": conversation_id,
                "attachment_id": attachment_id, "sender_persona_id": persona_id,
                "recipient_persona_id": recipient_persona_id, "recipient_space_id": f"personal/{recipient_persona_id}",
                "privacy": "private", "filename": filename, "media_type": media_type,
                "byte_length": len(raw), "content_hash": content_hash,
                "content_base64": base64.b64encode(raw).decode("ascii"), "created_at": created_at,
            }
            packet = self._encrypt_packet(peer=peer, payload=payload, recipient_persona_id=recipient_persona_id)
            attachment_aad = {"attachment_id": attachment_id, "owner_persona_id": persona_id, "content_hash": content_hash}
            attachment = {
                **attachment_aad, "message_id": message_id, "filename": filename, "media_type": media_type,
                "byte_length": len(raw), "storage_ref": self._store_attachment(attachment_id=attachment_id, raw=raw, aad=attachment_aad),
                "created_at": created_at, "encrypted": True,
            }
            aad = {"message_id": message_id, "sender_persona_id": persona_id, "recipient_persona_id": recipient_persona_id}
            record = {
                **aad, "conversation_id": conversation_id, "sender_mother_id": self.mother_id,
                "recipient_mother_id": recipient_mother_id, "kind": "attachment", "space_id": f"personal/{persona_id}",
                "privacy": "private", "status": "delivered_to_recipient_mother", "created_at": created_at,
                "content_hash": content_hash, "attachment_refs": [attachment_id], "delivery_packet": packet,
                **self._encrypt_local({"body": ""}, aad),
            }
            state.setdefault("attachments", []).append(attachment)
            state["messages"].append(record)
            state["used_requests"].append({"idempotency_key": key, "request_hash": request_hash, "object_id": message_id})
            state["used_requests"] = state["used_requests"][-4096:]
            state["receipts"].append(self._receipt(message_id, persona_id, "delivered", packet["packet_hash"]))
            self._write(state)
            return {**self._public_message(record), "delivery_packet": packet}

    def send_voice_note(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="message.send",
            request=request, phone_signature=phone_signature,
        )
        key, request_hash = self._request_key(request)
        filename, media_type, raw, content_hash, duration_ms = self._decode_voice_note(request)
        recipient_persona_id = self._clean(str(request.get("recipient_persona_id") or ""), 200)
        recipient_mother_id = self._clean(str(request.get("recipient_mother_id") or ""), 200)
        retention_seconds = int(request.get("retention_seconds") or 86_400)
        if retention_seconds < 300 or retention_seconds > 604_800:
            raise ValueError("Choose voice retention between five minutes and seven days")
        if not _ID.fullmatch(recipient_persona_id) or not _ID.fullmatch(recipient_mother_id):
            raise ValueError("Choose one Pilot recipient")
        with self._lock:
            state = self._read()
            used = next((item for item in state.get("used_requests", []) if item.get("idempotency_key") == key), None)
            if used:
                if used.get("request_hash") != request_hash:
                    raise PermissionError("That request key was already used for different content")
                record = next(item for item in state["messages"] if item["message_id"] == used["object_id"])
                return {**self._public_message(record), "delivery_packet": dict(record["delivery_packet"])}
            peer = next((item for item in state["peers"] if item.get("mother_id") == recipient_mother_id and item.get("status") == "trusted"), None)
            if not peer:
                raise PermissionError("The recipient's Pilot is not trusted by this mother")
            floor_id = str(request.get("ptt_floor_id") or "")
            if floor_id:
                floor = next((item for item in state.get("ptt_floors", []) if item.get("floor_id") == floor_id), None)
                if not floor or floor.get("status") != "held" or floor.get("holder_persona_id") != persona_id or floor.get("holder_device_id") != certificate.get("device_id") or floor.get("lease_id") != lease.get("lease_id"):
                    raise PermissionError("This phone does not hold that push-to-talk floor")
                if datetime.fromisoformat(str(floor["expires_at"]).replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                    raise PermissionError("That push-to-talk floor has expired")
                if floor.get("recipient_persona_id") != recipient_persona_id or floor.get("recipient_mother_id") != recipient_mother_id:
                    raise PermissionError("That push-to-talk floor belongs to another conversation")
                floor["status"] = "released"
                floor["released_at"] = utc_now_iso()
            message_id = f"message_{uuid4().hex}"
            attachment_id = f"attachment_{uuid4().hex}"
            created_at = utc_now_iso()
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=retention_seconds)).isoformat()
            conversation_id = f"conversation/{min(persona_id, recipient_persona_id)}--{max(persona_id, recipient_persona_id)}"
            payload = {
                "type": "voice_note", "message_id": message_id, "conversation_id": conversation_id,
                "attachment_id": attachment_id, "sender_persona_id": persona_id,
                "recipient_persona_id": recipient_persona_id, "recipient_space_id": f"personal/{recipient_persona_id}",
                "privacy": "private", "filename": filename, "media_type": media_type, "duration_ms": duration_ms,
                "byte_length": len(raw), "content_hash": content_hash, "expires_at": expires_at,
                "content_base64": base64.b64encode(raw).decode("ascii"), "created_at": created_at,
            }
            packet = self._encrypt_packet(peer=peer, payload=payload, recipient_persona_id=recipient_persona_id)
            attachment_aad = {"attachment_id": attachment_id, "owner_persona_id": persona_id, "content_hash": content_hash}
            attachment = {
                **attachment_aad, "message_id": message_id, "filename": filename, "media_type": media_type,
                "byte_length": len(raw), "duration_ms": duration_ms, "expires_at": expires_at,
                "storage_ref": self._store_attachment(attachment_id=attachment_id, raw=raw, aad=attachment_aad),
                "created_at": created_at, "encrypted": True,
            }
            aad = {"message_id": message_id, "sender_persona_id": persona_id, "recipient_persona_id": recipient_persona_id}
            record = {
                **aad, "conversation_id": conversation_id, "sender_mother_id": self.mother_id,
                "recipient_mother_id": recipient_mother_id, "kind": "voice_note", "space_id": f"personal/{persona_id}",
                "privacy": "private", "status": "delivered_to_recipient_mother", "created_at": created_at,
                "content_hash": content_hash, "attachment_refs": [attachment_id], "delivery_packet": packet,
                **self._encrypt_local({"body": ""}, aad),
            }
            state.setdefault("attachments", []).append(attachment)
            state["messages"].append(record)
            state["used_requests"].append({"idempotency_key": key, "request_hash": request_hash, "object_id": message_id})
            state["used_requests"] = state["used_requests"][-4096:]
            state["receipts"].append(self._receipt(message_id, persona_id, "delivered", packet["packet_hash"]))
            self._write(state)
            return {**self._public_message(record), "delivery_packet": packet}

    def control_ptt_floor(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="message.send",
            request=request, phone_signature=phone_signature,
        )
        key, request_hash = self._request_key(request)
        operation = str(request.get("operation") or "")
        if operation not in {"acquire", "renew", "release"}:
            raise ValueError("Choose a push-to-talk floor operation")
        now = datetime.now(timezone.utc)
        with self._lock:
            state = self._read()
            previous = next((item for item in state.get("ptt_events", []) if item.get("idempotency_key") == key), None)
            if previous:
                if previous.get("request_hash") != request_hash:
                    raise PermissionError("That push-to-talk request key was reused for different content")
                return dict(previous["result"])
            for floor in state.get("ptt_floors", []):
                if floor.get("status") == "held" and datetime.fromisoformat(str(floor["expires_at"]).replace("Z", "+00:00")) <= now:
                    floor["status"] = "expired"
                    floor["expired_at"] = utc_now_iso()
            if operation == "acquire":
                recipient_persona_id = self._clean(str(request.get("recipient_persona_id") or ""), 200)
                recipient_mother_id = self._clean(str(request.get("recipient_mother_id") or ""), 200)
                if not _ID.fullmatch(recipient_persona_id) or not _ID.fullmatch(recipient_mother_id):
                    raise ValueError("Choose one Pilot recipient")
                conversation_id = f"conversation/{min(persona_id, recipient_persona_id)}--{max(persona_id, recipient_persona_id)}"
                conflict = next((item for item in state.get("ptt_floors", []) if item.get("conversation_id") == conversation_id and item.get("status") == "held"), None)
                if conflict:
                    raise PermissionError("Someone else is speaking in that conversation")
                floor = {
                    "schema_version": "pilot.ptt-floor.v1", "floor_id": f"floor_{uuid4().hex}",
                    "conversation_id": conversation_id, "holder_persona_id": persona_id,
                    "holder_device_id": certificate["device_id"], "lease_id": lease["lease_id"],
                    "recipient_persona_id": recipient_persona_id, "recipient_mother_id": recipient_mother_id,
                    "status": "held", "acquired_at": utc_now_iso(), "expires_at": (now + timedelta(seconds=15)).isoformat(),
                }
                state.setdefault("ptt_floors", []).append(floor)
            else:
                floor_id = str(request.get("floor_id") or "")
                floor = next((item for item in state.get("ptt_floors", []) if item.get("floor_id") == floor_id), None)
                if not floor or floor.get("holder_persona_id") != persona_id or floor.get("holder_device_id") != certificate.get("device_id") or floor.get("lease_id") != lease.get("lease_id"):
                    raise PermissionError("This phone does not own that push-to-talk floor")
                if floor.get("status") != "held":
                    raise PermissionError("That push-to-talk floor is no longer active")
                if operation == "renew":
                    floor["expires_at"] = (now + timedelta(seconds=15)).isoformat()
                    floor["renewed_at"] = utc_now_iso()
                else:
                    floor["status"] = "released"
                    floor["released_at"] = utc_now_iso()
            result = {key: floor[key] for key in ("schema_version", "floor_id", "conversation_id", "holder_persona_id", "holder_device_id", "status", "expires_at")}
            state.setdefault("ptt_events", []).append({"idempotency_key": key, "request_hash": request_hash, "result": result})
            state["ptt_events"] = state["ptt_events"][-4096:]
            self._write(state)
            return result

    def _public_message(self, record: dict[str, Any]) -> dict[str, Any]:
        aad = {
            "message_id": record["message_id"],
            "sender_persona_id": record["sender_persona_id"],
            "recipient_persona_id": record["recipient_persona_id"],
        }
        result = {
            **{key: record.get(key) for key in (
                "message_id", "conversation_id", "sender_persona_id", "recipient_persona_id",
                "sender_mother_id", "recipient_mother_id", "kind", "space_id", "privacy", "status", "created_at", "content_hash",
            )},
            **self._decrypt_local(record, aad),
        }
        attachment_ids = list(record.get("attachment_refs") or [])
        if attachment_ids:
            state = self._read()
            result["attachments"] = [
                {key: item.get(key) for key in ("attachment_id", "filename", "media_type", "byte_length", "content_hash", "encrypted", "duration_ms", "expires_at") if item.get(key) is not None}
                for item in state.get("attachments", []) if item.get("attachment_id") in attachment_ids
            ]
        return result

    def read_attachment(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="inbox.read",
            request=request, phone_signature=phone_signature,
        )
        attachment_id = str(request.get("attachment_id") or "")
        with self._lock:
            state = self._read()
            attachment = next((item for item in state.get("attachments", []) if item.get("attachment_id") == attachment_id), None)
            if not attachment:
                raise KeyError("That attachment is not available")
            message = next((item for item in state["messages"] if attachment_id in item.get("attachment_refs", [])), None)
            if not message or persona_id not in {message.get("sender_persona_id"), message.get("recipient_persona_id")}:
                raise PermissionError("This phone cannot read that attachment")
            raw = self._read_attachment_bytes(attachment)
            return {
                **{key: attachment[key] for key in ("attachment_id", "filename", "media_type", "byte_length", "content_hash")},
                "content_base64": base64.b64encode(raw).decode("ascii"),
            }

    def search(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="inbox.read",
            request=request, phone_signature=phone_signature,
        )
        query = self._clean(str(request.get("query") or ""), 120).casefold()
        kind = str(request.get("kind") or "all")
        status = self._clean(str(request.get("status") or ""), 80)
        if kind not in {"all", "messages", "tasks", "files"}:
            raise ValueError("Choose a supported Inbox filter")
        if len(query) == 1:
            raise ValueError("Enter at least two characters to search")
        state = self._read()
        results: list[dict[str, Any]] = []
        if kind in {"all", "messages", "files"}:
            for record in reversed(state.get("messages", [])[-1000:]):
                if persona_id not in {record.get("sender_persona_id"), record.get("recipient_persona_id")}:
                    continue
                public = self._public_message(record)
                is_file = public.get("kind") == "attachment"
                if kind == "files" and not is_file or kind == "messages" and is_file:
                    continue
                card = dict(public.get("card") or {})
                searchable = " ".join([str(public.get("body") or ""), str(card.get("title") or ""), *[str(item.get("filename") or "") for item in public.get("attachments", [])]]).casefold()
                if (not query or query in searchable) and (not status or public.get("status") == status):
                    results.append({"result_type": "file" if is_file else "message", **public})
        if kind in {"all", "tasks"}:
            for record in reversed(state.get("actions", [])[-1000:]):
                if persona_id not in {record.get("owner_persona_id"), record.get("recipient_persona_id")}:
                    continue
                public = self._public_action(record)
                if (not query or query in str(public.get("title") or "").casefold()) and (not status or public.get("status") == status):
                    results.append({"result_type": "task", **public})
        results.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return {"schema_version": "pilot.inbox-search.v1", "query": query, "kind": kind, "count": min(len(results), 50), "results": results[:50]}

    def _public_action(self, action: dict[str, Any], *, include_content: bool = True) -> dict[str, Any]:
        result = {key: action.get(key) for key in (
            "action_id", "kind", "owner_persona_id", "recipient_persona_id", "recipient_mother_id",
            "space_id", "privacy", "scope_hash", "status", "created_at", "expires_at", "delivered_at", "responded_at",
            "read_at", "corrected_at", "snoozed_until", "completed_at", "cancelled_at", "failed_at", "expired_at",
            "proof_commitment_ids",
        ) if action.get(key) is not None}
        if include_content:
            aad = {"action_id": action["action_id"], "owner_persona_id": action["owner_persona_id"], "kind": action["kind"]}
            result.update(self._decrypt_local(action, aad))
        return result

    def approve_and_export_task(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="message.send",
            request=request, phone_signature=phone_signature,
        )
        action_id = str(request.get("action_id") or "")
        scope_hash = str(request.get("scope_hash") or "")
        with self._lock:
            state = self._read()
            action = next((item for item in state["actions"] if item.get("action_id") == action_id), None)
            if not action or action.get("owner_persona_id") != persona_id:
                raise PermissionError("That task proposal does not belong to this identity")
            if action.get("scope_hash") != scope_hash:
                raise PermissionError("The approved task is not the task now being sent")
            if action.get("status") == "delivered":
                return dict(action["delivery_packet"])
            if action.get("status") != "awaiting_approval":
                raise PermissionError("That task is no longer waiting for approval")
            peer = next((item for item in state["peers"] if item.get("mother_id") == action["recipient_mother_id"] and item.get("status") == "trusted"), None)
            if not peer:
                raise PermissionError("The recipient's Pilot is not trusted by this mother")
            content = self._public_action(action)
            packet = self._encrypt_packet(
                peer=peer,
                payload={"type": "task_proposal", **content},
                recipient_persona_id=str(action["recipient_persona_id"]),
            )
            action["status"] = "delivered"
            action["delivered_at"] = utc_now_iso()
            action["delivery_packet"] = packet
            proof_key = canonical_hash(request)[:32]
            authorization = self._proof(
                event="authorization", action=action, outcome="approved",
                private_record=request, idempotency_key=f"proof-auth-{proof_key}",
            )
            delivery_receipt = self._receipt(action_id, persona_id, "delivered", packet["packet_hash"])
            self._proof(
                event="delivery", action=action, outcome="delivered_to_recipient_mother",
                private_record=delivery_receipt, idempotency_key=f"proof-delivery-{proof_key}",
                previous_commitment_id=authorization,
            )
            state["receipts"].append(delivery_receipt)
            self._write(state)
            return packet

    def _derive_transport_key(self, private: X25519PrivateKey, public: X25519PublicKey, packet_id: str) -> bytes:
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=canonical_bytes({"protocol": "pilot-inbox-v1", "packet_id": packet_id})).derive(private.exchange(public))

    def _encrypt_packet(self, *, peer: dict[str, Any], payload: dict[str, Any], recipient_persona_id: str) -> dict[str, Any]:
        packet_id = f"packet_{uuid4().hex}"
        ephemeral = X25519PrivateKey.generate()
        peer_public = X25519PublicKey.from_public_bytes(base64.b64decode(peer["transport_public_key"]))
        metadata = {
            "schema_version": "pilot.inbox-packet.v1",
            "packet_id": packet_id,
            "sender_mother_id": self.mother_id,
            "recipient_mother_id": peer["mother_id"],
            "recipient_persona_id": recipient_persona_id,
            "sent_at": utc_now_iso(),
            "ephemeral_public_key": base64.b64encode(ephemeral.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii"),
        }
        nonce = secrets.token_bytes(12)
        key = self._derive_transport_key(ephemeral, peer_public, packet_id)
        ciphertext = AESGCM(key).encrypt(nonce, canonical_bytes(payload), canonical_bytes(metadata))
        unsigned = {
            **metadata,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        packet_hash = canonical_hash(unsigned)
        return {**unsigned, "packet_hash": packet_hash, "signature": self.identity.sign(canonical_bytes({**unsigned, "packet_hash": packet_hash}))}

    def receive_packet(self, packet: dict[str, Any]) -> dict[str, Any]:
        signature = str(packet.get("signature") or "")
        unsigned = {key: value for key, value in packet.items() if key != "signature"}
        packet_hash = str(unsigned.pop("packet_hash", ""))
        if packet.get("schema_version") != "pilot.inbox-packet.v1" or packet.get("recipient_mother_id") != self.mother_id:
            raise PermissionError("That packet is not addressed to this mother")
        if not secrets.compare_digest(packet_hash, canonical_hash(unsigned)):
            raise PermissionError("The Pilot packet was changed in transit")
        with self._lock:
            state = self._read()
            if packet["packet_id"] in state.get("received_packets", []):
                action = next((item for item in state["actions"] if item.get("source_packet_id") == packet["packet_id"] or packet["packet_id"] in item.get("source_update_packet_ids", [])), None)
                if action:
                    return self._public_action(action)
                message = next(item for item in state["messages"] if item.get("source_packet_id") == packet["packet_id"])
                return self._public_message(message)
            peer = next((item for item in state["peers"] if item.get("mother_id") == packet.get("sender_mother_id") and item.get("status") == "trusted"), None)
            if not peer or not DeviceIdentity.verify(peer["signing_public_key"], canonical_bytes({**unsigned, "packet_hash": packet_hash}), signature):
                raise PermissionError("Pilot could not verify the sending mother")
            metadata_keys = (
                "schema_version", "packet_id", "sender_mother_id", "recipient_mother_id",
                "recipient_persona_id", "sent_at", "ephemeral_public_key",
            )
            metadata = {key: packet[key] for key in metadata_keys}
            ephemeral = X25519PublicKey.from_public_bytes(base64.b64decode(packet["ephemeral_public_key"]))
            key = self._derive_transport_key(self._transport_private, ephemeral, str(packet["packet_id"]))
            plaintext = AESGCM(key).decrypt(base64.b64decode(packet["nonce"]), base64.b64decode(packet["ciphertext"]), canonical_bytes(metadata))
            payload = json.loads(plaintext)
            if payload.get("type") not in {"task_proposal", "task_update", "text", "attachment", "voice_note", "structured_card"} or payload.get("recipient_persona_id") != packet["recipient_persona_id"]:
                raise PermissionError("The decrypted Pilot task does not match its destination")
            if payload["type"] == "structured_card":
                card = dict(payload.get("card") or {})
                card_type = str(card.get("card_type") or "")
                if card_type not in self.STRUCTURED_CARD_TYPES or not secrets.compare_digest(str(payload.get("content_hash") or ""), canonical_hash(card)):
                    raise PermissionError("That structured card could not be verified")
                aad = {
                    "message_id": payload["message_id"], "sender_persona_id": payload["sender_persona_id"],
                    "recipient_persona_id": payload["recipient_persona_id"],
                }
                message = {
                    **aad, "conversation_id": payload["conversation_id"], "sender_mother_id": packet["sender_mother_id"],
                    "recipient_mother_id": self.mother_id, "kind": card_type, "space_id": payload["recipient_space_id"],
                    "privacy": payload["privacy"], "status": "delivered", "created_at": payload["created_at"],
                    "content_hash": payload["content_hash"], "source_packet_id": packet["packet_id"],
                    **self._encrypt_local({"body": str(card.get("detail") or ""), "card": card}, aad),
                }
                state["messages"].append(message)
                state["received_packets"] = (state.get("received_packets", []) + [packet["packet_id"]])[-4096:]
                state["receipts"].append(self._receipt(str(message["message_id"]), str(packet["recipient_persona_id"]), "delivered", packet_hash))
                self._write(state)
                return self._public_message(message)
            if payload["type"] in {"attachment", "voice_note"}:
                request_shape = {
                    "filename": payload.get("filename"), "media_type": payload.get("media_type"),
                    "content_base64": payload.get("content_base64"), "duration_ms": payload.get("duration_ms"),
                }
                if payload["type"] == "voice_note":
                    filename, media_type, raw, content_hash, duration_ms = self._decode_voice_note(request_shape)
                else:
                    filename, media_type, raw, content_hash = self._decode_attachment(request_shape)
                    duration_ms = None
                if not secrets.compare_digest(content_hash, str(payload.get("content_hash") or "")) or len(raw) != int(payload.get("byte_length") or -1):
                    raise PermissionError("The attachment does not match its signed description")
                attachment_id = str(payload.get("attachment_id") or "")
                message_id = str(payload.get("message_id") or "")
                if not _ID.fullmatch(attachment_id) or not _ID.fullmatch(message_id):
                    raise ValueError("The attachment identifiers are invalid")
                aad = {
                    "message_id": message_id,
                    "sender_persona_id": payload["sender_persona_id"],
                    "recipient_persona_id": payload["recipient_persona_id"],
                }
                attachment_aad = {
                    "attachment_id": attachment_id,
                    "owner_persona_id": payload["sender_persona_id"],
                    "content_hash": content_hash,
                }
                attachment = {
                    **attachment_aad, "message_id": message_id, "filename": filename, "media_type": media_type,
                    "byte_length": len(raw), "storage_ref": self._store_attachment(attachment_id=attachment_id, raw=raw, aad=attachment_aad),
                    "created_at": payload["created_at"], "encrypted": True,
                }
                if duration_ms is not None:
                    attachment["duration_ms"] = duration_ms
                    attachment["expires_at"] = str(payload.get("expires_at") or "")
                message = {
                    **aad, "conversation_id": payload["conversation_id"], "kind": payload["type"],
                    "sender_mother_id": packet["sender_mother_id"], "recipient_mother_id": self.mother_id,
                    "space_id": payload["recipient_space_id"], "privacy": payload["privacy"], "status": "delivered",
                    "created_at": payload["created_at"], "content_hash": content_hash,
                    "attachment_refs": [attachment_id], "source_packet_id": packet["packet_id"],
                    **self._encrypt_local({"body": ""}, aad),
                }
                state.setdefault("attachments", []).append(attachment)
                state["messages"].append(message)
                state["received_packets"] = (state.get("received_packets", []) + [packet["packet_id"]])[-4096:]
                state["receipts"].append(self._receipt(message_id, str(packet["recipient_persona_id"]), "delivered", packet_hash))
                self._write(state)
                return self._public_message(message)
            if payload["type"] == "text":
                if payload.get("recipient_space_id") != f"personal/{packet['recipient_persona_id']}" or payload.get("privacy") != "private":
                    raise PermissionError("The message space does not match its recipient")
                aad = {
                    "message_id": payload["message_id"],
                    "sender_persona_id": payload["sender_persona_id"],
                    "recipient_persona_id": payload["recipient_persona_id"],
                }
                message = {
                    **aad,
                    "conversation_id": payload["conversation_id"],
                    "sender_mother_id": packet["sender_mother_id"],
                    "recipient_mother_id": self.mother_id,
                    "kind": "text",
                    "space_id": payload["recipient_space_id"],
                    "privacy": payload["privacy"],
                    "status": "delivered",
                    "created_at": payload["created_at"],
                    "content_hash": payload["content_hash"],
                    "source_packet_id": packet["packet_id"],
                    **self._encrypt_local({"body": payload["body"]}, aad),
                }
                state["messages"].append(message)
                state["received_packets"] = (state.get("received_packets", []) + [packet["packet_id"]])[-4096:]
                state["receipts"].append(self._receipt(message["message_id"], str(packet["recipient_persona_id"]), "delivered", packet_hash))
                self._write(state)
                return self._public_message(message)
            if payload["type"] == "task_update":
                action = next((item for item in state["actions"] if item.get("action_id") == payload.get("action_id") and item.get("sender_mother_id") == packet.get("sender_mother_id")), None)
                if not action or payload.get("sender_persona_id") != action.get("owner_persona_id"):
                    raise PermissionError("That task update does not match a received task")
                event = str(payload.get("event") or "")
                if event == "corrected":
                    if action.get("status") in {"completed", "cancelled", "declined", "expired"}:
                        raise PermissionError("That task can no longer be corrected")
                    title = self._clean(str(payload.get("title") or ""), 240)
                    if len(title) < 2:
                        raise ValueError("The corrected task is empty")
                    self.pilot_inbox.revise_title(
                        task_id=str(action["local_task_id"]),
                        actor_persona_id=str(action["owner_persona_id"]),
                        title=title,
                    )
                    aad = {"action_id": action["action_id"], "owner_persona_id": action["owner_persona_id"], "kind": action["kind"]}
                    action.update(self._encrypt_local({"title": title}, aad))
                    action["corrected_at"] = str(payload.get("recorded_at") or utc_now_iso())
                elif event == "cancelled":
                    self.pilot_inbox.cancel(
                        task_id=str(action["local_task_id"]),
                        actor_persona_id=str(action["owner_persona_id"]),
                    )
                    action["status"] = "cancelled"
                    action["cancelled_at"] = str(payload.get("recorded_at") or utc_now_iso())
                else:
                    raise ValueError("That sender task update is unsupported")
                state["received_packets"] = (state.get("received_packets", []) + [packet["packet_id"]])[-4096:]
                action["source_update_packet_ids"] = (list(action.get("source_update_packet_ids") or []) + [packet["packet_id"]])[-128:]
                state["receipts"].append(self._receipt(str(action["action_id"]), str(action["recipient_persona_id"]), event, packet_hash))
                self._write(state)
                return self._public_action(action)
            local_task = self.pilot_inbox.import_pilot_delegation(
                recipient_persona_id=str(packet["recipient_persona_id"]),
                sender_persona_id=str(payload["owner_persona_id"]),
                title=str(payload["title"]),
                external_task_ref=str(payload["action_id"]),
                source_receipt_hash=packet_hash,
            )
            aad = {"action_id": payload["action_id"], "owner_persona_id": payload["owner_persona_id"], "kind": "task_proposal"}
            action = {
                **aad,
                "space_id": f"personal/{packet['recipient_persona_id']}",
                "privacy": "private",
                "recipient_persona_id": packet["recipient_persona_id"],
                "recipient_mother_id": self.mother_id,
                "sender_mother_id": packet["sender_mother_id"],
                "scope_hash": payload["scope_hash"],
                "status": "awaiting_recipient_acceptance",
                "created_at": payload["created_at"],
                "expires_at": payload.get("expires_at"),
                "delivered_at": utc_now_iso(),
                "source_packet_id": packet["packet_id"],
                "source_packet_hash": packet_hash,
                "local_task_id": local_task["task_id"],
                **self._encrypt_local({"title": payload["title"]}, aad),
            }
            state["actions"].append(action)
            state["received_packets"] = (state.get("received_packets", []) + [packet["packet_id"]])[-4096:]
            state["receipts"].append(self._receipt(action["action_id"], str(packet["recipient_persona_id"]), "delivered", packet_hash))
            self._write(state)
            return {**self._public_action(action), "local_task_id": local_task["task_id"]}

    def transition_task(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        event = str(request.get("event") or "")
        if event not in {"read", "corrected", "cancelled", "snoozed", "completed", "failed", "expired"}:
            raise ValueError("Choose a supported task update")
        scope = "task.create" if event in {"corrected", "cancelled"} else "task.respond"
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope=scope,
            request=request, phone_signature=phone_signature,
        )
        key, request_hash = self._request_key(request)
        action_id = str(request.get("action_id") or "")
        with self._lock:
            state = self._read()
            used = next((item for item in state.get("used_requests", []) if item.get("idempotency_key") == key), None)
            if used:
                if used.get("request_hash") != request_hash:
                    raise PermissionError("That task update key was already used for different content")
                previous = next(item for item in state["receipts"] if item.get("receipt_id") == used.get("object_id"))
                return dict(previous)
            action = next((item for item in state["actions"] if item.get("action_id") == action_id), None)
            if not action:
                raise KeyError("That task is not available")
            is_sender = action.get("owner_persona_id") == persona_id and action.get("recipient_mother_id") != self.mother_id
            is_recipient = action.get("recipient_persona_id") == persona_id and action.get("recipient_mother_id") == self.mother_id
            if event in {"corrected", "cancelled"} and not is_sender:
                raise PermissionError("Only the task sender can make that update")
            if event in {"read", "snoozed", "completed", "failed", "expired"} and not is_recipient:
                raise PermissionError("Only the task recipient can make that update")

            now = utc_now_iso()
            evidence_hash = str(action.get("source_packet_hash") or action.get("scope_hash") or "")
            if event == "corrected":
                if action.get("status") in {"completed", "cancelled", "declined", "expired"}:
                    raise PermissionError("That task can no longer be corrected")
                title = self._clean(str(request.get("title") or ""), 240)
                if len(title) < 2:
                    raise ValueError("Enter the corrected task")
                aad = {"action_id": action["action_id"], "owner_persona_id": action["owner_persona_id"], "kind": action["kind"]}
                action.update(self._encrypt_local({"title": title}, aad))
                action["corrected_at"] = now
                packet_payload = {
                    "type": "task_update", "event": event, "action_id": action_id,
                    "sender_persona_id": persona_id, "recipient_persona_id": action["recipient_persona_id"],
                    "title": title, "recorded_at": now,
                }
            elif event == "cancelled":
                if action.get("status") in {"completed", "cancelled", "declined", "expired"}:
                    raise PermissionError("That task is already closed")
                action["status"] = "cancelled"
                action["cancelled_at"] = now
                packet_payload = {
                    "type": "task_update", "event": event, "action_id": action_id,
                    "sender_persona_id": persona_id, "recipient_persona_id": action["recipient_persona_id"],
                    "recorded_at": now,
                }
            else:
                if action.get("status") not in {"awaiting_recipient_acceptance", "accepted", "snoozed"}:
                    raise PermissionError("That task cannot receive this update")
                if event == "read":
                    action["read_at"] = now
                elif event == "snoozed":
                    until = str(request.get("until") or "")
                    self.pilot_inbox.snooze(task_id=str(action["local_task_id"]), actor_persona_id=persona_id, until=until)
                    action["status"] = "snoozed"
                    action["snoozed_until"] = until
                elif event == "completed":
                    self.pilot_inbox.complete(task_id=str(action["local_task_id"]), actor_persona_id=persona_id)
                    action["status"] = "completed"
                    action["completed_at"] = now
                elif event == "failed":
                    action["status"] = "failed"
                    action["failed_at"] = now
                else:
                    expires_at = datetime.fromisoformat(str(action.get("expires_at") or "").replace("Z", "+00:00"))
                    if expires_at > datetime.now(timezone.utc):
                        raise PermissionError("That task has not expired")
                    action["status"] = "expired"
                    action["expired_at"] = now
                receipt = self._signed_task_receipt(action, persona_id=persona_id, state_name=event, evidence_hash=evidence_hash)
                self._proof(
                    event="outcome", action=action, outcome=event,
                    private_record=receipt, idempotency_key=f"proof-outcome-{key}",
                    previous_commitment_id=(action.get("proof_commitment_ids") or [None])[-1],
                )
                state["receipts"].append(receipt)
                state["used_requests"].append({"idempotency_key": key, "request_hash": request_hash, "object_id": receipt["receipt_id"]})
                state["used_requests"] = state["used_requests"][-4096:]
                self._write(state)
                return receipt

            peer = next((item for item in state["peers"] if item.get("mother_id") == action["recipient_mother_id"] and item.get("status") == "trusted"), None)
            if not peer:
                raise PermissionError("The recipient's Pilot is not trusted by this mother")
            packet = self._encrypt_packet(peer=peer, payload=packet_payload, recipient_persona_id=str(action["recipient_persona_id"]))
            receipt = self._receipt(action_id, persona_id, event, packet["packet_hash"])
            receipt["delivery_packet"] = packet
            state["receipts"].append(receipt)
            state["used_requests"].append({"idempotency_key": key, "request_hash": request_hash, "object_id": receipt["receipt_id"]})
            state["used_requests"] = state["used_requests"][-4096:]
            self._write(state)
            return receipt

    def _signed_task_receipt(self, action: dict[str, Any], *, persona_id: str, state_name: str, evidence_hash: str) -> dict[str, Any]:
        receipt = self._receipt(str(action["action_id"]), persona_id, state_name, evidence_hash)
        receipt["sender_mother_id"] = self.mother_id
        receipt["recipient_mother_id"] = action["sender_mother_id"]
        if state_name == "snoozed":
            receipt["snoozed_until"] = action.get("snoozed_until")
        receipt["signature"] = self.identity.sign(canonical_bytes(receipt))
        return receipt

    def respond_to_task(
        self,
        request: dict[str, Any],
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize(
            certificate=certificate, lease=lease, scope="task.respond",
            request=request, phone_signature=phone_signature,
        )
        action_id = str(request.get("action_id") or "")
        decision = str(request.get("decision") or "")
        if decision not in {"accepted", "declined"}:
            raise ValueError("Choose accept or decline")
        key, request_hash = self._request_key(request)
        with self._lock:
            state = self._read()
            used = next((item for item in state.get("used_requests", []) if item.get("idempotency_key") == key), None)
            if used:
                if used.get("request_hash") != request_hash:
                    raise PermissionError("That task response key was already used for different content")
                return dict(next(item for item in state["receipts"] if item.get("receipt_id") == used.get("object_id")))
            action = next((item for item in state["actions"] if item.get("action_id") == action_id and item.get("recipient_persona_id") == persona_id), None)
            if not action or action.get("status") != "awaiting_recipient_acceptance":
                raise PermissionError("No task request is waiting for this identity")
            self.pilot_inbox.respond_to_delegation(
                task_id=str(action["local_task_id"]), recipient_persona_id=persona_id,
                accept=decision == "accepted",
            )
            action["status"] = decision
            action["responded_at"] = utc_now_iso()
            receipt = self._receipt(action_id, persona_id, decision, action["source_packet_hash"])
            receipt["sender_mother_id"] = self.mother_id
            receipt["recipient_mother_id"] = action["sender_mother_id"]
            receipt["signature"] = self.identity.sign(canonical_bytes(receipt))
            self._proof(
                event="acceptance", action=action, outcome=decision,
                private_record=receipt, idempotency_key=f"proof-acceptance-{key}",
                previous_commitment_id=(action.get("proof_commitment_ids") or [None])[-1],
            )
            state["receipts"].append(receipt)
            state["used_requests"].append({"idempotency_key": key, "request_hash": request_hash, "object_id": receipt["receipt_id"]})
            state["used_requests"] = state["used_requests"][-4096:]
            self._write(state)
            return receipt

    def reconcile_receipt(self, receipt: dict[str, Any]) -> dict[str, Any]:
        signature = str(receipt.get("signature") or "")
        unsigned = {key: value for key, value in receipt.items() if key != "signature"}
        with self._lock:
            state = self._read()
            peer = next((item for item in state["peers"] if item.get("mother_id") == receipt.get("sender_mother_id") and item.get("status") == "trusted"), None)
            if not peer or receipt.get("recipient_mother_id") != self.mother_id or not DeviceIdentity.verify(peer["signing_public_key"], canonical_bytes(unsigned), signature):
                raise PermissionError("Pilot could not verify the task response")
            action = next((item for item in state["actions"] if item.get("action_id") == receipt.get("action_id") and item.get("recipient_mother_id") == receipt.get("sender_mother_id")), None)
            supported = {"accepted", "declined", "read", "snoozed", "completed", "failed", "expired"}
            if not action or receipt.get("state") not in supported:
                raise PermissionError("The response does not match a sent task")
            if receipt["state"] == "read":
                action["read_at"] = receipt["recorded_at"]
            else:
                action["status"] = receipt["state"]
                timestamp_field = {
                    "snoozed": "snoozed_at", "completed": "completed_at", "failed": "failed_at", "expired": "expired_at",
                }.get(str(receipt["state"]), "responded_at")
                action[timestamp_field] = receipt["recorded_at"]
                if receipt["state"] == "snoozed":
                    action["snoozed_until"] = receipt.get("snoozed_until")
            action["responded_at"] = receipt["recorded_at"]
            state["receipts"].append(dict(receipt))
            self._write(state)
            return self._public_action(action)

    @staticmethod
    def _receipt(action_id: str, actor_persona_id: str, state: str, evidence_hash: str) -> dict[str, Any]:
        return {
            "schema_version": "pilot.inbox-receipt.v1",
            "receipt_id": f"receipt_{uuid4().hex}",
            "action_id": action_id,
            "actor_persona_id": actor_persona_id,
            "state": state,
            "evidence_hash": evidence_hash,
            "recorded_at": utc_now_iso(),
            "private_content_included": False,
        }

    def stream(
        self,
        *,
        persona_id: str,
        certificate: dict[str, Any],
        lease: dict[str, Any],
    ) -> dict[str, Any]:
        verified = self.pairing.validate(certificate=certificate, lease=lease, required_scope="inbox.read")
        if verified["persona_id"] != persona_id:
            raise PermissionError("This phone cannot read another person's inbox")
        state = self._read()
        actions = [
            self._public_action(item)
            for item in state.get("actions", [])
            if persona_id in {item.get("owner_persona_id"), item.get("recipient_persona_id")}
        ]
        messages = [
            self._public_message(item)
            for item in state.get("messages", [])
            if persona_id in {item.get("sender_persona_id"), item.get("recipient_persona_id")}
        ]
        receipts = [
            {key: item.get(key) for key in ("receipt_id", "action_id", "actor_persona_id", "state", "recorded_at", "private_content_included")}
            for item in state.get("receipts", [])
            if item.get("actor_persona_id") == persona_id or any(action["action_id"] == item.get("action_id") for action in actions)
        ]
        return {
            "persona_id": persona_id,
            "revision": state.get("revision", 0),
            "messages": messages[-300:],
            "actions": actions[-300:],
            "receipts": receipts[-300:],
        }
