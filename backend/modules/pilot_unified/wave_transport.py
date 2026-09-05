from __future__ import annotations

import base64
import json
import os
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity


WAVE_VERSION = "pilot.optional-wave-transport.v1"
PRIORITIES = {"emergency": 0, "urgent": 1, "normal": 2, "bulk": 3}


class OptionalWaveTransport:
    """Hidden, hardware-gated store-and-forward transport for bounded Pilot payloads."""

    def __init__(self, runtime_dir: str | Path, *, mother_identity: DeviceIdentity, mtu: int = 180) -> None:
        if not 96 <= mtu <= 1024:
            raise ValueError("Wave MTU is outside the supported bound")
        self.root = Path(runtime_dir) / "pilot_wave_transport"
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.path = self.root / "state.json"
        self.identity = mother_identity
        self.mtu = mtu

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": WAVE_VERSION, "bridges": [], "trusted_senders": [], "queue": [], "seen": [], "receipts": [], "hardware_qualified": False}
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("schema_version") != WAVE_VERSION:
            raise RuntimeError("Wave transport state has an unsupported format")
        return state

    def _write(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    def product_manifest(self) -> dict[str, Any]:
        state = self._read()
        return {
            "visible_in_ordinary_setup": False,
            "radio_capability_advertised": bool(state["hardware_qualified"]),
            "mock_driver_counts_as_hardware": False,
            "pho_enabled": False,
            "wallet_enabled": False,
        }

    def foundation_receipt(self) -> dict[str, Any]:
        """Describe the adapted transport primitives without claiming RF delivery."""
        state = self._read()
        return {
            "schema_version": "pilot.wave-foundation-receipt.v1",
            "transport_version": WAVE_VERSION,
            "framing": "bounded_indexed_fragments",
            "integrity": "sha256_fragment_and_payload",
            "authentication": "ed25519_message_bundle",
            "queue": "priority_ttl_retry_idempotent",
            "store_and_forward": True,
            "configured_bridges": len(state.get("bridges") or []),
            "queued_messages": len(state.get("queue") or []),
            "physical_radio_driver_active": False,
            "internet_disconnected_delivery_verified": False,
            "radio_capability_advertised": bool(state.get("hardware_qualified")),
        }

    def enroll_bridge(
        self, *, bridge_id: str, bridge_public_key: str, capabilities: list[str],
        local_confirmation: bool, expires_hours: int = 24,
    ) -> dict[str, Any]:
        allowed = sorted(set(capabilities) & {"wave.send", "wave.receive", "wave.ptt"})
        if not local_confirmation or not allowed or not 1 <= expires_hours <= 24:
            raise PermissionError("Wave bridge enrollment requires bounded local confirmation")
        now = datetime.now(timezone.utc)
        payload = {
            "schema_version": "pilot.wave-bridge-lease.v1", "bridge_id": bridge_id,
            "bridge_public_key": bridge_public_key, "capabilities": allowed,
            "issued_at": now.isoformat(), "expires_at": (now + timedelta(hours=expires_hours)).isoformat(),
            "status": "active", "hardware_qualified": False,
        }
        lease = {**payload, "signature": self.identity.sign(canonical_bytes(payload))}
        state = self._read()
        state["bridges"] = [item for item in state["bridges"] if item["bridge_id"] != bridge_id] + [lease]
        self._write(state)
        return {key: lease[key] for key in ("bridge_id", "capabilities", "issued_at", "expires_at", "status", "hardware_qualified", "signature")}

    def revoke_bridge(self, bridge_id: str) -> None:
        state = self._read()
        bridge = next((item for item in state["bridges"] if item["bridge_id"] == bridge_id), None)
        if bridge:
            bridge["status"] = "revoked"
            bridge["revoked_at"] = utc_now_iso()
            state["queue"] = [item for item in state["queue"] if item["bridge_id"] != bridge_id]
            self._write(state)

    def trust_sender(self, *, sender_ref: str, signing_public_key: str, local_confirmation: bool) -> dict[str, Any]:
        if not local_confirmation:
            raise PermissionError("Wave sender trust requires local confirmation")
        record = {
            "sender_ref": sender_ref, "signing_public_key": signing_public_key,
            "status": "trusted", "trusted_at": utc_now_iso(),
        }
        state = self._read()
        state["trusted_senders"] = [item for item in state["trusted_senders"] if item["sender_ref"] != sender_ref] + [record]
        self._write(state)
        return {"sender_ref": sender_ref, "status": "trusted", "trusted_at": record["trusted_at"]}

    def enqueue(
        self, *, bridge_id: str, recipient_ref: str, payload: bytes,
        content_type: str, priority: str = "normal", ttl_seconds: int = 300,
        max_retries: int = 4, idempotency_key: str,
    ) -> dict[str, Any]:
        if priority not in PRIORITIES or not 10 <= ttl_seconds <= 86400 or not 0 <= max_retries <= 10:
            raise ValueError("Wave queue policy is invalid")
        if not payload or len(payload) > 1_500_000:
            raise ValueError("Wave payload is outside the supported bound")
        state = self._read()
        bridge = next((item for item in state["bridges"] if item["bridge_id"] == bridge_id and item["status"] == "active"), None)
        if not bridge or "wave.send" not in bridge["capabilities"]:
            raise PermissionError("No active bridge may send this payload")
        existing = next((item for item in state["queue"] if item["idempotency_key"] == idempotency_key), None)
        payload_hash = hashlib.sha256(payload).hexdigest()
        if existing:
            if existing["payload_hash"] != payload_hash:
                raise PermissionError("Wave idempotency key was used for different content")
            return self._public(existing)
        now = datetime.now(timezone.utc)
        message_id = f"wave_{uuid4().hex}"
        chunk_size = max(32, self.mtu - 80)
        total = (len(payload) + chunk_size - 1) // chunk_size
        fragments = []
        for index in range(total):
            chunk = payload[index * chunk_size:(index + 1) * chunk_size]
            header = {"version": 1, "message_id": message_id, "index": index, "total": total, "payload_hash": payload_hash}
            fragments.append({**header, "data": base64.b64encode(chunk).decode("ascii"), "fragment_hash": canonical_hash({**header, "data": base64.b64encode(chunk).decode("ascii")})})
        record = {
            "message_id": message_id, "bridge_id": bridge_id,
            "recipient_ref": "recipient_" + canonical_hash({"recipient": recipient_ref})[:24],
            "content_type": content_type, "payload_hash": payload_hash, "fragments": fragments,
            "priority": priority, "ttl_seconds": ttl_seconds, "max_retries": max_retries,
            "attempts": 0, "idempotency_key": idempotency_key, "status": "queued",
            "next_fragment": 0,
            "created_at": now.isoformat(), "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
        }
        record["signature"] = self.identity.sign(canonical_bytes({key: value for key, value in record.items() if key != "signature"}))
        state["queue"].append(record)
        state["queue"].sort(key=lambda item: (PRIORITIES[item["priority"]], item["created_at"]))
        self._write(state)
        return self._public(record)

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        return {key: record[key] for key in ("message_id", "bridge_id", "recipient_ref", "payload_hash", "priority", "attempts", "max_retries", "status", "created_at", "expires_at")}

    def next_frame(self, bridge_id: str) -> dict[str, Any] | None:
        state = self._read()
        now = datetime.now(timezone.utc)
        for record in state["queue"]:
            if record["bridge_id"] != bridge_id or record["status"] not in {"queued", "retrying"}:
                continue
            if datetime.fromisoformat(record["expires_at"]) <= now:
                record["status"] = "expired"
                continue
            if record["attempts"] >= record["max_retries"] + 1:
                record["status"] = "failed"
                continue
            frame_index = int(record.get("next_fragment") or 0)
            if frame_index >= len(record["fragments"]):
                record["attempts"] += 1
                record["next_fragment"] = 0
                record["status"] = "retrying"
                frame_index = 0
            record["next_fragment"] = frame_index + 1
            self._write(state)
            return {"message_id": record["message_id"], "fragment": record["fragments"][frame_index], "delivery_state": "radio_attempted_unverified"}
        self._write(state)
        return None

    def outbound_bundle(self, message_id: str) -> dict[str, Any]:
        state = self._read()
        record = next((item for item in state["queue"] if item["message_id"] == message_id), None)
        if not record:
            raise KeyError("Wave message is not queued")
        signed = {
            "message_id": message_id, "payload_hash": record["payload_hash"],
            "fragment_hashes": [item["fragment_hash"] for item in record["fragments"]],
        }
        return {"fragments": list(record["fragments"]), "message_signature": self.identity.sign(canonical_bytes(signed))}

    def reconstruct(self, *, bridge_id: str, fragments: list[dict[str, Any]], sender_ref: str, message_signature: str) -> dict[str, Any]:
        state = self._read()
        bridge = next((item for item in state["bridges"] if item["bridge_id"] == bridge_id and item["status"] == "active"), None)
        if not bridge or "wave.receive" not in bridge["capabilities"]:
            raise PermissionError("No active bridge may receive this payload")
        sender = next((item for item in state["trusted_senders"] if item["sender_ref"] == sender_ref and item["status"] == "trusted"), None)
        if not sender:
            raise PermissionError("Wave sender is not trusted")
        if not fragments:
            raise ValueError("No Wave fragments were supplied")
        ordered = sorted(fragments, key=lambda item: int(item["index"]))
        first = ordered[0]
        total = int(first["total"])
        if len(ordered) != total or [int(item["index"]) for item in ordered] != list(range(total)):
            raise ValueError("Wave fragment sequence is incomplete")
        for item in ordered:
            header = {key: item[key] for key in ("version", "message_id", "index", "total", "payload_hash")}
            if item["message_id"] != first["message_id"] or item["payload_hash"] != first["payload_hash"] or canonical_hash({**header, "data": item["data"]}) != item["fragment_hash"]:
                raise PermissionError("Wave fragment integrity failed")
        if first["message_id"] in state["seen"]:
            return {"message_id": first["message_id"], "status": "duplicate_discarded"}
        signed = {"message_id": first["message_id"], "payload_hash": first["payload_hash"], "fragment_hashes": [item["fragment_hash"] for item in ordered]}
        if not DeviceIdentity.verify(sender["signing_public_key"], canonical_bytes(signed), message_signature):
            raise PermissionError("Wave message signature is invalid")
        raw = b"".join(base64.b64decode(item["data"], validate=True) for item in ordered)
        if hashlib.sha256(raw).hexdigest() != first["payload_hash"]:
            raise PermissionError("Wave reconstructed payload hash failed")
        state["seen"] = (state["seen"] + [first["message_id"]])[-4096:]
        state["receipts"].append({"message_id": first["message_id"], "state": "radio_reconstructed_locally", "payload_hash": first["payload_hash"], "recorded_at": utc_now_iso(), "physical_delivery_verified": False})
        self._write(state)
        return {"message_id": first["message_id"], "status": "radio_reconstructed_locally", "payload": raw, "physical_delivery_verified": False}
