# ──────────────────────────────────────────────────────────────
#  Tessaris * C7 - Cognitive Fabric Phase-State Bridge
#  Propagates ψ-κ-T-Φ metrics from MorphicLedger -> Cognitive Fabric Adapter.
#  Enables synchronized reasoning between AION ↔ QQC ↔ CFA.
# ──────────────────────────────────────────────────────────────

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any

# ✅ Core Fabric
from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA

logger = logging.getLogger("PhaseStateBridge")

LOG_PATH = "backend/logs/phase_state_events.jsonl"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


class PhaseStateBridge:
    """
    Bridge for real-time ψ-κ-T-Φ propagation into the Cognitive Fabric Adapter (CFA).
    """

    def __init__(self):
        self.fabric = CFA
        self.state_cache = {"psi": 0.0, "kappa": 0.0, "T": 0.0, "phi": 0.0}
        logger.info("✅ PhaseStateBridge initialized (ψ-κ-T-Φ link active).")

    def ingest(self, packet: Dict[str, Any]):
        """
        Ingest a resonance packet from MorphicLedger or QQC feedback.
        Example packet:
        {
            "psi": 0.83, "kappa": 0.42, "T": 0.97, "phi": 0.56,
            "timestamp": "2025-10-19T11:12:00Z"
        }
        """
        try:
            ψ, κ, T, Φ = (
                float(packet.get("psi", 0.0)),
                float(packet.get("kappa", 0.0)),
                float(packet.get("T", 0.0)),
                float(packet.get("phi", 0.0)),
            )
            self.update_fabric_state(ψ, κ, T, Φ)
            self.log_event(ψ, κ, T, Φ)
        except Exception as e:
            logger.error(f"[C7] Ingest failed: {e}")

    def update_fabric_state(self, ψ: float, κ: float, T: float, Φ: float):
        """
        Update the Cognitive Fabric Adapter state with new resonance metrics.
        """
        try:
            self.state_cache.update({"psi": ψ, "kappa": κ, "T": T, "phi": Φ})
            CFA.update_phase_state(ψ=ψ, κ=κ, T=T, Φ=Φ)
            logger.debug(f"[C7] Updated CFA phase state: ψ={ψ}, κ={κ}, T={T}, Φ={Φ}")
        except Exception as e:
            logger.warning(f"[C7] Fabric update failed: {e}")

    def log_event(self, ψ: float, κ: float, T: float, Φ: float):
        """
        Append ψ-κ-T-Φ update event to persistent log for validation tracking.
        """
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "psi": ψ,
            "kappa": κ,
            "T": T,
            "phi": Φ,
        }
        try:
            with open(LOG_PATH, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"[C7] Logging failed: {e}")

    def verify_stability(self, tolerance: float = 1e-3) -> bool:
        """
        Check if recent phase-state changes are within stable resonance tolerance.
        Used by E6 orchestrator for Δφ control.
        """
        try:
            φ_values = []
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, "r") as f:
                    for line in f.readlines()[-50:]:
                        data = json.loads(line)
                        φ_values.append(data.get("phi", 0.0))
            if len(φ_values) < 2:
                return True
            delta = abs(φ_values[-1] - φ_values[-2])
            stable = delta < tolerance
            logger.info(f"[C7] Phase stability check: Δφ={delta:.6f} -> {'stable' if stable else 'unstable'}")
            return stable
        except Exception as e:
            logger.warning(f"[C7] Stability check failed: {e}")
            return False