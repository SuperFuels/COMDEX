"""
Tessaris RQC — Resonance → CodexTrace Bridge (v2)
────────────────────────────────────────────────────────────
Stage B2d · Telemetry → CodexTrace v2 integration.

Collects live Φ–ψ–κ–T metrics from photonic operators (⊕, ⟲, ↔)
and publishes them to both CodexMetrics (for GHX Visualizer)
and the MorphicLedger (for persistent time-series telemetry).

Ledger Schema v2 fields:
    operator, timestamp, Φ_mean, ψ_mean,
    resonance_index, coherence_energy,
    entanglement_fidelity, mutual_coherence, phase_correlation,
    gain, closure_state, phi_dot
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional

from backend.modules.cognitive_fabric.metrics_bridge import CODEX_METRICS

LEDGER_PATH = "data/ledger/rqc_live_telemetry.jsonl"
os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#   Core publishing function (v2)
# ──────────────────────────────────────────────
def publish_metrics(op_name: str, payload: Dict[str, Any]) -> None:
    """
    Push metrics from a photonic operator into the Codex/Telemetry system.
    Adds awareness-related fields for resonance closure and adaptive feedback.
    """
    try:
        timestamp = payload.get("timestamp", time.time())

        entry: Dict[str, Any] = {
            "operator": op_name,
            "timestamp": timestamp,
            "Φ_mean": payload.get("Φ_mean"),
            "ψ_mean": payload.get("ψ_mean"),
            "resonance_index": payload.get("resonance_index"),
            "coherence_energy": payload.get("coherence_energy"),
            "entanglement_fidelity": payload.get("entanglement_fidelity"),
            "mutual_coherence": payload.get("mutual_coherence"),
            "phase_correlation": payload.get("phase_correlation"),
            # awareness fields
            "gain": payload.get("gain"),
            "closure_state": payload.get("closure_state"),
            "phi_dot": payload.get("phi_dot"),
        }

        # 1️⃣  Push to CodexMetrics → CFA / GHX
        try:
            CODEX_METRICS.record_event(
                event=f"RQC::{op_name}",
                payload={k: v for k, v in entry.items() if v is not None},
                domain="photon_runtime",
                tags=["telemetry", "resonance", op_name],
            )
            logger.info(f"[ResonanceBridge] Published ({op_name}) → CodexMetrics")
        except Exception as e:
            logger.warning(f"[ResonanceBridge] Publish failed ({op_name}): {e}")

        # 2️⃣  Append to MorphicLedger (JSONL)
        with open(LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # 3️⃣  Optional log
        logger.debug(
            f"[ResonanceBridge] Ledger← {op_name} Φ={entry.get('Φ_mean')} ψ={entry.get('ψ_mean')} "
            f"gain={entry.get('gain')} state={entry.get('closure_state')}"
        )

    except Exception as e:
        logger.warning(f"[ResonanceBridge] Publish failed ({op_name}): {e}")


# ──────────────────────────────────────────────
#   Derived utility: awareness delta (φ̇)
# ──────────────────────────────────────────────
def compute_phi_dot(prev_phi: Optional[float], curr_phi: Optional[float], dt: float) -> Optional[float]:
    """Return rate-of-change of awareness Φ (φ̇) if measurable."""
    if prev_phi is None or curr_phi is None or dt <= 0:
        return None
    return round((curr_phi - prev_phi) / dt, 8)


# ──────────────────────────────────────────────
#   Demo / standalone
# ──────────────────────────────────────────────
if __name__ == "__main__":
    demo = {
        "Φ_mean": 1.0,
        "ψ_mean": 0.98,
        "resonance_index": 0.995,
        "coherence_energy": 0.97,
        "gain": 0.96,
        "closure_state": "stable",
        "phi_dot": 0.0002,
        "timestamp": time.time(),
    }
    publish_metrics("demo_op", demo)
    print("✅ Demo entry written to MorphicLedger v2 and CodexMetrics.")