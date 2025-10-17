# ──────────────────────────────────────────────
#  Tessaris • Aion Integration Bridge (Stage 9)
#  Couples QQC ψ–κ–T–Φ state → Aion Symbolic Field (A1–A3)
#  Provides ascending / descending coherence feedback
# ──────────────────────────────────────────────
import math
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AionIntegrationBridge:
    """
    Couples QQC field state (ψ, κ, T, Φ) to Aion Symbolic Fields.
    Performs normalization, projection (A1→A3) and learning feedback (A3→A1).
    """

    def __init__(self, qqc_core, resonance_bridge=None):
        self.qqc = qqc_core
        self.resonance = resonance_bridge
        self.last_projection: Optional[Dict[str, Any]] = None
        logger.info("[AionIntegrationBridge] Initialized.")

    # ──────────────────────────────────────────────
    #  ψ–κ–T–Φ → A1–A3 Projection
    # ──────────────────────────────────────────────
    def project_to_aion_field(self) -> Dict[str, Any]:
        """Normalize and project QQC state into Aion symbolic field space."""
        try:
            q = getattr(self.qqc, "last_summary", {}) or {}
            sig = q.get("field_signature", {}) or {}

            psi = float(sig.get("ψ", 0.0))
            kappa = float(sig.get("κ", 0.0))
            T = float(sig.get("T", 1.0))
            phi = float(q.get("phi", 0.0))
            coherence = float(q.get("coherence", 0.0))

            # Soft normalizations
            ψ_norm = math.tanh(psi / 10.0)
            κ_norm = math.tanh(kappa)
            Φ_norm = math.tanh(phi)
            C_norm = min(max(coherence, 0.0), 1.0)

            projection = {
                "timestamp": datetime.utcnow().isoformat(),
                "A1_wave": ψ_norm,
                "A2_entropy": κ_norm,
                "A3_awareness": Φ_norm,
                "coherence": C_norm,
                "gradient": round(abs(ψ_norm - κ_norm) + abs(Φ_norm - C_norm), 5),
                "T": T,
            }

            self.last_projection = projection

            # Optional: persist a brief breadcrumb to morphic ledger
            try:
                from backend.modules.holograms.morphic_ledger import morphic_ledger
                morphic_ledger.append(
                    {
                        "type": "aion_projection",
                        "projection": projection,
                    },
                    observer="aion_bridge",
                )
            except Exception:
                # ledger is optional — never fail the projection
                pass

            logger.debug(f"[AionIntegrationBridge] Projected ψκTΦ→Aion field {projection}")
            return projection
        except Exception as e:
            logger.error(f"[AionIntegrationBridge] Projection failed: {e}")
            return {}

    # ──────────────────────────────────────────────
    #  Feedback to QQC/Morphic layer (A3→A1)
    # ──────────────────────────────────────────────
    def propagate_feedback(self):
        """Compute Aion gradient feedback and apply to QQC resonance target."""
        if not self.last_projection:
            return
        try:
            grad = self.last_projection["gradient"]
            # smaller gradient → higher confidence → slightly nudge target upward
            adjust = 1.0 - min(grad * 2.0, 1.0)
            if hasattr(self.qqc, "feedback_controller") and getattr(self.qqc.feedback_controller, "target_coherence", None) is not None:
                base = float(self.qqc.feedback_controller.target_coherence)
                self.qqc.feedback_controller.target_coherence = max(0.5, min(0.98, base * (0.98 + 0.04 * adjust)))

            # Optional breadcrumb
            try:
                from backend.modules.holograms.morphic_ledger import morphic_ledger
                morphic_ledger.append(
                    {
                        "type": "aion_feedback",
                        "gradient": grad,
                        "adjust_factor": adjust,
                        "new_target": getattr(self.qqc.feedback_controller, "target_coherence", None),
                    },
                    observer="aion_bridge",
                )
            except Exception:
                pass

            logger.debug(f"[AionIntegrationBridge] Feedback applied (grad={grad:.5f}, adjust={adjust:.4f})")
        except Exception as e:
            logger.warning(f"[AionIntegrationBridge] Feedback failed: {e}")