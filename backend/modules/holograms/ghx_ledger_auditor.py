"""
🧩 SRK-18.6 - GHX Ledger Verifier & Auditor
Module: backend/modules/holograms/ghx_ledger_auditor.py
Subsystem: Holograms / GHX Continuity Layer

Purpose:
    Validate and replay GHX Continuity Ledger snapshots exported to GlyphVault.
    Detects tampering, hash inconsistencies, and divergence between nodes.

Features:
    * Snapshot verification and chain replay
    * Tamper detection via SHA3 re-hash validation
    * Diff comparison between snapshots
    * Structured audit reporting

Author: Tessaris Core Engineering
Spec Ref: SRK-18 / Phase 18.6
"""

import json
import hashlib
from typing import Dict, Any, List, Optional
from backend.modules.holograms.ghx_continuity_ledger import GHXContinuityLedger


class GHXLedgerAuditor:
    """Independent verifier and auditor for GHX Continuity Ledgers."""

    # ────────────────────────────────────────────────────────────────
    @staticmethod
    def verify_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Validate structural integrity and cryptographic linkage of a snapshot."""
        if "chain" not in snapshot:
            return {"verified": False, "error": "missing_chain"}

        chain = snapshot["chain"]
        if not chain:
            return {"verified": True, "count": 0}

        for i, entry in enumerate(chain):
            payload = {k: v for k, v in entry.items() if k not in ["curr_hash", "signature"]}
            expected_hash = hashlib.sha3_512(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()

            if entry["curr_hash"] != expected_hash:
                return {"verified": False, "error": "hash_mismatch", "index": i}

            if i > 0 and entry["prev_hash"] != chain[i - 1]["curr_hash"]:
                return {"verified": False, "error": "broken_link", "index": i}

            sig_base = f"{snapshot.get('node_id','unknown')}:{expected_hash}"
            expected_sig = hashlib.sha3_256(sig_base.encode("utf-8")).hexdigest()
            if entry["signature"] != expected_sig:
                return {"verified": False, "error": "bad_signature", "index": i}

        return {"verified": True, "count": len(chain)}

    # ────────────────────────────────────────────────────────────────
    @staticmethod
    def replay(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Rebuild the ledger from a snapshot and verify continuity."""
        ledger = GHXContinuityLedger(snapshot.get("node_id", "Replay.Node"))
        ledger.restore(snapshot)
        return ledger.verify_chain()

    # ────────────────────────────────────────────────────────────────
    @staticmethod
    def diff(a_snapshot: Dict[str, Any], b_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two snapshots for divergence."""
        a_len = len(a_snapshot.get("chain", []))
        b_len = len(b_snapshot.get("chain", []))
        a_last = a_snapshot.get("last_hash")
        b_last = b_snapshot.get("last_hash")

        diverged = a_last != b_last or a_len != b_len

        return {
            "diverged": diverged,
            "a_length": a_len,
            "b_length": b_len,
            "a_last_hash": a_last,
            "b_last_hash": b_last,
            "delta": abs(a_len - b_len),
        }

    # ────────────────────────────────────────────────────────────────
    @staticmethod
    def report(snapshot: Dict[str, Any]) -> str:
        """Generate a concise audit summary."""
        verification = GHXLedgerAuditor.verify_snapshot(snapshot)
        summary = {
            "node_id": snapshot.get("node_id", "unknown"),
            "length": len(snapshot.get("chain", [])),
            "last_hash": snapshot.get("last_hash"),
            "verified": verification.get("verified"),
            "error": verification.get("error"),
        }
        return json.dumps(summary, indent=2)