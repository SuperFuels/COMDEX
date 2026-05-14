"""
✅ SRK-17 Task 4 - Test: GHX Bundle Validator
Verifies that GHXBundleValidator correctly validates bundle integrity,
trace signature, and PMG binder continuity.
"""

import pytest
import time
import json
import hashlib
from uuid import uuid4

from backend.modules.holograms.ghx_bundle_validator import GHXBundleValidator
from backend.modules.holograms.ghx_trace_encoder import GHXTraceEncoder


@pytest.mark.asyncio
async def test_ghx_bundle_validator_integrity_and_trace():
    encoder = GHXTraceEncoder()
    validator = GHXBundleValidator()

    # ───────────────────────────────────────────────
    # Simulated USR telemetry (from UnifiedSymbolicRuntime)
    usr_telemetry = {
        "coherence": 0.83,
        "avg_coherence": 0.8,
        "mode_ratio": {"photon": 0.61, "symbolic": 0.39},
        "telemetry_count": 12,
    }

    ghx_trace = encoder.encode(usr_telemetry)

    # ───────────────────────────────────────────────
    # Construct simulated GHX bundle
    bundle = {
        "ghx_id": f"GHX-{uuid4()}",
        "timestamp": time.time(),
        "pmg_snapshot": {"states": {"a": 1, "b": 2}},
        "resonance_ledger": {"edges": 3, "stability": 0.97},
        "usr_telemetry": usr_telemetry,
        "pmg_binder": {
            "binder_seq": int(time.time() * 1000),
            "prev_hash": "abc123",
            "curr_hash": "def456",
            "linked": True,
        },
        "ghx_trace": ghx_trace,
    }

    # Add integrity hash
    integrity_hash = hashlib.sha3_512(
        json.dumps(bundle, sort_keys=True).encode("utf-8")
    ).hexdigest()
    bundle["integrity"] = {"hash": integrity_hash, "verified": True}

    # ───────────────────────────────────────────────
    # Run full validation
    report = validator.validate_bundle(bundle)

    # ───────────────────────────────────────────────
    # Assertions
    assert report["integrity_valid"] is True, "Integrity hash mismatch"
    assert report["trace_valid"] is True, "GHX trace failed verification"
    assert report["binder_valid"] is True, "PMG binder not linked correctly"
    assert report["overall_valid"] is True, "Bundle failed composite validation"


@pytest.mark.asyncio
async def test_ghx_bundle_validator_detects_tampering():
    encoder = GHXTraceEncoder()
    validator = GHXBundleValidator()

    usr_telemetry = {"coherence": 0.75, "telemetry_count": 5}
    ghx_trace = encoder.encode(usr_telemetry)

    bundle = {
        "ghx_id": f"GHX-{uuid4()}",
        "timestamp": time.time(),
        "usr_telemetry": usr_telemetry,
        "ghx_trace": ghx_trace,
    }

    # Compute valid hash first
    good_hash = hashlib.sha3_512(
        json.dumps(bundle, sort_keys=True).encode("utf-8")
    ).hexdigest()

    # Introduce tampering by modifying telemetry after hash
    bundle["usr_telemetry"]["coherence"] = 0.12
    bundle["integrity"] = {"hash": good_hash, "verified": True}

    report = validator.validate_bundle(bundle)

    assert report["integrity_valid"] is False, "Tampering not detected"
    assert report["overall_valid"] is False, "Invalid bundle incorrectly passed validation"