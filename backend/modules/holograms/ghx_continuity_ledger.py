"""
🧩 SRK-18 - GHX Continuity Ledger (GCL)
Module: backend/modules/holograms/ghx_continuity_ledger.py

Purpose:
    Establish a persistent, cryptographically verifiable event ledger
    for GHX continuity tracking. Each entry forms a hash-linked chain
    containing event metadata, signatures, and continuity verification.

Phases:
    * 18.1 - GCL Core Ledger implementation
    * 18.2 - Hook Integration (GCH)
    * 18.3 - Chain Integrity Enforcement (prev↔curr hash, signature)
    * 18.4+ - Federation, Vault Export, and Auditing
"""

import json
import time
import hashlib
from uuid import uuid4
from typing import Dict, Any, List, Optional


class GHXContinuityLedger:
    """
    Persistent event ledger maintaining hash-linked entries for GHX continuity.
    Each record is immutable once sealed, with prev↔curr linkage and
    deterministic signatures for tamper detection.
    """

    def __init__(self, node_id: str = "Tessaris.Node.Local"):
        self.node_id = node_id
        self.chain: List[Dict[str, Any]] = []
        self.last_hash: Optional[str] = None

    # ────────────────────────────────────────────────────────────────
    def _compute_entry_hash(self, entry: Dict[str, Any]) -> str:
        """Deterministic hash over canonicalized entry (excluding curr_hash)."""
        payload = json.dumps(
            {k: v for k, v in entry.items() if k != "curr_hash"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha3_512(payload).hexdigest()

    def _sign_entry(self, entry: Dict[str, Any]) -> str:
        """Compute deterministic node signature using sha3-256."""
        base = f"{self.node_id}:{self._compute_entry_hash(entry)}"
        return hashlib.sha3_256(base.encode("utf-8")).hexdigest()

    # ────────────────────────────────────────────────────────────────
    def append_event(
        self,
        event_type: str,
        meta: Optional[Dict[str, Any]] = None,
        origin: Optional[str] = None,
        signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append a new event to the ledger (auto-sealed and signed)."""
        entry = {
            "event_id": f"GCL-{uuid4()}",
            "seq": len(self.chain) + 1,
            "timestamp": time.time(),
            "event_type": event_type,
            "meta": meta or {},
            "origin": origin or self.node_id,
            "prev_hash": self.last_hash,
        }

        # seal and sign
        entry["curr_hash"] = self._compute_entry_hash(entry)
        entry["signature"] = signature or self._sign_entry(entry)

        # append to chain
        self.chain.append(entry)
        self.last_hash = entry["curr_hash"]
        return entry

    # ────────────────────────────────────────────────────────────────
    def verify_chain(self) -> Dict[str, Any]:
        """
        Verify full chain continuity:
            * curr_hash integrity
            * prev↔curr linkage
            * signature consistency
        Returns diagnostic dict.
        """
        if not self.chain:
            return {"verified": True, "count": 0}

        for i, entry in enumerate(self.chain):
            # Recompute current hash
            expected_hash = self._compute_entry_hash(
                {k: v for k, v in entry.items() if k not in ["curr_hash", "signature"]}
            )
            if entry["curr_hash"] != expected_hash:
                return {"verified": False, "error": "hash_mismatch", "index": i}

            # Verify prev linkage
            if i > 0 and entry["prev_hash"] != self.chain[i - 1]["curr_hash"]:
                return {"verified": False, "error": "link_broken", "index": i}

            # Verify signature
            expected_sig = self._sign_entry(
                {k: v for k, v in entry.items() if k != "signature"}
            )
            if entry["signature"] != expected_sig:
                return {"verified": False, "error": "bad_signature", "index": i}

        return {"verified": True, "count": len(self.chain)}

    # ────────────────────────────────────────────────────────────────
    def snapshot(self) -> Dict[str, Any]:
        """Return canonical snapshot of current ledger state."""
        return {
            "node_id": self.node_id,
            "length": len(self.chain),
            "last_hash": self.last_hash,
            "chain": list(self.chain),
            "verified": self.verify_chain()["verified"],
        }

    def restore(self, snapshot: Dict[str, Any]) -> None:
        """Restore ledger state from a prior snapshot."""
        self.node_id = snapshot.get("node_id", self.node_id)
        self.chain = snapshot.get("chain", [])
        self.last_hash = snapshot.get("last_hash")

    # ────────────────────────────────────────────────────────────────
    def export_chain(self, file_path: str) -> None:
        """Persist the ledger chain to a JSON file for archival."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.snapshot(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_chain(cls, file_path: str) -> "GHXContinuityLedger":
        """Load a previously exported chain into a new ledger instance."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ledger = cls(node_id=data.get("node_id", "Restored.Node"))
        ledger.restore(data)
        return ledger


# Optional CLI verification helper
if __name__ == "__main__":
    ledger = GHXContinuityLedger()
    ledger.append_event("startup", {"status": "ok"})
    ledger.append_event("heartbeat", {"coherence": 0.98})
    ledger.append_event("sync", {"phase": "ledger_test"})

    print("\n🧩 GHX Continuity Ledger Snapshot")
    print(json.dumps(ledger.snapshot(), indent=2))

    print("\n✅ Verification Result:")
    print(ledger.verify_chain())