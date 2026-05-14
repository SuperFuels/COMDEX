# ==========================================================
#  Tessaris * Cognitive Fabric Resonance Link
#  Unifies Φ-ψ-κ-T-CFA telemetry across AION / QQC / Morphic
#  Stage 14.1 - Resonance Telemetry Bridge
# ==========================================================

import time
import json
import logging
from typing import Dict, Any, Optional

from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA
from backend.modules.cognitive_fabric.metrics_bridge import CODEX_METRICS

logger = logging.getLogger("FabricResonanceLink")


class FabricResonanceLink:
    """
    Bridges incoming Fabric Stream resonance tensors (ψ̄ κ̄ T̄ Φ̄ σ)
    into the Cognitive Fabric + CodexMetrics bus for unified awareness telemetry.
    """

    def __init__(self, qqc_core=None):
        self.qqc = qqc_core
        self.last_packet: Optional[Dict[str, Any]] = None
        self.history: list[Dict[str, Any]] = []
        logger.info("[FabricResonanceLink] Initialized and listening for live Φ-ψ coupling tensors.")

    # ------------------------------------------------------
    #  Primary Ingest
    # ------------------------------------------------------
    def ingest_tensor(self, tensor: Dict[str, Any]):
        """
        Receive and process a live tensor from /fabric/stream endpoint.
        Expected keys: ψ̄, κ̄, T̄, Φ̄, σ
        """
        try:
            psi = float(tensor.get("ψ̄", 0.0))
            kappa = float(tensor.get("κ̄", 0.0))
            T = float(tensor.get("T̄", 0.0))
            phi = float(tensor.get("Φ̄", 0.0))
            sigma = float(tensor.get("σ", 0.0))

            coherence_energy = round(phi * psi * sigma, 8)
            resonance_index = round((psi + kappa + T + phi) / 4.0, 8)

            packet = {
                "timestamp": time.time(),
                "Φ_mean": phi,
                "ψ_mean": psi,
                "κ_mean": kappa,
                "T_mean": T,
                "correlation": sigma,
                "coherence_energy": coherence_energy,
                "resonance_index": resonance_index,
            }

            self.last_packet = packet
            self.history.append(packet)
            if len(self.history) > 500:
                self.history.pop(0)

            # 1️⃣ Commit to CodexMetrics (local + CFA mirror)
            CODEX_METRICS.record_event(
                "fabric_resonance_update",
                payload=packet,
                domain="symatics/resonance_coupling",
                tags=["fabric", "Φψ", "telemetry"],
            )

            # 2️⃣ Mirror to QQC core if present
            if self.qqc:
                self.qqc.last_summary = self.qqc.last_summary or {}
                self.qqc.last_summary.update({
                    "fabric_sync": {
                        "Φ": phi,
                        "ψ": psi,
                        "κ": kappa,
                        "T": T,
                        "σ": sigma,
                        "coherence_energy": coherence_energy,
                        "resonance_index": resonance_index,
                    }
                })

            # 3️⃣ Publish into CFA bus for global access
            try:
                CFA.commit(
                    source="FABRIC_LINK",
                    intent="update_resonance_state",
                    payload=packet,
                    domain="symatics/resonance_coupling",
                    tags=["resonance", "Φψ", "fabric"],
                )
            except Exception as e:
                logger.warning(f"[FabricResonanceLink] CFA commit failed: {e}")

            logger.info(
                f"[FabricResonanceLink] Φ={phi:.3f}, ψ={psi:.3f}, κ={kappa:.3f}, σ={sigma:.3f}, EΦψ={coherence_energy:.4f}"
            )

        except Exception as e:
            logger.exception(f"[FabricResonanceLink] Ingest failed: {e}")

    # ------------------------------------------------------
    #  Utility accessors
    # ------------------------------------------------------
    def latest(self) -> Optional[Dict[str, Any]]:
        return self.last_packet

    def recent(self, n: int = 10) -> list[Dict[str, Any]]:
        return self.history[-n:]

    def export_log(self, path: str = "data/metrics/fabric_resonance_log.json"):
        """Dump the recent history to a JSON file for visualizers."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.history[-100:], f, indent=2)
            logger.info(f"[FabricResonanceLink] Exported last {min(len(self.history),100)} entries -> {path}")
        except Exception as e:
            logger.error(f"[FabricResonanceLink] Log export failed: {e}")