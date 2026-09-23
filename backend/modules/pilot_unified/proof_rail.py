from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_gateway.glyphchain_proof_commit import (
    AION_EVIDENCE_PROOF_V1,
    preview_glyphchain_proof_commit,
)
from backend.modules.chain_sim.aion_proof_receipts import internal_commit_aion_proof_and_build_receipt


PROOF_RAIL_VERSION = "pilot.selective-proof-rail.v1"
ALLOWED_EVENTS = frozenset({"authorization", "delivery", "acceptance", "outcome", "deletion"})
ALLOWED_PUBLIC_FIELDS = frozenset({
    "schema_version", "commitment_id", "event", "object_ref", "scope_hash",
    "policy_version", "recorded_at", "outcome", "source_receipt_hash",
    "previous_commitment_id", "correction_of", "economics_enabled",
})
_HASH = re.compile(r"^[a-f0-9]{64}$")
_SAFE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")


class ExistingGlyphChainProofPublisher:
    """Adapts the existing proof commit/lookup foundation without enabling money."""

    def publish(self, commitment: dict[str, Any]) -> dict[str, Any]:
        preview = preview_glyphchain_proof_commit(
            proof_type=AION_EVIDENCE_PROOF_V1,
            business_id="pilot-private",
            job_id=str(commitment["commitment_id"]),
            proof_payload={
                key: commitment.get(key)
                for key in (
                    "event", "object_ref", "scope_hash", "policy_version", "recorded_at",
                    "outcome", "source_receipt_hash", "previous_commitment_id", "correction_of",
                )
                if commitment.get(key) is not None
            },
            metadata={"source": PROOF_RAIL_VERSION},
        )
        if not preview.get("ok"):
            raise RuntimeError("GlyphChain rejected the proof commitment")
        receipt = internal_commit_aion_proof_and_build_receipt(
            envelope=preview["envelope"],
            proof_commitment_hash=preview["proof_commitment_hash"],
            metadata={"source": PROOF_RAIL_VERSION},
        )
        if not receipt.get("ok") or not receipt.get("verified"):
            raise RuntimeError("GlyphChain did not verify the proof commitment")
        return {
            "status": "committed",
            "proof_commitment_id": receipt["proof_commitment_id"],
            "proof_commitment_hash": preview["proof_commitment_hash"],
        }


class SelectiveProofRail:
    """Durable privacy-minimised commitments for governed Pilot actions.

    The rail never stores the supplied private record. It retains only its canonical
    hash, allowing an authorised mother to verify a record it already possesses.
    """

    _lock = threading.RLock()

    def __init__(
        self,
        runtime_dir: str | Path,
        *,
        mother_identity: DeviceIdentity,
        publisher: ExistingGlyphChainProofPublisher | Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.root = Path(runtime_dir) / "pilot_proof_rail"
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.path = self.root / "state.json"
        self.identity = mother_identity
        self.publisher = publisher

    @staticmethod
    def _initial() -> dict[str, Any]:
        return {"schema_version": PROOF_RAIL_VERSION, "revision": 0, "commitments": [], "used_requests": []}

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise RuntimeError("Pilot proof state could not be verified") from None
        if not isinstance(state, dict) or state.get("schema_version") != PROOF_RAIL_VERSION:
            raise RuntimeError("Pilot proof state has an unsupported format")
        return state

    def _write(self, state: dict[str, Any]) -> None:
        state["revision"] = int(state.get("revision") or 0) + 1
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    @staticmethod
    def _public_hash(value: str, name: str) -> str:
        normal = str(value or "").lower()
        if not _HASH.fullmatch(normal):
            raise ValueError(f"{name} must be a canonical SHA-256 hash")
        return normal

    @staticmethod
    def _safe(value: str, name: str) -> str:
        normal = str(value or "")
        if not _SAFE.fullmatch(normal):
            raise ValueError(f"{name} contains unsupported characters")
        return normal

    def commit(
        self,
        *,
        event: str,
        object_id: str,
        scope_hash: str,
        policy_version: str,
        outcome: str,
        private_record: dict[str, Any],
        idempotency_key: str,
        previous_commitment_id: str | None = None,
        correction_of: str | None = None,
        publication_policy: str = "best_effort",
    ) -> dict[str, Any]:
        if event not in ALLOWED_EVENTS:
            raise ValueError("Choose a supported proof event")
        if publication_policy not in {"best_effort", "required", "local_only"}:
            raise ValueError("Choose a supported proof publication policy")
        if not isinstance(private_record, dict) or not private_record:
            raise ValueError("A mother-private source record is required")
        key = self._safe(idempotency_key, "idempotency_key")
        source_hash = canonical_hash(private_record)
        object_ref = "object_" + canonical_hash({"object_id": str(object_id)})[:32]
        recorded_at = utc_now_iso()
        seed = {
            "schema_version": PROOF_RAIL_VERSION,
            "event": event,
            "object_ref": object_ref,
            "scope_hash": self._public_hash(scope_hash, "scope_hash"),
            "policy_version": self._safe(policy_version, "policy_version"),
            "recorded_at": recorded_at,
            "outcome": self._safe(outcome, "outcome"),
            "source_receipt_hash": source_hash,
            "previous_commitment_id": previous_commitment_id,
            "correction_of": correction_of,
            "economics_enabled": False,
        }
        commitment_id = "proof_" + canonical_hash({**seed, "idempotency_key": key})[:32]
        public = {**seed, "commitment_id": commitment_id}
        public = {key_: value for key_, value in public.items() if value is not None}
        if set(public) - ALLOWED_PUBLIC_FIELDS:
            raise RuntimeError("Proof commitment contains a non-public field")
        signed = {**public, "signature": self.identity.sign(canonical_bytes(public))}

        with self._lock:
            state = self._read()
            used = next((item for item in state["used_requests"] if item["idempotency_key"] == key), None)
            if used:
                if used["request_hash"] != canonical_hash({k: v for k, v in seed.items() if k != "recorded_at"}):
                    raise PermissionError("That proof key was already used for a different event")
                return dict(next(item for item in state["commitments"] if item["commitment_id"] == used["commitment_id"]))

            publication = {"status": "local_only" if publication_policy == "local_only" else "pending"}
            if publication_policy != "local_only" and self.publisher is not None:
                try:
                    publication = self.publisher.publish(public) if hasattr(self.publisher, "publish") else self.publisher(public)
                except Exception as exc:
                    publication = {"status": "pending", "error": type(exc).__name__}
                    if publication_policy == "required":
                        raise RuntimeError("Required proof publication is unavailable") from None
            elif publication_policy == "required":
                raise RuntimeError("Required proof publication is unavailable")

            record = {
                **signed,
                "publication": publication,
                "private_record_stored": False,
                "would_move_money": False,
                "would_require_pho": False,
                "would_require_token": False,
                "would_require_wallet": False,
            }
            state["commitments"].append(record)
            state["used_requests"].append({
                "idempotency_key": key,
                "request_hash": canonical_hash({k: v for k, v in seed.items() if k != "recorded_at"}),
                "commitment_id": commitment_id,
            })
            state["used_requests"] = state["used_requests"][-4096:]
            self._write(state)
            return dict(record)

    def verify(self, commitment_id: str, *, private_record: dict[str, Any] | None = None) -> dict[str, Any]:
        state = self._read()
        record = next((item for item in state["commitments"] if item.get("commitment_id") == commitment_id), None)
        if not record:
            return {"verified": False, "status": "not_found", "commitment_id": commitment_id}
        public = {key: record[key] for key in ALLOWED_PUBLIC_FIELDS if key in record}
        signature_ok = DeviceIdentity.verify(self.identity.public_key_b64, canonical_bytes(public), str(record.get("signature") or ""))
        source_ok = None if private_record is None else canonical_hash(private_record) == record.get("source_receipt_hash")
        return {
            "verified": bool(signature_ok and source_ok is not False),
            "signature_verified": signature_ok,
            "source_record_verified": source_ok,
            "commitment_id": commitment_id,
            "publication_status": dict(record.get("publication") or {}).get("status", "unknown"),
            "private_record_stored": False,
        }

    def correct(
        self,
        *,
        commitment_id: str,
        private_record: dict[str, Any],
        scope_hash: str,
        policy_version: str,
        outcome: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        verification = self.verify(commitment_id)
        if not verification.get("verified"):
            raise KeyError("The original proof commitment is not available")
        return self.commit(
            event="outcome", object_id=f"correction:{commitment_id}", scope_hash=scope_hash,
            policy_version=policy_version, outcome=outcome, private_record=private_record,
            idempotency_key=idempotency_key, previous_commitment_id=commitment_id,
            correction_of=commitment_id,
        )

    def record_private_deletion(
        self,
        *,
        commitment_id: str,
        deletion_receipt: dict[str, Any],
        scope_hash: str,
        policy_version: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not self.verify(commitment_id).get("verified"):
            raise KeyError("The original proof commitment is not available")
        return self.commit(
            event="deletion", object_id=f"deletion:{commitment_id}", scope_hash=scope_hash,
            policy_version=policy_version, outcome="private_record_deleted",
            private_record=deletion_receipt, idempotency_key=idempotency_key,
            previous_commitment_id=commitment_id,
        )

    def health(self) -> dict[str, Any]:
        state = self._read()
        statuses = [str(item.get("publication", {}).get("status") or "unknown") for item in state["commitments"]]
        return {
            "application_available": True,
            "chain_available": bool(self.publisher is not None and all(status == "committed" for status in statuses)),
            "pending_publications": sum(status == "pending" for status in statuses),
            "commitment_count": len(statuses),
            "economics_enabled": False,
            "pho_enabled": False,
            "wallet_enabled": False,
        }

