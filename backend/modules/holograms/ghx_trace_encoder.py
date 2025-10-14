"""
🧩 SRK-17 Task 3 — USR Telemetry → GHX Trace Encoder
Module: backend/modules/holograms/ghx_trace_encoder.py

Purpose:
    Transform Unified Symbolic Runtime (USR) telemetry into a GHX Trace
    record suitable for CodexTrace ingestion and GHX bundle embedding.

Phase:
    SRK-17 Task 3 — USR Telemetry → GHX Trace Encoder
"""

import time
import json
import hashlib
from uuid import uuid4


class GHXTraceEncoder:
    """Converts USR telemetry into GHX-compatible trace packages."""

    def __init__(self):
        self._last_trace = None

    def encode(self, usr_telemetry: dict) -> dict:
        """
        Generate a GHX Trace entry from USR telemetry data.

        Args:
            usr_telemetry: Dict output from UnifiedSymbolicRuntime.export_telemetry().

        Returns:
            dict — structured GHX trace with integrity hash and stability metrics.
        """
        coherence = usr_telemetry.get("coherence", 1.0)
        avg_coh = usr_telemetry.get("avg_coherence", coherence)
        mode_ratio = usr_telemetry.get("mode_ratio", {})
        recent = usr_telemetry.get("recent", [])

        # Stability metric: combine avg_coh with photon/symbolic ratio weighting
        r_ph = mode_ratio.get("photon", 0.5)
        r_sy = mode_ratio.get("symbolic", 0.5)
        stability_index = round((avg_coh * (0.6 * r_ph + 0.4 * r_sy)), 6)

        trace = {
            "trace_id": f"GHXTRACE-{uuid4()}",
            "timestamp": time.time(),
            "coherence_vector": [coherence, avg_coh],
            "mode_ratio": mode_ratio,
            "telemetry_count": usr_telemetry.get("telemetry_count", len(recent)),
            "stability_index": stability_index,
            "recent": recent,
        }

        # Compute deterministic entropy signature
        entropy_signature = hashlib.sha3_512(
            json.dumps(trace, sort_keys=True).encode("utf-8")
        ).hexdigest()
        trace["entropy_signature"] = entropy_signature
        trace["hash_verified"] = True

        self._last_trace = trace
        return trace

    def verify_trace(self, trace: dict) -> bool:
        """Recompute and validate entropy signature."""
        recalculated = hashlib.sha3_512(
            json.dumps(
                {k: v for k, v in trace.items() if k not in ["entropy_signature", "hash_verified"]},
                sort_keys=True
            ).encode("utf-8")
        ).hexdigest()
        return recalculated == trace.get("entropy_signature")