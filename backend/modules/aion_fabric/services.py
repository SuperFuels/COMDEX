from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .household import HouseholdIdentityRegistry


class ServiceExecutionHub:
    """Persona-bound prepare/approve/execute boundary for external services."""

    _lock = threading.RLock()
    _services = {"calendar", "email", "messaging", "shopping", "booking", "maps", "music"}
    _secret_fields = {"password", "secret", "token", "card_number", "cvv", "cvc", "pin", "private_key"}
    _required_fields = {
        "calendar": ("title", "start", "end"),
        "email": ("to", "subject", "body"),
        "messaging": ("recipient", "body"),
        "shopping": ("item", "quantity"),
        "booking": ("what", "date"),
        "maps": ("destination",),
        "music": ("request",),
    }

    def __init__(self, runtime_dir: str | Path, *, household: HouseholdIdentityRegistry | None = None) -> None:
        self.root = Path(runtime_dir) / "services"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "proposals.json"
        self.household = household or HouseholdIdentityRegistry(runtime_dir)
        self.adapters: Dict[str, Callable[[Dict[str, Any], str], Dict[str, Any]]] = {}

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {"schema_version": "aion.service-execution.v1", "proposals": [], "receipts": [], "updated_at": utc_now_iso()}

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _save(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.replace(temporary, self.path)

    @classmethod
    def _validate_parameters(cls, value: Any, *, path: str = "parameters") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = re.sub(r"[^a-z0-9_]+", "_", str(key).lower())
                if normalized in cls._secret_fields:
                    raise ValueError(f"Raw credential field is forbidden at {path}.{key}")
                cls._validate_parameters(item, path=f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                cls._validate_parameters(item, path=f"{path}[{index}]")
        elif isinstance(value, str) and len(value) > 2000:
            raise ValueError("Service parameter is too large")

    def register_adapter(self, service: str, adapter: Callable[[Dict[str, Any], str], Dict[str, Any]]) -> None:
        if service not in self._services:
            raise ValueError("Unsupported service adapter")
        self.adapters[service] = adapter

    def prepare(self, *, persona_id: str, service: str, action: str, parameters: Dict[str, Any], agent_approval_id: str | None = None, idempotency_key: str | None = None) -> Dict[str, Any]:
        if service not in self._services or self.household.get(persona_id) is None:
            raise PermissionError("A known household persona and supported service are required")
        action = re.sub(r"[^a-z0-9_.-]+", "_", action.lower()).strip("_")[:100]
        if not action:
            raise ValueError("Service action is required")
        if not isinstance(parameters, dict):
            raise ValueError("Service parameters must be an object")
        self._validate_parameters(parameters)
        request_hash = canonical_hash({"service": service, "action": action, "parameters": parameters})
        persona = self.household.get(persona_id) or {}
        binding = str((persona.get("service_bindings") or {}).get(service) or "")
        missing_fields = [field for field in self._required_fields[service] if not parameters.get(field)]
        proposal = {
            "proposal_id": f"service_proposal_{uuid4().hex}",
            "persona_id": persona_id,
            "service": service,
            "action": action,
            "parameters": parameters,
            "parameters_hash": canonical_hash(parameters),
            "agent_approval_id": agent_approval_id,
            "credential_binding_present": bool(binding),
            "status": "needs_details" if missing_fields else "awaiting_private_approval",
            "missing_fields": missing_fields,
            "approval": {"state": "not_ready" if missing_fields else "pending", "approved_by_persona": None, "decided_at": None},
            "external_effect": False,
            "idempotency_key": str(idempotency_key or "")[:160] or None,
            "request_hash": request_hash,
            "created_at": utc_now_iso(),
        }
        with self._lock:
            state = self._load()
            if idempotency_key:
                previous = next((item for item in state.get("proposals", []) if item.get("persona_id") == persona_id and item.get("idempotency_key") == idempotency_key), None)
                if previous:
                    if previous.get("request_hash") != request_hash:
                        raise PermissionError("That service request key was already used for different details")
                    return dict(previous)
            state["proposals"] = list(state.get("proposals") or [])[-99:] + [proposal]
            self._save(state)
        return dict(proposal)

    def for_agent_approval(self, agent_approval_id: str) -> Dict[str, Any] | None:
        return next((dict(item) for item in self._load()["proposals"] if item.get("agent_approval_id") == agent_approval_id), None)

    def update_details(self, proposal_id: str, *, persona_id: str, details: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(details, dict):
            raise ValueError("Private service details must be an object")
        self._validate_parameters(details)
        with self._lock:
            state = self._load()
            proposal = next((item for item in state["proposals"] if item.get("proposal_id") == proposal_id), None)
            if proposal is None:
                raise KeyError("Service proposal was not found")
            if proposal.get("persona_id") != persona_id:
                raise PermissionError("Only the bound household persona can complete these details")
            if proposal.get("status") not in {"needs_details", "awaiting_private_approval"}:
                raise PermissionError("Service proposal details can no longer be changed")
            merged = {**dict(proposal.get("parameters") or {}), **details}
            missing = [field for field in self._required_fields[str(proposal["service"])] if not merged.get(field)]
            proposal["parameters"] = merged
            proposal["parameters_hash"] = canonical_hash(merged)
            proposal["missing_fields"] = missing
            proposal["status"] = "needs_details" if missing else "awaiting_private_approval"
            proposal["approval"] = {"state": "not_ready" if missing else "pending", "approved_by_persona": None, "decided_at": None}
            self._save(state)
            return dict(proposal)

    def decide(self, proposal_id: str, *, persona_id: str, approved: bool, parameters_hash: str | None = None, idempotency_key: str | None = None) -> Dict[str, Any]:
        with self._lock:
            state = self._load()
            proposal = next((item for item in state["proposals"] if item.get("proposal_id") == proposal_id), None)
            if proposal is None:
                raise KeyError("Service proposal was not found")
            if proposal.get("persona_id") != persona_id:
                raise PermissionError("Only the bound household persona can approve this action")
            if parameters_hash is not None and proposal.get("parameters_hash") != parameters_hash:
                raise PermissionError("The service details changed; review them again")
            if proposal.get("status") == "needs_details":
                raise PermissionError("The exact service action is missing required private details")
            if proposal["approval"]["state"] != "pending":
                if idempotency_key and proposal.get("decision_idempotency_key") == idempotency_key:
                    expected = canonical_hash({"approved": bool(approved), "parameters_hash": proposal.get("parameters_hash")})
                    if proposal.get("decision_hash") != expected:
                        raise PermissionError("That service decision key was already used for a different decision")
                return dict(proposal)
            proposal["approval"] = {"state": "approved" if approved else "rejected", "approved_by_persona": persona_id, "decided_at": utc_now_iso()}
            proposal["status"] = "approved_pending_adapter" if approved else "rejected"
            if idempotency_key:
                proposal["decision_idempotency_key"] = str(idempotency_key)[:160]
                proposal["decision_hash"] = canonical_hash({"approved": bool(approved), "parameters_hash": proposal.get("parameters_hash")})
            self._save(state)
            return dict(proposal)

    def execute(self, proposal_id: str, *, persona_id: str, parameters_hash: str | None = None, idempotency_key: str | None = None) -> Dict[str, Any]:
        with self._lock:
            state = self._load()
            proposal = next((item for item in state["proposals"] if item.get("proposal_id") == proposal_id), None)
            if proposal is None:
                raise KeyError("Service proposal was not found")
            if proposal.get("persona_id") != persona_id or proposal.get("approval", {}).get("approved_by_persona") != persona_id:
                raise PermissionError("Persona-bound private approval is required")
            if parameters_hash is not None and proposal.get("parameters_hash") != parameters_hash:
                raise PermissionError("The approved service details changed; review them again")
            if proposal.get("status") == "executed":
                receipt = next((item for item in state["receipts"] if item.get("proposal_id") == proposal_id), None)
                return dict(receipt or {})
            if proposal.get("status") == "executing":
                raise RuntimeError("A previous adapter attempt may still be in flight; reconcile before retrying")
            if proposal.get("status") == "execution_failed_unknown_effect":
                raise RuntimeError("The previous adapter result is uncertain and requires manual reconciliation")
            if proposal.get("status") != "approved_pending_adapter":
                raise PermissionError("The service proposal is not approved for execution")
            adapter = self.adapters.get(str(proposal["service"]))
            persona = self.household.get(persona_id) or {}
            credential_reference = str((persona.get("service_bindings") or {}).get(proposal["service"]) or "")
            if adapter is None or not credential_reference:
                raise RuntimeError("An authorized persona-specific service adapter is not connected")
            proposal["status"] = "executing"
            proposal["execution_attempt_id"] = f"service_attempt_{uuid4().hex}"
            proposal["execution_idempotency_key"] = str(idempotency_key or "")[:160] or None
            proposal["execution_started_at"] = utc_now_iso()
            self._save(state)
            try:
                result = adapter(dict(proposal), credential_reference)
            except Exception:
                proposal["status"] = "execution_failed_unknown_effect"
                proposal["manual_reconciliation_required"] = True
                self._save(state)
                raise
            if not isinstance(result, dict) or not result.get("verified"):
                proposal["status"] = "execution_failed_unknown_effect"
                proposal["manual_reconciliation_required"] = True
                self._save(state)
                raise RuntimeError("The service adapter did not return a verified receipt")
            receipt = {
                "receipt_id": f"service_receipt_{uuid4().hex}",
                "proposal_id": proposal_id,
                "persona_id": persona_id,
                "service": proposal["service"],
                "action": proposal["action"],
                "verified": True,
                "external_reference": str(result.get("external_reference") or "")[:300],
                "result_hash": canonical_hash(result),
                "raw_provider_response_retained": False,
                "idempotency_key": str(idempotency_key or "")[:160] or None,
                "created_at": utc_now_iso(),
            }
            proposal["status"] = "executed"
            proposal["external_effect"] = True
            state["receipts"] = list(state.get("receipts") or [])[-199:] + [receipt]
            self._save(state)
            return dict(receipt)

    def cancel_pending(self, *, persona_id: str) -> Dict[str, Any]:
        """Cancel every reversible proposal for one persona; never guess about in-flight effects."""
        cancellable = {"needs_details", "awaiting_private_approval", "approved_pending_adapter"}
        with self._lock:
            state = self._load()
            cancelled: list[str] = []
            retained_in_flight: list[str] = []
            for proposal in state.get("proposals", []):
                if proposal.get("persona_id") != persona_id:
                    continue
                status = str(proposal.get("status") or "")
                if status in cancellable:
                    proposal["status"] = "cancelled"
                    proposal["cancelled_at"] = utc_now_iso()
                    proposal["approval"] = {
                        "state": "cancelled",
                        "approved_by_persona": None,
                        "decided_at": utc_now_iso(),
                    }
                    cancelled.append(str(proposal.get("proposal_id") or ""))
                elif status in {"executing", "execution_failed_unknown_effect"}:
                    retained_in_flight.append(str(proposal.get("proposal_id") or ""))
            self._save(state)
            return {
                "cancelled": cancelled,
                "cancelled_count": len(cancelled),
                "in_flight_not_claimed_cancelled": retained_in_flight,
            }

    def snapshot(self) -> Dict[str, Any]:
        state = self._load()
        proposals = list(state.get("proposals") or [])
        return {
            "schema_version": state["schema_version"],
            "supported_services": sorted(self._services),
            "connected_adapters": sorted(self.adapters),
            "implemented_provider_adapters": {
                "calendar": "google_calendar_events_insert",
                "email": "gmail_users_messages_send",
            },
            "proposal_count": len(proposals),
            "pending_private_approval": sum(item.get("status") == "awaiting_private_approval" for item in proposals),
            "approved_pending_adapter": sum(item.get("status") == "approved_pending_adapter" for item in proposals),
            "verified_receipts": len(state.get("receipts") or []),
            "policy": {"model_executes_directly": False, "persona_match_required": True, "raw_payment_data_allowed": False},
            "updated_at": state.get("updated_at"),
        }

    def snapshot_for_persona(self, persona_id: str) -> Dict[str, Any]:
        persona = self.household.get(persona_id)
        if persona is None:
            raise PermissionError("A known household persona is required")
        state = self._load()
        proposals = [dict(item) for item in state.get("proposals", []) if item.get("persona_id") == persona_id]
        receipts = [dict(item) for item in state.get("receipts", []) if item.get("persona_id") == persona_id]
        return {
            "schema_version": "aion.service-execution.persona.v1",
            "supported_services": sorted(self._services),
            "bound_services": sorted((persona.get("service_bindings") or {}).keys()),
            "connected_adapters": sorted(self.adapters),
            "proposals": proposals,
            "receipts": receipts,
            "raw_credentials_exposed": False,
            "raw_payment_data_allowed": False,
            "external_effect_requires_private_approval": True,
            "updated_at": state.get("updated_at"),
        }
