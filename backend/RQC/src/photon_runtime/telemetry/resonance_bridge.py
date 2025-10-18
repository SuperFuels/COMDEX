"""
Tessaris RQC — Resonance → CodexTrace Bridge
────────────────────────────────────────────────────────────
Stage B2d · Telemetry → CodexTrace v2 integration.

Collects live Φ–ψ–κ–T metrics from photonic operators (⊕, ⟲, ↔)
and publishes them to both CodexMetrics (for GHX Visualizer)
and the MorphicLedger (for persistent time-series telemetry).
"""

import os
import json
import time
import logging
from typing import Dict, Any

from backend.modules.cognitive_fabric.metrics_bridge import CODEX_METRICS

LEDGER_PATH = "data/ledger/rqc_live_telemetry.jsonl"
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#   Ensure ledger folder exists
# ──────────────────────────────────────────────
os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)


# ──────────────────────────────────────────────
#   Core publishing function
# ──────────────────────────────────────────────
def publish_metrics(op_name: str, payload: Dict[str, Any]) -> None:
    """
    Push metrics from a photonic operator into the Codex / Telemetry system.
    This ensures dual persistence:
      • CodexMetrics → GHXVisualizer (live telemetry)
      • MorphicLedger → JSONL historical archive
    """
    try:
        # Build canonical telemetry record
        entry = {
            "operator": op_name,
            "timestamp": payload.get("timestamp", time.time()),
            "Φ_mean": payload.get("Φ_mean"),
            "ψ_mean": payload.get("ψ_mean"),
            "resonance_index": payload.get("resonance_index"),
            "coherence_energy": payload.get("coherence_energy"),
            "entanglement_fidelity": payload.get("entanglement_fidelity"),
            "mutual_coherence": payload.get("mutual_coherence"),
            "phase_correlation": payload.get("phase_correlation"),
        }

        # 1️⃣ Push to CodexMetrics (live GHX pipeline)
        try:
            CODEX_METRICS.push(op_name, payload)
            logger.info(f"[ResonanceBridge] Published ({op_name}) → CodexMetrics")
        except Exception as e:
            logger.warning(f"[ResonanceBridge] CodexMetrics publish failed ({op_name}): {e}")

        # 2️⃣ Persist to MorphicLedger JSONL
        try:
            with open(LEDGER_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"[ResonanceBridge] Ledger write failed ({op_name}): {e}")

        # 3️⃣ Debug log summary
        logger.debug(
            f"[ResonanceBridge] {op_name}: Φ={entry.get('Φ_mean')} "
            f"ψ={entry.get('ψ_mean')} R={entry.get('resonance_index')} "
            f"C={entry.get('coherence_energy')}"
        )

    except Exception as e:
        logger.error(f"[ResonanceBridge] Fatal publish failure ({op_name}): {e}")


# ──────────────────────────────────────────────
#   Demo / standalone run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    demo = {
        "Φ_mean": 1.0,
        "ψ_mean": 0.98,
        "resonance_index": 0.995,
        "coherence_energy": 0.97,
        "timestamp": time.time(),
    }
    publish_metrics("demo_op", demo)
    print("✅ Demo entry written to ledger and CodexMetrics.")