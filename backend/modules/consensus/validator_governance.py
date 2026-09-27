"""Quorum-authorised validator-set transition packages for GlyphChain."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .finality_checkpoint import MAX_VALIDATORS, normalize_checkpoint


SCHEMA_VERSION = "glyphchain.validator-governance.v1"
PROOF_SCHEMA = "glyphchain.validator-transition-proof.v1"
APPROVAL_DOMAIN = "GLYPHCHAIN_VALIDATOR_TRANSITION_APPROVAL_V1"
PROPOSE_CONFIRMATION = "PROPOSE GLYPHCHAIN VALIDATOR SET CHANGE"
FINALIZE_CONFIRMATION = "FINALIZE GLYPHCHAIN VALIDATOR SET CHANGE"


class ValidatorGovernanceError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    payload = value if isinstance(value, bytes) else _canonical(value)
    return hashlib.sha256(payload).hexdigest()


def transition_body(*, current_checkpoint: Mapping[str, Any], next_checkpoint: Mapping[str, Any],
                    action: str, reason: str, governance_reference: str) -> dict[str, Any]:
    current = normalize_checkpoint(current_checkpoint)
    successor = normalize_checkpoint(next_checkpoint)
    wanted_action = str(action or "").strip().lower()
    if wanted_action not in {"admission", "removal", "replacement", "emergency_removal"}:
        raise ValidatorGovernanceError("validator governance action invalid")
    if current["chain_id"] != successor["chain_id"] or current["network_id"] != successor["network_id"]:
        raise ValidatorGovernanceError("validator checkpoint network identity changed")
    if int(successor["epoch"]) != int(current["epoch"]) + 1:
        raise ValidatorGovernanceError("successor checkpoint epoch must increment by one")
    if int(successor["effective_height"]) <= int(current["effective_height"]):
        raise ValidatorGovernanceError("successor checkpoint effective height must advance")
    before = {item["validator_id"] for item in current["validator_set"]}
    after = {item["validator_id"] for item in successor["validator_set"]}
    admitted = sorted(after - before)
    removed = sorted(before - after)
    if not admitted and not removed and current["validator_set_root"] == successor["validator_set_root"]:
        raise ValidatorGovernanceError("validator transition makes no membership or power/key change")
    if wanted_action == "admission" and (not admitted or removed):
        raise ValidatorGovernanceError("admission transition must only add validators")
    if wanted_action in {"removal", "emergency_removal"} and (not removed or admitted):
        raise ValidatorGovernanceError("removal transition must only remove validators")
    if not str(reason or "").strip() or not str(governance_reference or "").strip():
        raise ValidatorGovernanceError("validator transition requires reason and governance reference")
    body = {
        "domain": APPROVAL_DOMAIN,
        "chain_id": current["chain_id"],
        "network_id": current["network_id"],
        "action": wanted_action,
        "reason": str(reason).strip()[:2000],
        "governance_reference": str(governance_reference).strip()[:240],
        "current_checkpoint_id": current["checkpoint_id"],
        "current_validator_set_root": current["validator_set_root"],
        "next_checkpoint": successor,
        "admitted_validator_ids": admitted,
        "removed_validator_ids": removed,
    }
    body["proposal_id"] = _sha(body)
    return body


def approval_sign_bytes(proposal: Mapping[str, Any], validator_id: str) -> bytes:
    body = dict(proposal)
    body.pop("proposal_id", None)
    return _canonical({
        "domain": APPROVAL_DOMAIN,
        "proposal_id": str(proposal.get("proposal_id") or ""),
        "validator_id": str(validator_id or "").strip(),
        "transition_sha256": _sha(body),
    })


def sign_approval(proposal: Mapping[str, Any], *, validator_id: str, private_key: Ed25519PrivateKey) -> dict[str, str]:
    return {
        "validator_id": str(validator_id).strip(),
        "signature_base64": base64.b64encode(private_key.sign(approval_sign_bytes(proposal, validator_id))).decode("ascii"),
    }


def _verify_approval(proposal: Mapping[str, Any], approval: Mapping[str, Any], checkpoint: Mapping[str, Any]) -> bool:
    validator_id = str(approval.get("validator_id") or "").strip()
    validator = next((item for item in checkpoint["validator_set"] if item["validator_id"] == validator_id), None)
    if validator is None:
        return False
    try:
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(validator["public_key_base64"], validate=True))
        public.verify(
            base64.b64decode(str(approval.get("signature_base64") or ""), validate=True),
            approval_sign_bytes(proposal, validator_id),
        )
        return True
    except Exception:
        return False


def _approval_eligible(proposal: Mapping[str, Any], validator_id: str) -> bool:
    """Never let a validator being removed authorise its successor set.

    An admitted validator is already unable to approve because it is absent from
    the current checkpoint.  Explicitly excluding every removed validator also
    closes the compromised-validator case for removal, emergency removal and
    replacement transitions.
    """

    return str(validator_id or "").strip() not in {
        str(value or "").strip() for value in list(proposal.get("removed_validator_ids") or [])
    }


def verify_transition_proof(
    proof: Mapping[str, Any], *, expected_previous_checkpoint_id: str, expected_next_checkpoint_id: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if proof.get("schema_version") != PROOF_SCHEMA:
        errors.append("validator_transition_proof_schema_invalid")
    proposal = proof.get("proposal") if isinstance(proof.get("proposal"), Mapping) else {}
    current = proof.get("current_checkpoint") if isinstance(proof.get("current_checkpoint"), Mapping) else {}
    try:
        current_normalized = normalize_checkpoint(current)
        rebuilt = transition_body(
            current_checkpoint=current_normalized,
            next_checkpoint=proposal.get("next_checkpoint") or {},
            action=str(proposal.get("action") or ""), reason=str(proposal.get("reason") or ""),
            governance_reference=str(proposal.get("governance_reference") or ""),
        )
        if rebuilt != dict(proposal):
            errors.append("validator_transition_proposal_invalid")
        next_checkpoint = rebuilt["next_checkpoint"]
        if current_normalized["checkpoint_id"] != str(expected_previous_checkpoint_id):
            errors.append("validator_transition_previous_checkpoint_pin_mismatch")
        if next_checkpoint["checkpoint_id"] != str(expected_next_checkpoint_id):
            errors.append("validator_transition_next_checkpoint_pin_mismatch")
        powers = {item["validator_id"]: int(item["power"]) for item in current_normalized["validator_set"]}
        total = sum(powers.values()); quorum = (2 * total + 2) // 3 if total else 0
        raw_approvals = proof.get("approvals") or []
        if not isinstance(raw_approvals, list) or len(raw_approvals) > MAX_VALIDATORS:
            raise ValidatorGovernanceError("validator transition approval limit exceeded")
        seen: set[str] = set(); signed_power = 0
        for approval in raw_approvals:
            if not isinstance(approval, Mapping):
                errors.append("validator_transition_approval_invalid"); continue
            validator_id = str(approval.get("validator_id") or "").strip()
            if validator_id in seen:
                errors.append("validator_transition_duplicate_approval"); continue
            seen.add(validator_id)
            if not _approval_eligible(rebuilt, validator_id):
                errors.append(f"validator_transition_removed_validator_approval:{validator_id}"); continue
            if not _verify_approval(rebuilt, approval, current_normalized):
                errors.append(f"validator_transition_approval_signature_invalid:{validator_id}"); continue
            signed_power += powers.get(validator_id, 0)
        if signed_power < quorum:
            errors.append("validator_transition_signed_quorum_not_reached")
    except Exception:
        current_normalized = {}; next_checkpoint = {}; signed_power = quorum = 0
        errors.append("validator_transition_proof_malformed")
    return {
        "valid": not errors,
        "errors": errors,
        "signed_power": signed_power,
        "quorum_power": quorum,
        "current_checkpoint_id": current_normalized.get("checkpoint_id"),
        "next_checkpoint_id": next_checkpoint.get("checkpoint_id"),
        "next_checkpoint": next_checkpoint,
    }


class ValidatorGovernanceStore:
    MAX_STATE_BYTES = 16 * 1024 * 1024

    def __init__(self, root: Path, *, current_checkpoint: Mapping[str, Any], clock_ms: Any | None = None) -> None:
        self.root = Path(root)
        self.path = self.root / "validator-governance.json"
        self.current_checkpoint = normalize_checkpoint(current_checkpoint)
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))

    def _default(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "chain_id": self.current_checkpoint["chain_id"],
            "network_id": self.current_checkpoint["network_id"],
            "current_checkpoint_id": self.current_checkpoint["checkpoint_id"],
            "status": "IDLE", "proposal": None, "approvals": [], "events": [],
            "updated_at_ms": int(self._clock_ms()),
        }

    def status(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._with_assurance(self._default())
        if self.path.stat().st_size > self.MAX_STATE_BYTES:
            raise ValidatorGovernanceError("validator governance state exceeds its size limit")
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValidatorGovernanceError("validator governance state unreadable") from exc
        claimed = str(value.pop("state_hash", "") or "") if isinstance(value, dict) else ""
        if not isinstance(value, dict) or claimed != _sha(value):
            raise ValidatorGovernanceError("validator governance state hash mismatch")
        if value.get("schema_version") != SCHEMA_VERSION or value.get("current_checkpoint_id") != self.current_checkpoint["checkpoint_id"]:
            raise ValidatorGovernanceError("validator governance checkpoint binding mismatch")
        events = list(value.get("events") or [])
        previous = str(events[0].get("previous_event_hash") or "") if events else ""
        for raw in events:
            record = dict(raw); claimed = str(record.pop("event_hash", "") or "")
            if str(record.get("previous_event_hash") or "") != previous or claimed != _sha(record):
                raise ValidatorGovernanceError("validator governance event chain invalid")
            previous = claimed
        return self._with_assurance(value)

    def propose(self, *, next_checkpoint: Mapping[str, Any], action: str, reason: str,
                governance_reference: str, operator_id: str, confirmation: str,
                current_finalized_height: int) -> dict[str, Any]:
        if confirmation != PROPOSE_CONFIRMATION:
            raise ValidatorGovernanceError("validator governance proposal confirmation required")
        state = self.status()
        if state.get("proposal"):
            raise ValidatorGovernanceError("a validator governance proposal is already active")
        proposal = transition_body(
            current_checkpoint=self.current_checkpoint, next_checkpoint=next_checkpoint,
            action=action, reason=reason, governance_reference=governance_reference,
        )
        minimum_lead = max(1, int(os.getenv("GLYPHCHAIN_VALIDATOR_CHANGE_MIN_LEAD_BLOCKS", "100") or 100))
        if int(proposal["next_checkpoint"]["effective_height"]) < int(current_finalized_height) + minimum_lead:
            raise ValidatorGovernanceError("validator transition has insufficient activation lead time")
        return self._save_event(state, "PROPOSED", proposal=proposal, approvals=[], event="proposal_created", operator_id=operator_id)

    def add_approval(self, approval: Mapping[str, Any], *, operator_id: str) -> dict[str, Any]:
        state = self.status(); proposal = state.get("proposal")
        if not isinstance(proposal, dict):
            raise ValidatorGovernanceError("no validator governance proposal is active")
        if not _verify_approval(proposal, approval, self.current_checkpoint):
            raise ValidatorGovernanceError("validator governance approval signature invalid")
        validator_id = str(approval.get("validator_id") or "").strip()
        if not _approval_eligible(proposal, validator_id):
            raise ValidatorGovernanceError("validator being removed cannot approve its successor set")
        approvals = [item for item in list(state.get("approvals") or []) if item.get("validator_id") != validator_id]
        approvals.append({"validator_id": validator_id, "signature_base64": str(approval.get("signature_base64") or "")})
        return self._save_event(state, "QUORUM_READY" if self._power(approvals, proposal) >= self._quorum() else "COLLECTING_APPROVALS",
                                proposal=proposal, approvals=sorted(approvals, key=lambda item: item["validator_id"]),
                                event="approval_recorded", operator_id=operator_id)

    def finalize(self, *, operator_id: str, confirmation: str) -> dict[str, Any]:
        if confirmation != FINALIZE_CONFIRMATION:
            raise ValidatorGovernanceError("validator governance finalization confirmation required")
        state = self.status(); proposal = state.get("proposal"); approvals = list(state.get("approvals") or [])
        if not isinstance(proposal, dict) or self._power(approvals, proposal) < self._quorum():
            raise ValidatorGovernanceError("validator governance signed quorum not reached")
        proof = {"schema_version": PROOF_SCHEMA, "current_checkpoint": self.current_checkpoint,
                 "proposal": proposal, "approvals": approvals, "finalized_at_ms": int(self._clock_ms())}
        result = verify_transition_proof(
            proof, expected_previous_checkpoint_id=self.current_checkpoint["checkpoint_id"],
            expected_next_checkpoint_id=proposal["next_checkpoint"]["checkpoint_id"],
        )
        if not result["valid"]:
            raise ValidatorGovernanceError("validator governance proof verification failed")
        state = self._save_event(state, "FINALIZED", proposal=proposal, approvals=approvals,
                                 event="transition_finalized", operator_id=operator_id)
        return {**state, "transition_proof": proof, "next_checkpoint": proposal["next_checkpoint"],
                "restart_required_at_height": int(proposal["next_checkpoint"]["effective_height"])}

    def _quorum(self) -> int:
        total = sum(int(item["power"]) for item in self.current_checkpoint["validator_set"])
        return (2 * total + 2) // 3 if total else 0

    def _power(self, approvals: list[dict[str, Any]], proposal: Mapping[str, Any] | None = None) -> int:
        powers = {item["validator_id"]: int(item["power"]) for item in self.current_checkpoint["validator_set"]}
        active_proposal = proposal or {}
        return sum(
            powers.get(str(item.get("validator_id") or ""), 0)
            for item in approvals
            if _approval_eligible(active_proposal, str(item.get("validator_id") or ""))
        )

    def _with_assurance(self, state: dict[str, Any]) -> dict[str, Any]:
        value = dict(state); approvals = list(value.get("approvals") or [])
        proposal = value.get("proposal") if isinstance(value.get("proposal"), Mapping) else {}
        value["signed_power"] = self._power(approvals, proposal); value["quorum_power"] = self._quorum()
        value["quorum_reached"] = value["signed_power"] >= value["quorum_power"] and bool(value.get("proposal"))
        return value

    def _save_event(self, state: dict[str, Any], status: str, *, proposal: dict[str, Any],
                    approvals: list[dict[str, Any]], event: str, operator_id: str) -> dict[str, Any]:
        now = int(self._clock_ms()); events = list(state.get("events") or [])[-1023:]
        previous = str(events[-1].get("event_hash") or "") if events else ""
        record = {"sequence": int(events[-1]["sequence"] if events else 0) + 1,
                  "recorded_at_ms": now, "event": event, "operator_id": str(operator_id or "").strip(),
                  "proposal_id": str(proposal.get("proposal_id") or ""), "previous_event_hash": previous}
        record["event_hash"] = _sha(record); events.append(record)
        value = {**state, "status": status, "proposal": proposal, "approvals": approvals,
                 "events": events, "updated_at_ms": now}
        self.root.mkdir(parents=True, exist_ok=True)
        try: os.chmod(self.root, 0o700)
        except OSError: pass
        persisted = dict(value); persisted.pop("signed_power", None); persisted.pop("quorum_power", None); persisted.pop("quorum_reached", None)
        persisted["state_hash"] = _sha(persisted)
        temporary = self.path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(persisted, handle, indent=2, sort_keys=True); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, self.path)
        try: os.chmod(self.path, 0o600)
        except OSError: pass
        return self._with_assurance(persisted)
