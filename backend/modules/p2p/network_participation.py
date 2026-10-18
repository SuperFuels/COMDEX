"""Explicit, local administration of GlyphChain desktop participation.

No desktop becomes a relay or validator by discovering peers or by merely
possessing the application.  Elevated network roles require a durable local
approval record and role-specific acknowledgements.  This module deliberately
does not implement validator admission governance; it records the local side
of that future decision and refuses a validator role without an approval ID.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import threading
from typing import Any, Mapping


SCHEMA_VERSION = "glyphchain.network-participation.v1"
ROLES = {"light", "relay", "validator"}
CONFIRMATIONS = {
    "relay": "ENABLE GLYPHCHAIN RELAY",
    "validator": "ENABLE GLYPHCHAIN VALIDATOR",
}
ROLE_CAPABILITIES = {
    "light": {
        "verify_proofs": True,
        "outbound_sync": True,
        "accept_inbound_peers": False,
        "relay_messages": False,
        "propose_blocks": False,
        "vote": False,
    },
    "relay": {
        "verify_proofs": True,
        "outbound_sync": True,
        "accept_inbound_peers": True,
        "relay_messages": True,
        "propose_blocks": False,
        "vote": False,
    },
    "validator": {
        "verify_proofs": True,
        "outbound_sync": True,
        "accept_inbound_peers": True,
        "relay_messages": True,
        "propose_blocks": True,
        "vote": True,
    },
}


class NetworkParticipationError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "role": "light",
        "opted_in": False,
        "operator_id": None,
        "approved_at": None,
        "storage_limit_bytes": 512 * 1024 * 1024,
        "public_connectivity_acknowledged": False,
        "availability_acknowledged": False,
        "key_custody_acknowledged": False,
        "governance_approval_id": None,
        "validator_set_checkpoint_id": None,
        "capabilities": dict(ROLE_CAPABILITIES["light"]),
    }


class NetworkParticipationStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.path = self.root / "network-participation.json"
        self.audit_path = self.root / "network-participation-events.jsonl"
        self._lock = threading.RLock()

    def status(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return _default_state()
            try:
                value = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise NetworkParticipationError("network_participation_state_unreadable") from exc
            return self._validate_state(value)

    def configure(
        self,
        *,
        role: str,
        operator_id: str,
        confirmation: str | None = None,
        storage_limit_bytes: int = 512 * 1024 * 1024,
        public_connectivity_acknowledged: bool = False,
        availability_acknowledged: bool = False,
        key_custody_acknowledged: bool = False,
        governance_approval_id: str | None = None,
        validator_set_checkpoint_id: str | None = None,
    ) -> dict[str, Any]:
        requested = str(role or "").strip().lower()
        actor = str(operator_id or "").strip()
        if requested not in ROLES:
            raise NetworkParticipationError("network_participation_role_invalid")
        if not actor:
            raise NetworkParticipationError("network_participation_operator_required")
        limit = int(storage_limit_bytes)
        if limit < 64 * 1024 * 1024 or limit > 4 * 1024 * 1024 * 1024 * 1024:
            raise NetworkParticipationError("network_participation_storage_limit_invalid")
        if requested in {"relay", "validator"}:
            if str(confirmation or "") != CONFIRMATIONS[requested]:
                raise NetworkParticipationError("network_participation_explicit_confirmation_required")
            if not public_connectivity_acknowledged:
                raise NetworkParticipationError("network_participation_connectivity_acknowledgement_required")
        if requested == "validator":
            if not availability_acknowledged:
                raise NetworkParticipationError("validator_availability_acknowledgement_required")
            if not key_custody_acknowledged:
                raise NetworkParticipationError("validator_key_custody_acknowledgement_required")
            if not str(governance_approval_id or "").strip():
                raise NetworkParticipationError("validator_governance_approval_required")
            if not str(validator_set_checkpoint_id or "").strip():
                raise NetworkParticipationError("validator_checkpoint_required")
        state = {
            "schema_version": SCHEMA_VERSION,
            "role": requested,
            "opted_in": requested in {"relay", "validator"},
            "operator_id": actor,
            "approved_at": _now(),
            "storage_limit_bytes": limit,
            "public_connectivity_acknowledged": bool(public_connectivity_acknowledged),
            "availability_acknowledged": bool(availability_acknowledged),
            "key_custody_acknowledged": bool(key_custody_acknowledged),
            "governance_approval_id": str(governance_approval_id or "").strip() or None,
            "validator_set_checkpoint_id": str(validator_set_checkpoint_id or "").strip() or None,
            "capabilities": dict(ROLE_CAPABILITIES[requested]),
        }
        with self._lock:
            previous = self.status()
            self._write(state)
            self._append_audit("ROLE_CONFIGURED", actor, previous, state)
        return dict(state)

    def disable_elevated_participation(self, *, operator_id: str, reason: str) -> dict[str, Any]:
        actor = str(operator_id or "").strip()
        why = str(reason or "").strip()
        if not actor or not why:
            raise NetworkParticipationError("operator_and_reason_required")
        with self._lock:
            previous = self.status()
            state = _default_state()
            state.update({"operator_id": actor, "approved_at": _now()})
            self._write(state)
            self._append_audit("ELEVATED_PARTICIPATION_DISABLED", actor, previous, state, reason=why)
        return dict(state)

    def verify_audit_chain(self) -> bool:
        previous = ""
        if not self.audit_path.exists():
            return True
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            supplied = str(event.pop("event_hash", ""))
            if event.get("previous_event_hash") != previous:
                return False
            expected = sha256(_canonical(event)).hexdigest()
            if supplied != expected:
                return False
            previous = supplied
        return True

    def _validate_state(self, value: Mapping[str, Any]) -> dict[str, Any]:
        if value.get("schema_version") != SCHEMA_VERSION:
            raise NetworkParticipationError("network_participation_schema_unsupported")
        role = str(value.get("role") or "").strip().lower()
        if role not in ROLES:
            raise NetworkParticipationError("network_participation_role_invalid")
        result = dict(value)
        result["capabilities"] = dict(ROLE_CAPABILITIES[role])
        if role in {"relay", "validator"} and value.get("opted_in") is not True:
            raise NetworkParticipationError("elevated_network_participation_not_approved")
        return result

    def _write(self, state: Mapping[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(dict(state), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    def _append_audit(
        self,
        event_type: str,
        actor: str,
        previous_state: Mapping[str, Any],
        new_state: Mapping[str, Any],
        *,
        reason: str | None = None,
    ) -> None:
        previous_hash = ""
        if self.audit_path.exists():
            lines = self.audit_path.read_text(encoding="utf-8").splitlines()
            if lines:
                previous_hash = str(json.loads(lines[-1]).get("event_hash") or "")
        event = {
            "schema_version": "glyphchain.network-participation-event.v1",
            "event_type": event_type,
            "actor_id": actor,
            "occurred_at": _now(),
            "previous_role": previous_state.get("role"),
            "new_role": new_state.get("role"),
            "reason": reason,
            "previous_event_hash": previous_hash,
        }
        event["event_hash"] = sha256(_canonical(event)).hexdigest()
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(self.audit_path, 0o600)


def participation_from_env() -> dict[str, Any]:
    """Return enforced participation state or legacy deployment state.

    When enforcement is enabled, the configured state file is authoritative.
    Without enforcement, existing developer clusters continue to use their
    explicit process configuration and are labelled ``legacy_deployment``.
    """
    enforce = str(os.getenv("GLYPHCHAIN_ENFORCE_EXPLICIT_PARTICIPATION", "0") or "0").lower() in {
        "1", "true", "yes", "on",
    }
    if not enforce:
        state = _default_state()
        if str(os.getenv("GLYPHCHAIN_SELF_VAL_ID", "") or "").strip():
            state.update({
                "role": "validator",
                "opted_in": False,
                "capabilities": dict(ROLE_CAPABILITIES["validator"]),
                "warning": "explicit_participation_not_enforced",
            })
        return {"enforced": False, "source": "legacy_deployment", **state}
    root = str(os.getenv("GLYPHCHAIN_PARTICIPATION_DIR", "") or "").strip()
    if not root:
        root = str(Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state")) / "participation")
    state = NetworkParticipationStore(root).status()
    return {"enforced": True, "source": "local_admin_record", **state}
