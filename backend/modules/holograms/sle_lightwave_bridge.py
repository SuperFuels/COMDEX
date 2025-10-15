# ──────────────────────────────────────────────
#  Tessaris • SLE → HST LightWave Coupling Layer
#  (Stage 4 HQCE Integration)
#  Feeds live beam data from the Symbolic Light Engine into
#  the HST field tensor for dynamic ψ–κ–T field regulation.
# ──────────────────────────────────────────────

import uuid
import time
import logging
import asyncio
from typing import Dict, Any, Optional

from backend.modules.holograms.hst_generator import HSTGenerator
from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController

logger = logging.getLogger(__name__)


class SLELightWaveBridge:
    """
    Couples real-time LightWave beam data from SLE into the HST field tensor.
    The bridge translates physical coherence + drift metrics into ψ–κ–T
    tensor updates for the holographic runtime.
    """

    def __init__(self, hst: Optional[HSTGenerator] = None):
        self.hst = hst or HSTGenerator()
        self.feedback_controller = MorphicFeedbackController()
        self.last_update: Optional[Dict[str, Any]] = None
        self.session_id = str(uuid.uuid4())
        self._beam_counter = 0
        logger.info(f"[SLELightWaveBridge] Initialized bridge session → {self.session_id}")

    # ────────────────────────────────────────────
    #  Ingestion of Beam Data
    # ────────────────────────────────────────────
    def inject_beam_feedback(self, beam_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accept a beam feedback packet from SLE and translate it into
        an HST field node update + ψ–κ–T tensor correction.
        Expected input keys:
            {
                "beam_id": str,
                "coherence": float,
                "phase_shift": float,
                "entropy_drift": float,
                "gain": float,
                "timestamp": float
            }
        """
        try:
            beam_id = beam_data.get("beam_id", f"beam-{self._beam_counter}")
            self._beam_counter += 1

            coherence = float(beam_data.get("coherence", 0.5))
            entropy_drift = float(beam_data.get("entropy_drift", 0.0))
            gain = float(beam_data.get("gain", 1.0))
            phase_shift = float(beam_data.get("phase_shift", 0.0))

            # Normalize coherence and entropy range
            coherence = max(0.0, min(1.0, coherence))
            entropy = max(0.0, min(1.0, 1.0 - coherence))

            # Update HST field node
            self.hst.inject_lightwave_beam({
                "beam_id": beam_id,
                "coherence": coherence,
                "entropy": entropy,
                "phase_shift": phase_shift,
                "gain": gain,
                "entropy_drift": entropy_drift,
                "timestamp": beam_data.get("timestamp", time.time()),
            })

            # Run morphic feedback regulation
            adjustment = self.feedback_controller.regulate(
                self.hst.field_tensor,
                list(self.hst.nodes.values())
            )
            self.last_update = adjustment

            logger.info(f"[SLELightWaveBridge] Beam {beam_id} → ΔC={adjustment.get('correction', 0):.4f}")
            return adjustment

        except Exception as e:
            logger.error(f"[SLELightWaveBridge] Failed to inject beam feedback: {e}")
            return {"status": "error", "error": str(e)}

    # ────────────────────────────────────────────
    #  Live Monitoring and Broadcast
    # ────────────────────────────────────────────
    async def broadcast_field_state(self):
        """Push the current HST + ψ–κ–T state over WebSocket (async safe)."""
        try:
            from backend.modules.symbolic.hst.hst_websocket_streamer import broadcast_replay_paths
            payload = {
                "type": "hst_field_state",
                "session_id": self.session_id,
                "field_tensor": self.hst.field_tensor,
                "adjustment": self.last_update or {},
                "timestamp": time.time(),
            }
            # Non-blocking broadcast
            asyncio.create_task(broadcast_replay_paths(self.session_id, []))
            logger.info(f"[SLELightWaveBridge] Broadcasted HST field state → {self.session_id}")
        except Exception as e:
            logger.warning(f"[SLELightWaveBridge] Broadcast failed: {e}")

    # ────────────────────────────────────────────
    #  Diagnostic Dump
    # ────────────────────────────────────────────
    def summarize_state(self) -> Dict[str, Any]:
        """Return a compact summary for diagnostic dashboards."""
        psi_kappa_T = self.hst.field_tensor or {}
        return {
            "session_id": self.session_id,
            "last_psi_kappa_T": psi_kappa_T,
            "last_adjustment": self.last_update or {},
            "node_count": len(self.hst.nodes),
            "timestamp": time.time(),
        }