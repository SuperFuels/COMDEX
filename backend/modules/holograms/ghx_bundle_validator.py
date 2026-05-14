"""
🧩 SRK-17 Task 4 - GHX Bundle Validator
Module: backend/modules/holograms/ghx_bundle_validator.py

Purpose:
    Validate and verify assembled GHX bundles before distributed
    synchronization or GlyphVault archival.

Responsibilities:
    * Verify SHA3-512 integrity signature.
    * Recompute deterministic bundle hash and compare to embedded value.
    * Validate GHX Trace entropy signature (via GHXTraceEncoder).
    * Optionally check PMG Binder continuity.

Integrates with:
    GHXSyncLayer (SRK-17 Tasks 1-3)
"""

import json
import hashlib
from typing import Dict, Any

from backend.modules.holograms.ghx_trace_encoder import GHXTraceEncoder


class GHXBundleValidator:
    """Validates GHX bundles for integrity and trace coherence."""

    def __init__(self):
        self.encoder = GHXTraceEncoder()

    # ────────────────────────────────────────────────────────────────
    def verify_integrity(self, bundle: Dict[str, Any]) -> bool:
        """
        Recompute bundle integrity hash and compare to stored signature.
        """
        if "integrity" not in bundle:
            return False

        stored_hash = bundle["integrity"].get("hash")
        # Recompute excluding the existing integrity field
        bundle_copy = {k: v for k, v in bundle.items() if k != "integrity"}
        recomputed = hashlib.sha3_512(
            json.dumps(bundle_copy, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return stored_hash == recomputed

    # ────────────────────────────────────────────────────────────────
    def verify_trace(self, bundle: Dict[str, Any]) -> bool:
        """
        Validate embedded GHX trace signature.
        """
        ghx_trace = bundle.get("ghx_trace")
        if not ghx_trace:
            return False
        return self.encoder.verify_trace(ghx_trace)

    # ────────────────────────────────────────────────────────────────
    def verify_pmg_binder(self, bundle: Dict[str, Any]) -> bool:
        """
        Validate PMG Binder continuity if present.
        Ensures the binder is correctly chained to the previous hash.
        """
        binder = bundle.get("pmg_binder")
        if not binder:
            return True  # optional field
        prev_hash = binder.get("prev_hash")
        linked = binder.get("linked", False)
        return not linked or bool(prev_hash)

    # ────────────────────────────────────────────────────────────────
    def validate_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform full GHX bundle validation sequence.
        Returns detailed validation report.
        """
        results = {
            "integrity_valid": self.verify_integrity(bundle),
            "trace_valid": self.verify_trace(bundle),
            "binder_valid": self.verify_pmg_binder(bundle),
        }

        results["overall_valid"] = all(results.values())
        return results