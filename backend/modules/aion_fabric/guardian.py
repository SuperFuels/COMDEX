from __future__ import annotations

import json
import os
import secrets
import threading
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .pilot_inbox import PilotInbox
from .private_identity import ProductionPrivateIdentity


class PilotGuardian:
    """Non-medical urgent-help escalation to explicitly trusted contacts.

    Guardian never represents itself as an emergency-service dispatcher. The
    only executable proof is a verified alert through an owner-authorized
    trusted-contact adapter.
    """

    _lock = threading.RLock()

    def __init__(
        self, runtime_dir: str | Path, *, identities: ProductionPrivateIdentity | None = None,
        inbox: PilotInbox | None = None,
    ) -> None:
        self.root = Path(runtime_dir) / "guardian"; self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.identities = identities or ProductionPrivateIdentity(runtime_dir)
        self.inbox = inbox or PilotInbox(runtime_dir, identities=self.identities)
        self.alert_adapters: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {"schema_version": "pilot.guardian.v1", "permissions": [], "incidents": [], "responses": [], "sensor_signals": [], "operations": []}

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists(): return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8")); return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError): return self._initial()

    def _write(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso(); temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state)); os.chmod(temporary, 0o600); os.replace(temporary, self.path)

    def _profile(self, persona_id: str) -> Dict[str, Any]:
        profile = next((item for item in self.identities.snapshot().get("profiles", []) if item.get("persona_id") == persona_id and item.get("status") == "active"), None)
        if profile is None: raise PermissionError("A production private identity is required")
        return dict(profile)

    @staticmethod
    def _replay(state: Dict[str, Any], key: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        if not key:
            return None
        item = next((entry for entry in state.get("operations", []) if entry.get("idempotency_key") == key), None)
        if item is None:
            return None
        if item.get("request_hash") != canonical_hash(payload):
            raise PermissionError("That Guardian idempotency key was already used for different details")
        return dict(item.get("result") or {})

    @staticmethod
    def _record(state: Dict[str, Any], key: str, payload: Dict[str, Any], result: Dict[str, Any]) -> None:
        if key:
            state["operations"] = list(state.get("operations", []))[-255:] + [{
                "idempotency_key": key, "request_hash": canonical_hash(payload), "result": dict(result),
            }]

    def register_alert_adapter(self, channel: str, adapter: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        if channel not in {"pilot", "sms", "email", "whatsapp", "voice_call"}: raise ValueError("Unsupported Guardian alert adapter")
        self.alert_adapters[channel] = adapter

    def grant_emergency_contact(
        self, *, persona_id: str, contact_id: str, channel: str,
        share_location: bool, location_permission_receipt: str = "",
        allow_interruption: bool = True, idempotency_key: str = "",
    ) -> Dict[str, Any]:
        self._profile(persona_id); contacts = self.inbox._read().get("contacts", [])
        contact = next((item for item in contacts if item.get("contact_id") == contact_id and item.get("owner_persona_id") == persona_id), None)
        if contact is None: raise PermissionError("Choose one of this identity's private contacts")
        if channel not in {"pilot", "sms", "email", "whatsapp", "voice_call"}: raise ValueError("Unsupported Guardian route")
        if share_location and len(str(location_permission_receipt)) < 12: raise PermissionError("Explicit location-sharing permission is required")
        permission = {
            "permission_id": f"guardian_permission_{uuid4().hex}", "persona_id": persona_id,
            "contact_id": contact_id, "contact_name": contact["display_name"], "channel": channel,
            "share_location": bool(share_location), "location_permission_hash": canonical_hash(location_permission_receipt) if share_location else None,
            "emergency_interruption_allowed": bool(allow_interruption), "ordinary_contact_permission_implied": False,
            "status": "active", "created_at": utc_now_iso(),
        }
        payload = {"operation": "grant", "persona_id": persona_id, "contact_id": contact_id, "channel": channel, "share_location": bool(share_location), "location_permission_receipt": str(location_permission_receipt), "allow_interruption": bool(allow_interruption)}
        with self._lock:
            state = self._read(); replay = self._replay(state, idempotency_key, payload)
            if replay is not None: return replay
            state["permissions"] = [item for item in state["permissions"] if not (item.get("persona_id") == persona_id and item.get("contact_id") == contact_id)] + [permission]
            self._record(state, idempotency_key, payload, permission); self._write(state)
        return dict(permission)

    def request_help(
        self, *, persona_id: str, trigger: str, surface: str,
        location: Dict[str, Any] | None = None, sensor_signal_id: str = "", idempotency_key: str = "",
    ) -> Dict[str, Any]:
        self._profile(persona_id); trigger = " ".join(str(trigger).split())[:240]
        if not trigger: raise ValueError("An explicit help request is required")
        state = self._read(); permissions = [item for item in state["permissions"] if item.get("persona_id") == persona_id and item.get("status") == "active"]
        payload = {"operation": "request", "persona_id": persona_id, "trigger": trigger, "surface": str(surface), "location": dict(location or {}), "sensor_signal_id": str(sensor_signal_id)}
        replay = self._replay(state, idempotency_key, payload)
        if replay is not None: return replay
        incident = {
            "incident_id": f"guardian_incident_{uuid4().hex}", "persona_id": persona_id,
            "trigger": trigger, "trigger_surface": str(surface)[:40], "sensor_signal_id": str(sensor_signal_id)[:120],
            "status": "awaiting_large_confirmation", "trusted_contact_count": len(permissions),
            "confirmation_required": True, "false_positive_cancel_available": True,
            "ambulance_dispatched": False, "emergency_service_contacted": False,
            "medical_diagnosis_made": False, "location": dict(location or {}),
            "location_not_shared_without_permission": True, "response_token": secrets.token_urlsafe(24),
            "created_at": utc_now_iso(),
        }
        with self._lock:
            state = self._read(); replay = self._replay(state, idempotency_key, payload)
            if replay is not None: return replay
            state["incidents"] = list(state["incidents"])[-99:] + [incident]
            self._record(state, idempotency_key, payload, incident); self._write(state)
        return dict(incident)

    def cancel(self, *, incident_id: str, persona_id: str, reason: str = "false_alarm", idempotency_key: str = "") -> Dict[str, Any]:
        with self._lock:
            state = self._read(); payload = {"operation": "cancel", "incident_id": incident_id, "persona_id": persona_id, "reason": reason}; replay = self._replay(state, idempotency_key, payload)
            if replay is not None: return replay
            incident = next((item for item in state["incidents"] if item.get("incident_id") == incident_id), None)
            if incident is None: raise KeyError("Guardian incident was not found")
            if incident.get("persona_id") != persona_id: raise PermissionError("Only the protected identity can cancel this alert")
            if incident.get("status") in {"alerts_verified", "cancelled"}: return dict(incident)
            incident["status"] = "cancelled"; incident["cancelled_at"] = utc_now_iso(); incident["cancellation_reason"] = str(reason)[:100]; result = dict(incident); self._record(state, idempotency_key, payload, result); self._write(state); return result

    def confirm(self, *, incident_id: str, persona_id: str, idempotency_key: str = "") -> Dict[str, Any]:
        with self._lock:
            state = self._read(); payload = {"operation": "confirm", "incident_id": incident_id, "persona_id": persona_id}; replay = self._replay(state, idempotency_key, payload)
            if replay is not None: return replay
            incident = next((item for item in state["incidents"] if item.get("incident_id") == incident_id), None)
            if incident is None: raise KeyError("Guardian incident was not found")
            if incident.get("persona_id") != persona_id: raise PermissionError("Only the protected identity can confirm this alert")
            if incident.get("status") != "awaiting_large_confirmation": return dict(incident)
            permissions = [item for item in state["permissions"] if item.get("persona_id") == persona_id and item.get("status") == "active"]
            if not permissions: raise RuntimeError("No explicitly authorized Guardian contact is configured")
            incident["status"] = "confirmed_pending_trusted_contact_delivery"; incident["confirmed_at"] = utc_now_iso()
            incident["pending_permission_ids"] = [item["permission_id"] for item in permissions]; result = dict(incident); self._record(state, idempotency_key, payload, result); self._write(state); return result

    def deliver_alerts(self, *, incident_id: str, persona_id: str, idempotency_key: str = "") -> Dict[str, Any]:
        with self._lock:
            state = self._read(); payload = {"operation": "deliver", "incident_id": incident_id, "persona_id": persona_id}; replay = self._replay(state, idempotency_key, payload)
            if replay is not None: return replay
            incident = next((item for item in state["incidents"] if item.get("incident_id") == incident_id), None)
            if incident is None: raise KeyError("Guardian incident was not found")
            if incident.get("persona_id") != persona_id or incident.get("status") != "confirmed_pending_trusted_contact_delivery": raise PermissionError("A confirmed Guardian incident is required")
            permissions = [item for item in state["permissions"] if item.get("permission_id") in incident.get("pending_permission_ids", [])]
            verified, failures = [], []
            for permission in permissions:
                adapter = self.alert_adapters.get(str(permission["channel"]))
                if adapter is None:
                    failures.append({"permission_id": permission["permission_id"], "reason": "adapter_not_connected"}); continue
                payload = {
                    "incident_id": incident_id, "protected_persona_id": persona_id,
                    "contact_id": permission["contact_id"], "trigger": incident["trigger"],
                    "urgent": True, "response_token": incident["response_token"],
                    "location": incident["location"] if permission.get("share_location") else None,
                    "ambulance_dispatched": False,
                }
                try: result = adapter(payload)
                except Exception as exc:
                    failures.append({"permission_id": permission["permission_id"], "reason": type(exc).__name__}); continue
                if isinstance(result, dict) and result.get("verified") and result.get("provider_alert_id"):
                    verified.append({"permission_id": permission["permission_id"], "provider_alert_id": str(result["provider_alert_id"])[:200], "channel": permission["channel"], "verified_at": utc_now_iso()})
                else: failures.append({"permission_id": permission["permission_id"], "reason": "unverified_provider_result"})
            incident["verified_alerts"] = verified; incident["delivery_failures"] = failures
            incident["status"] = "alerts_verified" if verified else "connectivity_fallback_required"
            incident["ambulance_dispatched"] = False; incident["emergency_service_contacted"] = False
            result = {"incident_id": incident_id, "status": incident["status"], "verified_alerts": verified, "failures": failures, "ambulance_dispatched": False}
            self._record(state, idempotency_key, payload, result); self._write(state); return result

    def record_response(self, *, response_token: str, responder_name: str, message: str) -> Dict[str, Any]:
        with self._lock:
            state = self._read(); incident = next((item for item in state["incidents"] if secrets.compare_digest(str(item.get("response_token") or ""), str(response_token))), None)
            if incident is None: raise PermissionError("Guardian response link is invalid")
            response = {"response_id": f"guardian_response_{uuid4().hex}", "incident_id": incident["incident_id"], "responder_name": " ".join(str(responder_name).split())[:100], "message": " ".join(str(message).split())[:1000], "created_at": utc_now_iso()}
            state["responses"] = list(state["responses"])[-199:] + [response]; incident["live_response_received"] = True; self._write(state); return dict(response)

    def ingest_sensor_signal(self, *, persona_id: str, source: str, kind: str, confidence: float) -> Dict[str, Any]:
        self._profile(persona_id)
        if kind not in {"possible_fall", "wearable_sos", "inactivity"}: raise ValueError("Unsupported non-medical Guardian signal")
        signal = {"signal_id": f"guardian_signal_{uuid4().hex}", "persona_id": persona_id, "source": str(source)[:100], "kind": kind, "confidence": max(0.0, min(float(confidence), 1.0)), "medical_diagnosis": False, "automatic_dispatch": False, "status": "prompt_required", "created_at": utc_now_iso()}
        with self._lock:
            state = self._read(); state["sensor_signals"] = list(state["sensor_signals"])[-199:] + [signal]; self._write(state)
        return dict(signal)

    def snapshot(self, *, persona_id: str) -> Dict[str, Any]:
        self._profile(persona_id); state = self._read()
        return {key: [dict(item) for item in state.get(key, []) if item.get("persona_id") == persona_id] for key in ("permissions", "incidents", "sensor_signals")}
