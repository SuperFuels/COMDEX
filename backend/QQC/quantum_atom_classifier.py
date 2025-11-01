# ──────────────────────────────────────────────────────────────
#  Tessaris * Quantum Atom Classifier (v1.0)
#  Symbolic resonance-based intent classifier for AION.
#  Fallback / companion to the LLMClassifier - uses Symatics logic.
# ──────────────────────────────────────────────────────────────

import math
import random
import logging
import asyncio
from typing import Any, Dict

# Optional: import from Symatics Algebra if available
try:
    from backend.modules.symatics.symatics_core import Wave, Photon
except ImportError:
    Wave = Photon = None

# Optional link to Morphic Ledger
try:
    from backend.modules.morphic.ledger import MorphicLedger
except ImportError:
    MorphicLedger = None

logger = logging.getLogger("QuantumAtomClassifier")


class QuantumAtomClassifier:
    """
    Symbolic fallback for AION's LLM classifier.
    Computes a resonance pattern (ψ-κ-T-Φ) signature and
    classifies intent based on harmonic ratios.
    """

    def __init__(self):
        self.ledger = MorphicLedger() if MorphicLedger else None
        self.history = []
        self.field_baseline = 0.618  # golden ratio baseline

        logger.info("🌀 QuantumAtomClassifier initialized (Symatics fallback active).")

    # ──────────────────────────────────────────────────────────────
    async def resonate_intent(self, input_signal: Any) -> str:
        """
        Analyze the symbolic or textual input using resonance metrics.
        Returns an intent tag similar to the LLM classifier.
        """
        try:
            # Convert to symbolic waveform
            spectrum = self._compute_resonance(input_signal)
            psi, kappa, T, phi = spectrum["psi"], spectrum["kappa"], spectrum["T"], spectrum["phi"]

            # Symbolic classification thresholds (tuned to Symatics Algebra)
            tag = self._map_resonance_to_tag(psi, kappa, T, phi)
            self.history.append({"input": str(input_signal), "tag": tag, "spectrum": spectrum})

            # Optional MorphicLedger trace
            if self.ledger:
                try:
                    self.ledger.record({
                        "timestamp": asyncio.get_event_loop().time(),
                        "module": "QuantumAtomClassifier",
                        "tag": tag,
                        "spectrum": spectrum,
                    })
                except Exception:
                    pass

            logger.debug(f"[QuantumAtomClassifier] {tag} <- ψ={psi:.3f}, κ={kappa:.3f}, Φ={phi:.3f}")
            return tag

        except Exception as e:
            logger.error(f"[QuantumAtomClassifier] Resonance classification failed: {e}")
            return "reflect"

    # ──────────────────────────────────────────────────────────────
    def _compute_resonance(self, signal: Any) -> Dict[str, float]:
        """
        Estimate symbolic resonance metrics (ψ, κ, T, Φ)
        from textual or structured input.
        """
        text = str(signal).lower()
        entropy = sum(ord(c) for c in text) % 2048 / 2048.0
        coherence = (math.sin(entropy * math.pi) + 1) / 2
        kappa = abs(math.cos(entropy * math.pi * 1.3))
        T = 1.0 + (coherence - 0.5)
        phi = (coherence * self.field_baseline) + (random.random() * 0.05)

        return {
            "psi": entropy,
            "kappa": kappa,
            "T": T,
            "phi": phi,
        }

    # ──────────────────────────────────────────────────────────────
    def _map_resonance_to_tag(self, psi: float, kappa: float, T: float, phi: float) -> str:
        """
        Translate resonance ratios into semantic tags.
        """
        coherence = (psi + kappa) / 2  # compute first

        if phi > 0.66 and coherence > 0.7:
            return "reflect"
        if T > 1.2 and kappa > 0.8:
            return "plan"
        if psi < 0.3 and phi > 0.5:
            return "dream"
        if abs(kappa - psi) < 0.15:
            return "emotion"
        if T > 1.4:
            return "energy"
        if phi < 0.4 and psi > 0.8:
            return "predict"
        if psi < 0.2 and kappa < 0.3:
            return "memory"
        return "reflect"
    # ──────────────────────────────────────────────────────────────
    def last_resonance(self) -> Dict[str, Any]:
        """Return the last classified resonance spectrum."""
        return self.history[-1] if self.history else {}