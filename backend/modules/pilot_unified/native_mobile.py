from __future__ import annotations

import base64
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity


NATIVE_POLICY_VERSION = "pilot.native-mobile-policy.v1"
DEEPLINK_KINDS = frozenset({"pairing", "invitation", "task", "approval", "tv_takeover"})
SENSITIVE_NOTIFICATION_KINDS = frozenset({"message", "task", "approval", "calendar", "guardian"})
PERMISSIONS = frozenset({"camera_observer", "microphone_voice", "microphone_ptt", "notifications", "location"})
_REF = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")


class NativeMobileSecurityAuthority:
    """Platform-neutral security contract for future signed iOS/Android clients."""

    def __init__(self, runtime_dir: str | Path, *, mother_identity: DeviceIdentity, device_id: str) -> None:
        if not _REF.fullmatch(device_id):
            raise ValueError("Native device identifier is invalid")
        self.root = Path(runtime_dir) / "pilot_native_mobile" / device_id
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.state_path = self.root / "state.json"
        self.cache_key_path = self.root / "cache.key"
        self.identity = mother_identity
        self.device_id = device_id
        self.cache_key = self._key()

    def _key(self) -> bytes:
        if self.cache_key_path.exists():
            raw = self.cache_key_path.read_bytes()
            if len(raw) != 32:
                raise RuntimeError("Native cache key is invalid")
            os.chmod(self.cache_key_path, 0o600)
            return raw
        raw = secrets.token_bytes(32)
        self.cache_key_path.write_bytes(raw)
        os.chmod(self.cache_key_path, 0o600)
        return raw

    def _read(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {
                "schema_version": NATIVE_POLICY_VERSION,
                "permissions": {name: {"status": "not_requested", "indicator": False} for name in PERMISSIONS},
                "lifecycle": [], "used_links": [], "app_locked": True,
                "biometric_challenges": [], "used_biometric_nonces": [],
                "push_channels": [], "background_events": [],
            }
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if state.get("schema_version") != NATIVE_POLICY_VERSION:
            raise RuntimeError("Native mobile state has an unsupported format")
        return state

    def _write(self, state: dict[str, Any]) -> None:
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.state_path)

    def issue_deep_link(self, *, kind: str, object_ref: str, expires_minutes: int = 15) -> str:
        if kind not in DEEPLINK_KINDS or not _REF.fullmatch(object_ref) or not 1 <= expires_minutes <= 60:
            raise ValueError("Deep link request is invalid")
        now = datetime.now(timezone.utc)
        payload = {
            "schema_version": "pilot.native-deeplink.v1", "kind": kind,
            "object_ref": object_ref, "device_id": self.device_id,
            "issued_at": now.isoformat(), "expires_at": (now + timedelta(minutes=expires_minutes)).isoformat(),
            "nonce": secrets.token_urlsafe(18),
        }
        envelope = {**payload, "signature": self.identity.sign(canonical_bytes(payload))}
        token = base64.urlsafe_b64encode(canonical_bytes(envelope)).decode("ascii").rstrip("=")
        return f"pilot://open/{kind}?proof={token}"

    def consume_deep_link(self, link: str) -> dict[str, Any]:
        match = re.fullmatch(r"pilot://open/([a-z_]+)\?proof=([A-Za-z0-9_-]+)", link)
        if not match or match.group(1) not in DEEPLINK_KINDS:
            raise ValueError("Pilot deep link is malformed")
        token = match.group(2)
        envelope = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
        signature = str(envelope.pop("signature", ""))
        if set(envelope) != {"schema_version", "kind", "object_ref", "device_id", "issued_at", "expires_at", "nonce"}:
            raise ValueError("Pilot deep link fields are invalid")
        if envelope["kind"] != match.group(1) or envelope["device_id"] != self.device_id:
            raise PermissionError("Pilot deep link targets another context")
        if not DeviceIdentity.verify(self.identity.public_key_b64, canonical_bytes(envelope), signature):
            raise PermissionError("Pilot deep link signature is invalid")
        if datetime.fromisoformat(envelope["expires_at"]) <= datetime.now(timezone.utc):
            raise PermissionError("Pilot deep link has expired")
        link_hash = canonical_hash(envelope)
        state = self._read()
        if link_hash in state["used_links"]:
            raise PermissionError("Pilot deep link has already been used")
        state["used_links"] = (state["used_links"] + [link_hash])[-2048:]
        self._write(state)
        return {"kind": envelope["kind"], "object_ref": envelope["object_ref"], "verified": True}

    def set_app_lock(self, *, locked: bool) -> dict[str, Any]:
        state = self._read()
        state["app_locked"] = bool(locked)
        state["lock_changed_at"] = utc_now_iso()
        if locked:
            state["clipboard_cleared"] = True
            for permission in ("camera_observer", "microphone_voice", "microphone_ptt"):
                state["permissions"][permission]["indicator"] = False
        self._write(state)
        return {"app_locked": state["app_locked"], "clipboard_cleared": bool(state.get("clipboard_cleared"))}

    def notification_preview(self, *, kind: str, sender_label: str | None = None, unlocked: bool = False) -> dict[str, Any]:
        if kind not in SENSITIVE_NOTIFICATION_KINDS:
            raise ValueError("Notification kind is unsupported")
        if not unlocked or self._read()["app_locked"]:
            return {"title": "Pilot", "body": "Open Pilot to view a private update.", "protected": True}
        label = re.sub(r"[^A-Za-z0-9 .'-]", "", str(sender_label or "Pilot"))[:60] or "Pilot"
        return {"title": label, "body": f"New {kind} update", "protected": True, "content_included": False}

    def privacy_controls(self) -> dict[str, Any]:
        return {
            "schema_version": NATIVE_POLICY_VERSION,
            "app_lock_required": True,
            "clipboard_clear_on_lock": True,
            "clipboard_private_copy_timeout_seconds": 30,
            "screenshot_policy": "redact_private_surfaces_in_task_switcher_and_system_capture_where_platform_allows",
            "screen_recording_indicator_required": True,
            "hardware_backed_cache_key_required_in_production": True,
        }

    def write_secure_cache(self, *, cache_id: str, value: dict[str, Any]) -> dict[str, Any]:
        if not _REF.fullmatch(cache_id):
            raise ValueError("Cache identifier is invalid")
        nonce = secrets.token_bytes(12)
        aad = canonical_bytes({"schema_version": "pilot.native-cache.v1", "device_id": self.device_id, "cache_id": cache_id})
        ciphertext = AESGCM(self.cache_key).encrypt(nonce, canonical_bytes(value), aad)
        path = self.root / f"cache-{cache_id}.bin"
        path.write_bytes(nonce + ciphertext)
        os.chmod(path, 0o600)
        return {"cache_id": cache_id, "encrypted": True, "content_hash": canonical_hash(value)}

    def read_secure_cache(self, *, cache_id: str) -> dict[str, Any]:
        if self._read()["app_locked"]:
            raise PermissionError("Unlock Pilot before reading private cache")
        return self._read_secure_cache_value(cache_id=cache_id)

    def _read_secure_cache_value(self, *, cache_id: str) -> dict[str, Any]:
        raw = (self.root / f"cache-{cache_id}.bin").read_bytes()
        aad = canonical_bytes({"schema_version": "pilot.native-cache.v1", "device_id": self.device_id, "cache_id": cache_id})
        return json.loads(AESGCM(self.cache_key).decrypt(raw[:12], raw[12:], aad))

    def issue_biometric_challenge(
        self, *, action_ref: str, payload_hash: str, expires_minutes: int = 3,
    ) -> dict[str, Any]:
        if not _REF.fullmatch(action_ref) or not re.fullmatch(r"[0-9a-f]{64}", str(payload_hash)):
            raise ValueError("Biometric approval target is invalid")
        if not 1 <= expires_minutes <= 5:
            raise ValueError("Biometric challenge lifetime is outside the supported bound")
        now = datetime.now(timezone.utc)
        challenge = {
            "schema_version": "pilot.native-biometric-challenge.v1",
            "challenge_id": f"bio_{secrets.token_hex(16)}", "device_id": self.device_id,
            "action_ref": action_ref, "payload_hash": payload_hash,
            "nonce": secrets.token_urlsafe(24), "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=expires_minutes)).isoformat(),
            "biometric_is_identity_inference": False,
        }
        state = self._read()
        state["biometric_challenges"] = list(state.get("biometric_challenges") or [])[-63:] + [challenge]
        self._write(state)
        return challenge

    def consume_biometric_approval(
        self, request: dict[str, Any], *, device_public_key: str, signature: str,
    ) -> dict[str, Any]:
        required = {
            "schema_version", "challenge_id", "device_id", "action_ref", "payload_hash",
            "nonce", "issued_at", "expires_at", "biometric_is_identity_inference",
            "local_authentication",
        }
        if set(request) != required or request.get("schema_version") != "pilot.native-biometric-approval.v1":
            raise ValueError("Biometric approval is malformed")
        if request.get("device_id") != self.device_id or request.get("biometric_is_identity_inference") is not False:
            raise PermissionError("Biometric approval targets another device or policy")
        if request.get("local_authentication") not in {"biometric", "biometric_or_device_passcode"}:
            raise PermissionError("Local possession confirmation is missing")
        if datetime.fromisoformat(str(request["expires_at"]).replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            raise PermissionError("Biometric approval has expired")
        if not DeviceIdentity.verify(device_public_key, canonical_bytes(request), signature):
            raise PermissionError("The trusted phone did not sign this approval")
        state = self._read()
        challenge = next((
            item for item in state.get("biometric_challenges", [])
            if item.get("challenge_id") == request["challenge_id"]
        ), None)
        if not challenge:
            raise PermissionError("Biometric approval challenge is unavailable")
        nonce = str(request["nonce"])
        if nonce in state.get("used_biometric_nonces", []):
            raise PermissionError("Biometric approval replay detected")
        for key in ("device_id", "action_ref", "payload_hash", "nonce", "issued_at", "expires_at", "biometric_is_identity_inference"):
            if request[key] != challenge[key]:
                raise PermissionError("Biometric approval does not match its exact challenge")
        state["used_biometric_nonces"] = list(state.get("used_biometric_nonces") or [])[-255:] + [nonce]
        state["biometric_challenges"] = [
            item for item in state.get("biometric_challenges", []) if item.get("challenge_id") != request["challenge_id"]
        ]
        self._write(state)
        return {
            "approved": True, "action_ref": request["action_ref"],
            "payload_hash": request["payload_hash"], "possession_confirmed": True,
            "biometric_identity_inferred": False,
        }

    def register_push_channel(self, *, platform: str, provider_token: str) -> dict[str, Any]:
        if platform not in {"apns", "fcm"}:
            raise ValueError("Native push platform is unsupported")
        token = str(provider_token).strip()
        if not 32 <= len(token) <= 4096 or any(char.isspace() for char in token):
            raise ValueError("Native push token is invalid")
        token_hash = canonical_hash({"platform": platform, "token": token})
        cache_id = f"push_{platform}"
        self.write_secure_cache(cache_id=cache_id, value={"platform": platform, "provider_token": token})
        state = self._read()
        channel = {
            "platform": platform, "token_hash": token_hash, "cache_id": cache_id,
            "registered_at": utc_now_iso(), "content_preview_allowed": False,
        }
        state["push_channels"] = [
            item for item in state.get("push_channels", []) if item.get("platform") != platform
        ] + [channel]
        self._write(state)
        return {key: channel[key] for key in ("platform", "token_hash", "registered_at", "content_preview_allowed")}

    def deliver_background_event(
        self, *, event_id: str, kind: str,
        sender: Callable[[str, str, dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        if not _REF.fullmatch(event_id) or kind not in SENSITIVE_NOTIFICATION_KINDS:
            raise ValueError("Background Inbox event is invalid")
        state = self._read()
        prior = next((item for item in state.get("background_events", []) if item.get("event_id") == event_id), None)
        if prior:
            return {**prior, "duplicate": True}
        channels = list(state.get("push_channels") or [])
        if not channels:
            raise PermissionError("No authorized native push channel is connected")
        channel = channels[-1]
        secret = self._read_secure_cache_value(cache_id=str(channel["cache_id"]))
        payload = {
            "schema_version": "pilot.native-background-wake.v1",
            "event_id": event_id, "kind": kind, "device_id": self.device_id,
            "content_available": True, "private_content_included": False,
            "notification": {"title": "Pilot", "body": "Open Pilot to view a private update."},
        }
        provider = dict(sender(str(channel["platform"]), str(secret["provider_token"]), payload) or {})
        accepted = bool(provider.get("accepted"))
        record = {
            "event_id": event_id, "kind": kind,
            "state": "provider_accepted" if accepted else "provider_failed",
            "provider_receipt_hash": canonical_hash(provider),
            "private_content_sent": False, "human_delivery_verified": False,
            "recorded_at": utc_now_iso(), "duplicate": False,
        }
        state = self._read()
        if any(item.get("event_id") == event_id for item in state.get("background_events", [])):
            existing = next(item for item in state["background_events"] if item.get("event_id") == event_id)
            return {**existing, "duplicate": True}
        state["background_events"] = list(state.get("background_events") or [])[-1023:] + [record]
        self._write(state)
        return record

    def permission(self, *, name: str, status: str, active: bool = False) -> dict[str, Any]:
        if name not in PERMISSIONS or status not in {"not_requested", "denied", "granted", "limited"}:
            raise ValueError("Native permission state is invalid")
        if active and (status != "granted" or name not in {"camera_observer", "microphone_voice", "microphone_ptt"}):
            raise PermissionError("That permission cannot be active")
        state = self._read()
        state["permissions"][name] = {"status": status, "indicator": bool(active), "changed_at": utc_now_iso()}
        self._write(state)
        return {"name": name, **state["permissions"][name]}

    def lifecycle(self, *, event: str, battery_percent: int, thermal: str, network: str) -> dict[str, Any]:
        if event not in {"foreground", "background", "suspended", "resumed", "terminated"}:
            raise ValueError("Lifecycle event is unsupported")
        if not 0 <= battery_percent <= 100 or thermal not in {"nominal", "fair", "serious", "critical"} or network not in {"offline", "wifi", "cellular"}:
            raise ValueError("Lifecycle measurements are invalid")
        state = self._read()
        record = {
            "event": event, "battery_percent": battery_percent, "thermal": thermal,
            "network": network, "recorded_at": utc_now_iso(),
            "background_delivery_allowed": event == "background" and network != "offline" and thermal != "critical",
        }
        state["lifecycle"] = (state["lifecycle"] + [record])[-500:]
        if event in {"suspended", "terminated"}:
            state["app_locked"] = True
            for name in ("camera_observer", "microphone_voice", "microphone_ptt"):
                state["permissions"][name]["indicator"] = False
        self._write(state)
        return record
