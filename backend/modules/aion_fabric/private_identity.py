from __future__ import annotations

import base64
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .identity import DeviceIdentity


class ProductionPrivateIdentity:
    """User-controlled identity, device possession, consent and memory governance."""

    ROLES = {"adult", "child"}
    MEMORY_SCOPES = {"private", "household_shared"}
    SHARED_SCREEN_IDLE_MINUTES = 5
    SHARED_SCREEN_PRESENCE_SECONDS = 300

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "private_identity"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {
            "schema_version": "pilot.private-identity.v1", "profiles": [], "devices": [],
            "pending_device_challenges": [], "consents": [], "memories": [],
            "active_shared_identity": None, "recovery_events": [], "used_activation_nonces": [],
            "used_pairing_challenges": [], "memory_operations": [],
            "shared_screen_events": [],
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

    @staticmethod
    def _profile(state: Dict[str, Any], persona_id: str) -> Dict[str, Any]:
        profile = next((item for item in state.get("profiles", []) if item.get("persona_id") == persona_id and item.get("status") == "active"), None)
        if profile is None:
            raise KeyError("Active private identity was not found")
        return profile

    def onboard(
        self,
        *,
        display_name: str,
        role: str = "adult",
        guardian_persona_id: str | None = None,
        age_band: str = "",
    ) -> Dict[str, Any]:
        clean_role = str(role).strip().lower()
        clean_name = " ".join(str(display_name).split())[:80]
        if clean_role not in self.ROLES or len(clean_name) < 2:
            raise ValueError("A valid display name and identity role are required")
        state = self._read()
        duplicate = next(
            (
                item for item in state.get("profiles", [])
                if str(item.get("display_name") or "").casefold() == clean_name.casefold()
                and item.get("role") == clean_role
                and item.get("status") == "active"
            ),
            None,
        )
        if duplicate is not None:
            raise ValueError("That private identity already exists; select it instead of creating it again")
        if clean_role == "child":
            guardian = self._profile(state, str(guardian_persona_id or ""))
            if guardian.get("role") != "adult":
                raise PermissionError("A child profile requires an active adult guardian")
        recovery_code = "-".join(secrets.token_hex(3) for _ in range(4))
        profile = {
            "persona_id": f"persona_{uuid4().hex}", "display_name": clean_name, "role": clean_role,
            "guardian_persona_id": str(guardian_persona_id or "") or None,
            "age_band": " ".join(str(age_band).split())[:20] if clean_role == "child" else "",
            "status": "active", "memory_default_scope": "private", "shared_screen_name_visible": True,
            "recovery_code_hash": canonical_hash({"code": recovery_code}), "created_at": utc_now_iso(),
        }
        state["profiles"].append(profile)
        self._write(state)
        return {**{key: value for key, value in profile.items() if key != "recovery_code_hash"}, "recovery_code": recovery_code, "recovery_code_shown_once": True}

    def begin_phone_enrollment(
        self,
        *,
        persona_id: str,
        device_label: str,
        public_key: str,
        biometric_capable: bool,
    ) -> Dict[str, Any]:
        state = self._read()
        self._profile(state, persona_id)
        try:
            if len(base64.b64decode(public_key, validate=True)) != 32:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Phone public key must be a valid Ed25519 key") from None
        challenge = {
            "challenge_id": f"phone_challenge_{uuid4().hex}", "persona_id": persona_id,
            "device_id": f"phone_{uuid4().hex}", "device_label": " ".join(str(device_label).split())[:80],
            "public_key": public_key, "biometric_capable": bool(biometric_capable),
            "nonce": secrets.token_urlsafe(24),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        }
        state["pending_device_challenges"] = list(state.get("pending_device_challenges") or [])[-19:] + [challenge]
        self._write(state)
        return {key: value for key, value in challenge.items() if key != "public_key"}

    def complete_phone_enrollment(self, challenge_id: str, *, signature: str) -> Dict[str, Any]:
        state = self._read()
        challenge = next((item for item in state.get("pending_device_challenges", []) if item.get("challenge_id") == challenge_id), None)
        if challenge is None:
            raise KeyError("Phone enrollment challenge was not found")
        if datetime.fromisoformat(str(challenge["expires_at"]).replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            raise PermissionError("Phone enrollment challenge expired")
        signed = {key: challenge[key] for key in ("challenge_id", "persona_id", "device_id", "device_label", "biometric_capable", "nonce", "expires_at")}
        if not DeviceIdentity.verify(str(challenge["public_key"]), canonical_bytes(signed), signature):
            raise PermissionError("Phone possession signature is invalid")
        device = {
            "device_id": challenge["device_id"], "persona_id": challenge["persona_id"],
            "device_label": challenge["device_label"], "public_key": challenge["public_key"],
            "status": "trusted", "possession_verified": True,
            "biometric_capable": bool(challenge["biometric_capable"]),
            "biometric_assurance": "native_attestation_required" if challenge["biometric_capable"] else "unavailable",
            "enrolled_at": utc_now_iso(),
        }
        state["devices"] = [item for item in state.get("devices", []) if item.get("device_id") != device["device_id"]] + [device]
        state["pending_device_challenges"] = [item for item in state.get("pending_device_challenges", []) if item.get("challenge_id") != challenge_id]
        self._write(state)
        return {key: value for key, value in device.items() if key != "public_key"}

    def enroll_phone_from_verified_pairing(
        self,
        *,
        persona_id: str,
        device_id: str,
        device_label: str,
        public_key: str,
        pairing_payload: Dict[str, Any],
        signature: str,
        mother_id: str,
    ) -> Dict[str, Any]:
        """Commit a mother-bound transport challenge into the identity source of truth."""
        state = self._read()
        self._profile(state, persona_id)
        if (
            pairing_payload.get("schema_version") != "pilot.phone-pairing-challenge.v1"
            or pairing_payload.get("persona_id") != persona_id
            or pairing_payload.get("device_id") != device_id
            or pairing_payload.get("mother_id") != mother_id
        ):
            raise PermissionError("The phone pairing proof does not match this identity")
        challenge_id = str(pairing_payload.get("challenge_id") or "")
        existing = next((item for item in state.get("devices", []) if item.get("device_id") == device_id), None)
        if challenge_id in state.get("used_pairing_challenges", []):
            if existing and existing.get("persona_id") == persona_id and existing.get("public_key") == public_key:
                return {key: value for key, value in existing.items() if key != "public_key"}
            raise PermissionError("That phone pairing proof has already been used")
        try:
            valid_key = len(base64.b64decode(public_key, validate=True)) == 32
        except (ValueError, TypeError):
            valid_key = False
        if not valid_key or not DeviceIdentity.verify(public_key, canonical_bytes(pairing_payload), signature):
            raise PermissionError("The phone pairing possession proof is invalid")
        device = {
            "device_id": device_id,
            "persona_id": persona_id,
            "device_label": " ".join(str(device_label).split())[:80],
            "public_key": public_key,
            "status": "trusted",
            "possession_verified": True,
            "biometric_capable": False,
            "biometric_assurance": "native_attestation_required",
            "enrollment_method": "mother_bound_mobile_pairing",
            "mother_id": mother_id,
            "pairing_challenge_id": challenge_id,
            "enrolled_at": utc_now_iso(),
        }
        state["devices"] = [item for item in state.get("devices", []) if item.get("device_id") != device_id] + [device]
        state["used_pairing_challenges"] = list(state.get("used_pairing_challenges", []))[-255:] + [challenge_id]
        self._write(state)
        return {key: value for key, value in device.items() if key != "public_key"}

    def device_status(self, *, persona_id: str, device_id: str) -> Dict[str, Any]:
        state = self._read()
        self._profile(state, persona_id)
        device = next(
            (item for item in state.get("devices", []) if item.get("device_id") == device_id and item.get("persona_id") == persona_id),
            None,
        )
        if device is None:
            return {"device_id": device_id, "persona_id": persona_id, "status": "not_connected"}
        return {
            "device_id": device_id,
            "persona_id": persona_id,
            "status": device.get("status"),
            "possession_verified": bool(device.get("possession_verified")),
            "revoked_at": device.get("revoked_at"),
        }

    def revoke_device(self, *, persona_id: str, device_id: str, reason: str) -> Dict[str, Any]:
        state = self._read()
        self._profile(state, persona_id)
        device = next((item for item in state.get("devices", []) if item.get("device_id") == device_id and item.get("persona_id") == persona_id), None)
        if device is None:
            raise KeyError("That phone is not bound to this identity")
        device["status"] = "revoked"
        device["revoked_at"] = utc_now_iso()
        device["revocation_reason"] = " ".join(str(reason).split())[:120] or "owner_requested"
        active = dict(state.get("active_shared_identity") or {})
        if active.get("device_id") == device_id:
            self._record_shared_screen_event(state, active=active, reason="trusted_phone_revoked")
            state["active_shared_identity"] = None
        self._write(state)
        return {"device_id": device_id, "status": "revoked", "active_sessions_revoked": True}

    def recover(self, *, persona_id: str, recovery_code: str) -> Dict[str, Any]:
        state = self._read()
        profile = self._profile(state, persona_id)
        if not secrets.compare_digest(str(profile["recovery_code_hash"]), canonical_hash({"code": str(recovery_code)})):
            raise PermissionError("Recovery code is invalid")
        revoked = 0
        for device in state.get("devices", []):
            if device.get("persona_id") == persona_id and device.get("status") == "trusted":
                device["status"] = "revoked"
                device["revoked_at"] = utc_now_iso()
                device["revocation_reason"] = "account_recovery"
                revoked += 1
        active = dict(state.get("active_shared_identity") or {})
        if active:
            self._record_shared_screen_event(state, active=active, reason="account_recovery")
        state["active_shared_identity"] = None
        event = {"recovery_id": f"recovery_{uuid4().hex}", "persona_id": persona_id, "devices_revoked": revoked, "created_at": utc_now_iso()}
        state["recovery_events"].append(event)
        self._write(state)
        return event

    @staticmethod
    def _session_expiry_reason(active: Dict[str, Any], *, now: datetime | None = None) -> str | None:
        try:
            if not active:
                return "already_locked"
            checked_at = now or datetime.now(timezone.utc)
            if datetime.fromisoformat(str(active["expires_at"]).replace("Z", "+00:00")) <= checked_at:
                return "inactivity_timeout"
            presence_expiry = active.get("presence_expires_at")
            if presence_expiry and datetime.fromisoformat(str(presence_expiry).replace("Z", "+00:00")) <= checked_at:
                return "trusted_phone_departed"
            return None
        except (KeyError, TypeError, ValueError):
            return "invalid_session"

    @classmethod
    def _is_live_session(cls, active: Dict[str, Any]) -> bool:
        return cls._session_expiry_reason(active) is None

    @staticmethod
    def _record_shared_screen_event(state: Dict[str, Any], *, active: Dict[str, Any], reason: str) -> None:
        state["shared_screen_events"] = list(state.get("shared_screen_events") or [])[-255:] + [{
            "persona_id": active.get("persona_id"), "device_id": active.get("device_id"),
            "reason": re.sub(r"[^a-z0-9_.-]+", "_", str(reason).lower())[:60],
            "occurred_at": utc_now_iso(),
        }]

    def _expire_shared_screen_if_needed(self, state: Dict[str, Any]) -> str | None:
        active = dict(state.get("active_shared_identity") or {})
        reason = self._session_expiry_reason(active)
        if active and reason:
            self._record_shared_screen_event(state, active=active, reason=reason)
            state["active_shared_identity"] = None
            self._write(state)
        return reason

    def activate_shared_screen(self, *, persona_id: str, device_id: str, nonce: str, signature: str, minutes: int = 5) -> Dict[str, Any]:
        state = self._read()
        profile = self._profile(state, persona_id)
        device = next((item for item in state.get("devices", []) if item.get("device_id") == device_id and item.get("persona_id") == persona_id and item.get("status") == "trusted"), None)
        if device is None:
            raise PermissionError("A trusted phone must activate the shared-screen identity")
        payload = {"purpose": "activate_shared_screen", "persona_id": persona_id, "device_id": device_id, "nonce": str(nonce)}
        if str(nonce) in state.get("used_activation_nonces", []):
            raise PermissionError("Shared-screen activation replay detected")
        if not DeviceIdentity.verify(str(device["public_key"]), canonical_bytes(payload), signature):
            raise PermissionError("Shared-screen identity signature is invalid")
        existing = dict(state.get("active_shared_identity") or {})
        if self._is_live_session(existing) and (
            existing.get("persona_id") != persona_id or existing.get("device_id") != device_id
        ):
            raise PermissionError(f"The television is currently controlled by {existing.get('display_name') or 'another person'}")
        idle_minutes = max(1, min(int(minutes), self.SHARED_SCREEN_IDLE_MINUTES))
        now = datetime.now(timezone.utc)
        active = {
            "persona_id": persona_id, "display_name": profile["display_name"], "device_id": device_id,
            "activated_at": now.isoformat(), "last_activity_at": now.isoformat(),
            "last_presence_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=idle_minutes)).isoformat(),
            "presence_expires_at": (now + timedelta(seconds=self.SHARED_SCREEN_PRESENCE_SECONDS)).isoformat(),
            "idle_timeout_seconds": idle_minutes * 60, "exclusive": True,
            "departure_timeout_seconds": self.SHARED_SCREEN_PRESENCE_SECONDS,
            "private_details_on_shared_screen": False,
        }
        state["active_shared_identity"] = active
        state["used_activation_nonces"] = list(state.get("used_activation_nonces") or [])[-255:] + [str(nonce)]
        self._write(state)
        return active

    def touch_shared_screen(self, *, persona_id: str, source: str = "interaction") -> Dict[str, Any]:
        """Renew only the currently active person's bounded television lease."""
        state = self._read()
        active = dict(state.get("active_shared_identity") or {})
        if self._expire_shared_screen_if_needed(state):
            raise PermissionError("The private television session has expired; reactivate it from the trusted phone")
        if active.get("persona_id") != persona_id:
            raise PermissionError("That identity does not control the television")
        now = datetime.now(timezone.utc)
        active["last_activity_at"] = now.isoformat()
        active["expires_at"] = (now + timedelta(minutes=self.SHARED_SCREEN_IDLE_MINUTES)).isoformat()
        active["last_activity_source"] = re.sub(r"[^a-z0-9_.-]+", "_", str(source).lower())[:60]
        state["active_shared_identity"] = active
        self._write(state)
        return active

    def confirm_shared_screen_presence(self, *, persona_id: str, device_id: str) -> Dict[str, Any]:
        """Renew nearby-phone presence without disguising passive presence as TV activity."""
        state = self._read()
        active = dict(state.get("active_shared_identity") or {})
        reason = self._expire_shared_screen_if_needed(state)
        if reason:
            raise PermissionError(f"The private television session is locked ({reason}); take control again")
        if active.get("persona_id") != persona_id or active.get("device_id") != device_id:
            raise PermissionError("This trusted phone does not control the television")
        device = next((
            item for item in state.get("devices", [])
            if item.get("device_id") == device_id and item.get("persona_id") == persona_id and item.get("status") == "trusted"
        ), None)
        if device is None:
            raise PermissionError("A revoked or unknown phone cannot keep a television workspace unlocked")
        now = datetime.now(timezone.utc)
        active["last_presence_at"] = now.isoformat()
        active["presence_expires_at"] = (now + timedelta(seconds=self.SHARED_SCREEN_PRESENCE_SECONDS)).isoformat()
        state["active_shared_identity"] = active
        self._write(state)
        return active

    def release_shared_screen(self, *, persona_id: str | None = None, reason: str = "owner_logout") -> Dict[str, Any]:
        """Lock the shared workspace without deleting the person's identity or data."""
        state = self._read()
        active = dict(state.get("active_shared_identity") or {})
        if not active:
            return {"released": False, "reason": "already_locked"}
        if persona_id and active.get("persona_id") != persona_id:
            raise PermissionError("That identity does not control the television")
        clean_reason = re.sub(r"[^a-z0-9_.-]+", "_", str(reason).lower())[:60]
        self._record_shared_screen_event(state, active=active, reason=clean_reason)
        state["active_shared_identity"] = None
        self._write(state)
        return {
            "released": True, "persona_id": active.get("persona_id"),
            "display_name": active.get("display_name"),
            "reason": clean_reason,
            "released_at": utc_now_iso(),
        }

    def release_shared_screen_signed(self, *, persona_id: str, device_id: str, nonce: str, signature: str) -> Dict[str, Any]:
        state = self._read()
        active = dict(state.get("active_shared_identity") or {})
        if not self._is_live_session(active):
            return self.release_shared_screen(reason="expired_or_already_locked")
        if active.get("persona_id") != persona_id or active.get("device_id") != device_id:
            raise PermissionError("This trusted phone does not control the television")
        device = next(
            (item for item in state.get("devices", []) if item.get("device_id") == device_id and item.get("persona_id") == persona_id and item.get("status") == "trusted"),
            None,
        )
        payload = {"purpose": "release_shared_screen", "persona_id": persona_id, "device_id": device_id, "nonce": str(nonce)}
        if device is None or not DeviceIdentity.verify(str(device["public_key"]), canonical_bytes(payload), signature):
            raise PermissionError("Shared-screen release signature is invalid")
        return self.release_shared_screen(persona_id=persona_id, reason="trusted_phone_logout")

    def grant_consent(self, *, persona_id: str, service: str, scopes: list[str], device_id: str) -> Dict[str, Any]:
        state = self._read()
        self._profile(state, persona_id)
        device = next((item for item in state.get("devices", []) if item.get("device_id") == device_id and item.get("persona_id") == persona_id and item.get("status") == "trusted"), None)
        clean_scopes = sorted({re.sub(r"[^a-z0-9_.:/-]+", "", str(scope).lower())[:160] for scope in scopes if str(scope).strip()})
        if device is None or not clean_scopes:
            raise PermissionError("Explicit consent requires this person's trusted phone and visible scopes")
        consent = {
            "consent_id": f"consent_{uuid4().hex}", "persona_id": persona_id,
            "service": re.sub(r"[^a-z0-9_.-]+", "", str(service).lower())[:80], "scopes": clean_scopes,
            "device_id": device_id, "status": "granted", "granted_at": utc_now_iso(),
            "inspectable": True, "silent_scope_expansion": False,
        }
        state["consents"] = [item for item in state.get("consents", []) if not (item.get("persona_id") == persona_id and item.get("service") == consent["service"] and item.get("status") == "granted")] + [consent]
        self._write(state)
        return consent

    def revoke_consent(self, *, persona_id: str, consent_id: str) -> Dict[str, Any]:
        state = self._read()
        consent = next((item for item in state.get("consents", []) if item.get("consent_id") == consent_id and item.get("persona_id") == persona_id), None)
        if consent is None:
            raise KeyError("Service consent was not found")
        consent["status"] = "revoked"
        consent["revoked_at"] = utc_now_iso()
        self._write(state)
        return dict(consent)

    @staticmethod
    def _memory_replay(state: Dict[str, Any], idempotency_key: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        if not idempotency_key:
            return None
        request_hash = canonical_hash(payload)
        previous = next((item for item in state.get("memory_operations", []) if item.get("idempotency_key") == idempotency_key), None)
        if previous is None:
            return None
        if previous.get("request_hash") != request_hash:
            raise PermissionError("That memory idempotency key was already used for different details")
        return dict(previous.get("result") or {})

    @staticmethod
    def _record_memory_operation(
        state: Dict[str, Any], idempotency_key: str, payload: Dict[str, Any], result: Dict[str, Any],
    ) -> None:
        if not idempotency_key:
            return
        state["memory_operations"] = list(state.get("memory_operations", []))[-255:] + [{
            "idempotency_key": idempotency_key, "request_hash": canonical_hash(payload), "result": dict(result),
        }]

    def remember(self, *, persona_id: str, kind: str, summary: str, scope: str = "private", source_reference: str = "", idempotency_key: str = "") -> Dict[str, Any]:
        state = self._read()
        self._profile(state, persona_id)
        if scope not in self.MEMORY_SCOPES:
            raise ValueError("Memory scope must be private or household_shared")
        payload = {"operation": "create", "persona_id": persona_id, "kind": str(kind), "summary": str(summary), "scope": scope, "source_reference": str(source_reference)}
        replay = self._memory_replay(state, idempotency_key, payload)
        if replay is not None:
            return replay
        memory = {
            "memory_id": f"memory_{uuid4().hex}", "persona_id": persona_id,
            "kind": re.sub(r"[^a-z0-9_.-]+", "_", str(kind).lower())[:80],
            "summary": " ".join(str(summary).split())[:500], "scope": scope,
            "source_reference": " ".join(str(source_reference).split())[:180],
            "created_at": utc_now_iso(), "corrected_at": None,
        }
        if not memory["summary"]:
            raise ValueError("Memory summary is required")
        memory["record_hash"] = canonical_hash(memory)
        state["memories"].append(memory)
        state["memories"] = state["memories"][-1000:]
        self._record_memory_operation(state, idempotency_key, payload, memory)
        self._write(state)
        return memory

    def memories(self, *, persona_id: str, requester_persona_id: str) -> list[Dict[str, Any]]:
        state = self._read()
        profile = self._profile(state, persona_id)
        requester = self._profile(state, requester_persona_id)
        allowed = requester_persona_id == persona_id or (profile.get("role") == "child" and profile.get("guardian_persona_id") == requester_persona_id and requester.get("role") == "adult")
        if not allowed:
            raise PermissionError("Private memory belongs to another identity")
        return [dict(item) for item in state.get("memories", []) if item.get("persona_id") == persona_id]

    def update_memory(self, *, persona_id: str, memory_id: str, summary: str | None = None, scope: str | None = None, idempotency_key: str = "") -> Dict[str, Any]:
        state = self._read()
        payload = {"operation": "update", "persona_id": persona_id, "memory_id": memory_id, "summary": summary, "scope": scope}
        replay = self._memory_replay(state, idempotency_key, payload)
        if replay is not None:
            return replay
        memory = next((item for item in state.get("memories", []) if item.get("memory_id") == memory_id and item.get("persona_id") == persona_id), None)
        if memory is None:
            raise KeyError("Private memory was not found")
        if scope is not None:
            if scope not in self.MEMORY_SCOPES:
                raise ValueError("Memory scope must be private or household_shared")
            memory["scope"] = scope
        if summary is not None:
            clean = " ".join(str(summary).split())[:500]
            if not clean:
                raise ValueError("Corrected memory cannot be empty")
            memory["summary"] = clean
            memory["corrected_at"] = utc_now_iso()
        memory["record_hash"] = canonical_hash({key: value for key, value in memory.items() if key != "record_hash"})
        self._record_memory_operation(state, idempotency_key, payload, memory)
        self._write(state)
        return dict(memory)

    def delete_memory(self, *, persona_id: str, memory_id: str, idempotency_key: str = "") -> Dict[str, Any]:
        state = self._read()
        payload = {"operation": "delete", "persona_id": persona_id, "memory_id": memory_id}
        replay = self._memory_replay(state, idempotency_key, payload)
        if replay is not None:
            return replay
        before = len(state.get("memories", []))
        state["memories"] = [item for item in state.get("memories", []) if not (item.get("memory_id") == memory_id and item.get("persona_id") == persona_id)]
        if len(state["memories"]) == before:
            raise KeyError("Private memory was not found")
        result = {"memory_id": memory_id, "deleted": True, "recoverable": False}
        self._record_memory_operation(state, idempotency_key, payload, result)
        self._write(state)
        return result

    def export(self, *, persona_id: str, requester_persona_id: str) -> Dict[str, Any]:
        memories = self.memories(persona_id=persona_id, requester_persona_id=requester_persona_id)
        state = self._read()
        profile = self._profile(state, persona_id)
        consents = [dict(item) for item in state.get("consents", []) if item.get("persona_id") == persona_id]
        devices = [{key: value for key, value in item.items() if key != "public_key"} for item in state.get("devices", []) if item.get("persona_id") == persona_id]
        return {"schema_version": "pilot.private-export.v1", "exported_at": utc_now_iso(), "profile": {key: value for key, value in profile.items() if key != "recovery_code_hash"}, "memories": memories, "consents": consents, "devices": devices}

    def snapshot(self, *, viewer_persona_id: str | None = None) -> Dict[str, Any]:
        state = self._read()
        active = dict(state.get("active_shared_identity") or {})
        expiry_reason = self._session_expiry_reason(active)
        if active and expiry_reason:
            self._record_shared_screen_event(state, active=active, reason=expiry_reason)
            state["active_shared_identity"] = None
            self._write(state)
            active = {}
        profiles = [{key: value for key, value in item.items() if key not in {"recovery_code_hash"}} for item in state.get("profiles", [])]
        own_consents = [dict(item) for item in state.get("consents", []) if viewer_persona_id and item.get("persona_id") == viewer_persona_id]
        return {
            "schema_version": state.get("schema_version"), "profiles": profiles,
            "active_shared_identity": active or None, "viewer_consents": own_consents,
            "shared_screen": {
                "state": "active" if active else "locked",
                "exclusive": True,
                "idle_timeout_seconds": self.SHARED_SCREEN_IDLE_MINUTES * 60,
                "departure_timeout_seconds": self.SHARED_SCREEN_PRESENCE_SECONDS,
                "requires_trusted_phone": True,
                "last_lock_reason": (list(state.get("shared_screen_events") or [])[-1].get("reason") if state.get("shared_screen_events") else None),
            },
            "viewer_memory_count": len([item for item in state.get("memories", []) if viewer_persona_id and item.get("persona_id") == viewer_persona_id]),
            "trusted_device_count": len([item for item in state.get("devices", []) if item.get("status") == "trusted"]),
            "biometric": {"native_signed_possession_implemented": True, "platform_attestation_field_qualified": False},
        }
