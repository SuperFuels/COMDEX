"""Durable coordination state for future GlyphChain protocol activations.

This module does not make an upgrade safe merely because an operator scheduled
it.  It binds a release digest, activation height and validator checkpoint into
one plan, advertises local support through the signed HELLO identity exchange,
and provides a fail-closed readiness assessment for consensus.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "glyphchain.protocol-upgrade.v1"
EVENT_SCHEMA = "glyphchain.protocol-upgrade-event.v1"
EXACT_SCHEDULE_CONFIRMATION = "SCHEDULE GLYPHCHAIN PROTOCOL UPGRADE"
EXACT_CANCEL_CONFIRMATION = "CANCEL GLYPHCHAIN PROTOCOL UPGRADE"
EXACT_COMPLETE_CONFIRMATION = "COMPLETE GLYPHCHAIN PROTOCOL UPGRADE"


class ProtocolUpgradeError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else _canonical(value)
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def protocol_upgrade_root_from_env() -> Path:
    configured = str(os.getenv("GLYPHCHAIN_PROTOCOL_UPGRADE_DIR", "") or "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path(str(os.getenv("GLYPHCHAIN_STATE_DIR", "") or ".glyphchain_state")) / "protocol-upgrade"


def local_supported_range() -> tuple[int, int]:
    minimum = max(1, _integer(os.getenv("GLYPHCHAIN_PROTOCOL_MIN_SUPPORTED", "1"), 1))
    maximum = max(minimum, _integer(os.getenv("GLYPHCHAIN_PROTOCOL_MAX_SUPPORTED", "1"), 1))
    return minimum, maximum


def normalize_protocol_advertisement(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ProtocolUpgradeError("protocol advertisement schema unsupported")
    result = {
        "schema_version": SCHEMA_VERSION,
        "active_version": _integer(value.get("active_version"), 0),
        "supported_min": _integer(value.get("supported_min"), 0),
        "supported_max": _integer(value.get("supported_max"), 0),
        "plan_id": str(value.get("plan_id") or "").strip(),
        "target_version": _integer(value.get("target_version"), 0),
        "activation_height": _integer(value.get("activation_height"), 0),
    }
    if not (1 <= result["supported_min"] <= result["active_version"] <= result["supported_max"] <= 1_000_000):
        raise ProtocolUpgradeError("protocol advertisement version range invalid")
    if result["plan_id"] and (not result["plan_id"].startswith("sha256:") or len(result["plan_id"]) != 71):
        raise ProtocolUpgradeError("protocol advertisement plan identifier invalid")
    if result["plan_id"] and (result["target_version"] < result["active_version"] or result["activation_height"] <= 0):
        raise ProtocolUpgradeError("protocol advertisement plan fields invalid")
    if not result["plan_id"] and (result["target_version"] or result["activation_height"]):
        raise ProtocolUpgradeError("protocol advertisement has unbound plan fields")
    return result


class ProtocolUpgradeStore:
    MAX_JOURNAL_BYTES = 256 * 1024 * 1024
    def __init__(self, root: Path, *, chain_id: str, node_id: str, clock_ms: Any | None = None) -> None:
        self.root = Path(root)
        self.state_path = self.root / "protocol-upgrade.json"
        self.journal_path = self.root / "protocol-upgrade-events.jsonl"
        self.chain_id = str(chain_id or "").strip()
        self.node_id = str(node_id or "").strip()
        if not self.chain_id or not self.node_id:
            raise ProtocolUpgradeError("protocol upgrade coordination requires chain_id and node_id")
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))

    @classmethod
    def from_env(cls, *, chain_id: str, node_id: str) -> "ProtocolUpgradeStore":
        return cls(protocol_upgrade_root_from_env(), chain_id=chain_id, node_id=node_id)

    def _default(self) -> dict[str, Any]:
        minimum, maximum = local_supported_range()
        return {
            "schema_version": SCHEMA_VERSION,
            "chain_id": self.chain_id,
            "node_id": self.node_id,
            "status": "STABLE",
            "current_protocol_version": minimum,
            "supported_min": minimum,
            "supported_max": maximum,
            "plan": None,
            "event_sequence": 0,
            "last_event_hash": "",
            "updated_at_ms": int(self._clock_ms()),
        }

    def status(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._default()
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ProtocolUpgradeError("protocol upgrade state unreadable") from exc
        if not isinstance(value, dict):
            raise ProtocolUpgradeError("protocol upgrade state invalid")
        claimed = str(value.pop("state_hash", "") or "")
        if claimed != _digest(value):
            raise ProtocolUpgradeError("protocol upgrade state hash mismatch")
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ProtocolUpgradeError("protocol upgrade schema unsupported")
        if value.get("chain_id") != self.chain_id or value.get("node_id") != self.node_id:
            raise ProtocolUpgradeError("protocol upgrade identity mismatch")
        return value

    def schedule(
        self, *, target_version: int, activation_height: int,
        release_manifest_sha256: str, validator_checkpoint_id: str,
        governance_approval_id: str, operator_id: str, confirmation: str,
        current_finalized_height: int,
    ) -> dict[str, Any]:
        if confirmation != EXACT_SCHEDULE_CONFIRMATION:
            raise ProtocolUpgradeError("protocol upgrade schedule confirmation required")
        current = self.status()
        if current.get("plan"):
            raise ProtocolUpgradeError("a protocol upgrade plan is already scheduled")
        target = int(target_version)
        current_version = int(current.get("current_protocol_version") or 1)
        if target <= current_version:
            raise ProtocolUpgradeError("target protocol version must be newer than current version")
        minimum_lead = max(1, _integer(os.getenv("GLYPHCHAIN_PROTOCOL_UPGRADE_MIN_LEAD_BLOCKS", "100"), 100))
        if int(activation_height) < int(current_finalized_height) + minimum_lead:
            raise ProtocolUpgradeError("protocol upgrade activation height has insufficient lead time")
        release = str(release_manifest_sha256 or "").strip().lower()
        if len(release) != 64 or any(ch not in "0123456789abcdef" for ch in release):
            raise ProtocolUpgradeError("protocol upgrade requires an exact SHA-256 release manifest digest")
        if not all(str(value or "").strip() for value in (validator_checkpoint_id, governance_approval_id, operator_id)):
            raise ProtocolUpgradeError("protocol upgrade requires checkpoint, governance approval and operator")
        plan_body = {
            "chain_id": self.chain_id,
            "from_version": current_version,
            "target_version": target,
            "activation_height": int(activation_height),
            "release_manifest_sha256": release,
            "validator_checkpoint_id": str(validator_checkpoint_id).strip(),
            "governance_approval_id": str(governance_approval_id).strip(),
        }
        plan = {
            **plan_body,
            "plan_id": _digest(plan_body),
            "scheduled_at_ms": int(self._clock_ms()),
            "scheduled_by": str(operator_id).strip(),
        }
        return self._write(current, status="SCHEDULED", plan=plan, event_type="upgrade_scheduled", operator_id=operator_id)

    def cancel(self, *, operator_id: str, reason: str, confirmation: str, current_finalized_height: int) -> dict[str, Any]:
        current = self.status()
        plan = current.get("plan")
        if not isinstance(plan, dict):
            raise ProtocolUpgradeError("no protocol upgrade plan is scheduled")
        if confirmation != EXACT_CANCEL_CONFIRMATION:
            raise ProtocolUpgradeError("protocol upgrade cancellation confirmation required")
        if int(current_finalized_height) >= int(plan.get("activation_height") or 0):
            raise ProtocolUpgradeError("an activated protocol plan cannot be cancelled locally")
        if not str(operator_id or "").strip() or not str(reason or "").strip():
            raise ProtocolUpgradeError("protocol upgrade cancellation requires operator and reason")
        return self._write(current, status="STABLE", plan=None, event_type="upgrade_cancelled", operator_id=operator_id, reason=reason)

    def complete(self, *, operator_id: str, confirmation: str, current_finalized_height: int) -> dict[str, Any]:
        current = self.status()
        plan = current.get("plan")
        if not isinstance(plan, dict):
            raise ProtocolUpgradeError("no protocol upgrade plan is scheduled")
        if confirmation != EXACT_COMPLETE_CONFIRMATION:
            raise ProtocolUpgradeError("protocol upgrade completion confirmation required")
        target = int(plan.get("target_version") or 0)
        if int(current_finalized_height) < int(plan.get("activation_height") or 0):
            raise ProtocolUpgradeError("protocol upgrade activation height has not finalized")
        if local_supported_range()[1] < target:
            raise ProtocolUpgradeError("installed software does not support the activated protocol")
        completed = dict(current)
        completed["current_protocol_version"] = target
        return self._write(
            completed, status="STABLE", plan=None, event_type="upgrade_completed", operator_id=operator_id,
        )

    def advertisement(self, *, finalized_height: int) -> dict[str, Any]:
        state = self.status()
        minimum, maximum = local_supported_range()
        plan = state.get("plan") if isinstance(state.get("plan"), dict) else None
        active = int(state.get("current_protocol_version") or minimum)
        if active < minimum or active > maximum:
            raise ProtocolUpgradeError("installed software does not support the persisted active protocol")
        if plan and int(finalized_height) >= int(plan.get("activation_height") or 0) and maximum >= int(plan.get("target_version") or 0):
            active = int(plan["target_version"])
        return {
            "schema_version": SCHEMA_VERSION,
            "active_version": active,
            "supported_min": minimum,
            "supported_max": maximum,
            "plan_id": str(plan.get("plan_id") or "") if plan else "",
            "target_version": int(plan.get("target_version") or 0) if plan else 0,
            "activation_height": int(plan.get("activation_height") or 0) if plan else 0,
        }

    def assess(self, *, next_height: int, validator_powers: dict[str, int], self_validator_id: str,
               peer_advertisements: Iterable[dict[str, Any]]) -> dict[str, Any]:
        state = self.status()
        plan = state.get("plan") if isinstance(state.get("plan"), dict) else None
        local = self.advertisement(finalized_height=max(0, int(next_height) - 1))
        if not plan:
            return {"phase": "STABLE", "consensus_allowed": True, "active_version": local["active_version"], "plan": None}
        target = int(plan["target_version"])
        activation = int(plan["activation_height"])
        total_power = sum(max(0, int(value)) for value in validator_powers.values())
        quorum = (2 * total_power + 2) // 3 if total_power else 0
        ready: set[str] = set()
        if self_validator_id and local["supported_max"] >= target:
            ready.add(self_validator_id)
        mismatched: list[str] = []
        for item in peer_advertisements:
            validator_id = str(item.get("validator_id") or "").strip()
            advert = item.get("protocol") if isinstance(item.get("protocol"), dict) else {}
            if not validator_id or validator_id not in validator_powers:
                continue
            if str(advert.get("plan_id") or "") != str(plan["plan_id"]):
                mismatched.append(validator_id)
                continue
            if int(advert.get("supported_max") or 0) >= target:
                ready.add(validator_id)
        ready_power = sum(int(validator_powers.get(value, 0)) for value in ready)
        local_supported = int(local["supported_max"]) >= target
        activated = int(next_height) >= activation
        allowed = not activated or (local_supported and ready_power >= quorum)
        phase = "ACTIVE" if activated and allowed else ("UPGRADE_HALT" if activated else "SCHEDULED")
        return {
            "phase": phase,
            "consensus_allowed": allowed,
            "active_version": target if activated and allowed else int(local["active_version"]),
            "plan": dict(plan),
            "ready_power": ready_power,
            "quorum_power": quorum,
            "ready_validators": sorted(ready),
            "mismatched_validator_count": len(set(mismatched)),
            "local_target_supported": local_supported,
        }

    def verify_journal(self) -> bool:
        if not self.journal_path.exists():
            return True
        records = self._journal()
        maximum = max(32, min(100_000, _integer(os.getenv("GLYPHCHAIN_PROTOCOL_UPGRADE_EVENT_LIMIT", "4096"), 4096)))
        if len(records) > maximum:
            return False
        previous = str(records[0].get("previous_event_hash") or "") if records else ""
        for raw in records:
            item = dict(raw)
            claimed = str(item.pop("event_hash", "") or "")
            if str(item.get("previous_event_hash") or "") != previous or claimed != _digest(item):
                return False
            previous = claimed
        return True

    def _journal(self) -> list[dict[str, Any]]:
        if not self.journal_path.exists():
            return []
        if self.journal_path.stat().st_size > self.MAX_JOURNAL_BYTES:
            raise ProtocolUpgradeError("protocol upgrade journal exceeds its size limit")
        records: list[dict[str, Any]] = []
        try:
            for line in self.journal_path.read_text(encoding="utf-8").splitlines():
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError
                records.append(item)
        except Exception as exc:
            raise ProtocolUpgradeError("protocol upgrade journal invalid") from exc
        return records

    def _write(self, current: dict[str, Any], *, status: str, plan: dict[str, Any] | None,
               event_type: str, operator_id: str, reason: str = "") -> dict[str, Any]:
        now = int(self._clock_ms())
        sequence = int(current.get("event_sequence") or 0) + 1
        event = {
            "schema_version": EVENT_SCHEMA,
            "sequence": sequence,
            "recorded_at_ms": now,
            "chain_id": self.chain_id,
            "node_id": self.node_id,
            "event_type": event_type,
            "operator_id": str(operator_id).strip(),
            "plan_id": str((plan or current.get("plan") or {}).get("plan_id") or ""),
            "reason": str(reason or "").strip()[:1000],
            "previous_event_hash": str(current.get("last_event_hash") or ""),
        }
        event["event_hash"] = _digest(event)
        next_state = {
            **current, "status": status, "plan": plan, "updated_at_ms": now,
            "event_sequence": sequence, "last_event_hash": event["event_hash"],
        }
        self.root.mkdir(parents=True, exist_ok=True)
        try: os.chmod(self.root, 0o700)
        except OSError: pass
        records = self._journal()
        records.append(event)
        maximum = max(32, min(100_000, _integer(os.getenv("GLYPHCHAIN_PROTOCOL_UPGRADE_EVENT_LIMIT", "4096"), 4096)))
        records = records[-maximum:]
        journal_temporary = self.journal_path.with_suffix(".jsonl.tmp")
        with journal_temporary.open("w", encoding="utf-8") as handle:
            for item in records:
                handle.write(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(journal_temporary, self.journal_path)
        try: os.chmod(self.journal_path, 0o600)
        except OSError: pass
        return self._persist_state_only(next_state)

    def _persist_state_only(self, next_state: dict[str, Any]) -> dict[str, Any]:
        persisted = dict(next_state); persisted["state_hash"] = _digest(persisted)
        temporary = self.state_path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(persisted, handle, indent=2, sort_keys=True); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, self.state_path)
        try: os.chmod(self.state_path, 0o600)
        except OSError: pass
        return next_state


def local_protocol_advertisement(*, chain_id: str, node_id: str, finalized_height: int = 0) -> dict[str, Any]:
    return ProtocolUpgradeStore.from_env(chain_id=chain_id, node_id=node_id).advertisement(finalized_height=finalized_height)
