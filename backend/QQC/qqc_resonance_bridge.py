# ──────────────────────────────────────────────
#  Tessaris * QQC Resonance Bridge (Stage 8)
#  Couples QuantumMorphicRuntime ψ-κ-T output ↔ QQC awareness core
#  Provides bidirectional resonance feedback and Morphic Ledger sync
# ──────────────────────────────────────────────

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class QQCResonanceBridge:
    """Bridges Morphic ψ-κ-T runtime signatures into QQC coherence core."""

    def __init__(self, qqc_core, morphic_runtime):
        self.qqc = qqc_core
        self.runtime = morphic_runtime
        self.last_sync: Optional[Dict[str, Any]] = None
        logger.info("[QQCResonanceBridge] Initialized for ψ-κ-T coupling.")

    # ──────────────────────────────────────────────
    #  ψ-κ-T -> QQC Φ Sync
    # ──────────────────────────────────────────────
    def sync_from_morphic(self):
        """Inject latest Morphic ψ-κ-T state into QQC awareness cycle."""
        try:
            ψκT = getattr(self.runtime, "last_field_signature", None)
            if not ψκT:
                logger.warning("[QQCResonanceBridge] No ψ-κ-T signature available.")
                return

            coherence = ψκT.get("coherence", 0.0)
            psi = ψκT.get("psi", 0.0)
            kappa = ψκT.get("kappa", 0.0)
            T = ψκT.get("T", 1.0)

            # Update internal QQC feedback controller
            if hasattr(self.qqc, "feedback_controller"):
                self.qqc.feedback_controller.target_coherence = coherence

            # Update last_summary fields for resonance tracking
            self.qqc.last_summary = self.qqc.last_summary or {}
            self.qqc.last_summary.update({
                "morphic_sync": {
                    "ψ": psi,
                    "κ": kappa,
                    "T": T,
                    "coherence": coherence,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            })

            logger.debug(f"[QQCResonanceBridge] Synced ψ={psi:.4f}, κ={kappa:.4f}, T={T:.4f}, coherence={coherence:.4f}")

        except Exception as e:
            logger.error(f"[QQCResonanceBridge] Morphic sync failed: {e}")

    # ──────────────────────────────────────────────
    #  QQC Φ -> Morphic Feedback
    # ──────────────────────────────────────────────
    def propagate_to_morphic(self):
        """Feed QQC Φ / ΔΦ awareness metrics back into Morphic Ledger."""
        try:
            summary = getattr(self.qqc, "last_summary", {})
            if not summary:
                return

            phi = summary.get("phi", 0.0)
            delta_phi = summary.get("delta_phi", 0.0)
            coherence = summary.get("coherence", 0.0)

            from backend.modules.holograms.morphic_ledger import morphic_ledger
            morphic_ledger.append({
                "timestamp": datetime.utcnow().isoformat(),
                "Φ": phi,
                "ΔΦ": delta_phi,
                "coherence": coherence,
                "origin": "QQCResonanceBridge",
            }, observer="qqc_core")

            logger.debug(f"[QQCResonanceBridge] Propagated Φ={phi:.4f}, ΔΦ={delta_phi:.4f} -> Morphic Ledger.")

        except Exception as e:
            logger.warning(f"[QQCResonanceBridge] Feedback propagation failed: {e}")