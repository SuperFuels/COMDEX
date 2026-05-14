# ── Symbolic-Holographic Convergence Engine (ψ-κ-T Learning Loop) ──────────────
import asyncio
import logging
from datetime import datetime
from backend.modules.holograms.morphic_ledger import morphic_ledger
from backend.QQC.qqc_central_kernel import QuantumQuadCore
from backend.modules.tessaris.tessaris_runtime import TessarisRuntime

logger = logging.getLogger(__name__)


class ConvergenceEngine:
    """
    Links Tessaris symbolic reasoning with HQCE holographic coherence.

    Periodically samples ψ-κ-T-C tensors from the Morphic Ledger and
    adjusts both the TessarisRuntime (symbolic cognition field) and
    QuantumQuadCore (holographic resonance engine) parameters.

    Stage 13: Symbolic-Holographic Convergence Loop
    """

    def __init__(self, qqc_kernel: QuantumQuadCore, tessaris: TessarisRuntime):
        self.qqc = qqc_kernel
        self.tessaris = tessaris
        self.last_update = None
        self.running = False
        self.interval = 2.0  # seconds between feedback iterations

    async def run(self):
        """Start adaptive ψ-κ-T feedback loop."""
        self.running = True
        logger.info("[CONVERGENCE] Symbolic-Holographic loop active.")

        while self.running:
            try:
                entry = morphic_ledger.query_latest()
                if not entry:
                    await asyncio.sleep(self.interval)
                    continue

                tensor = entry.get("tensor", {})
                psi = tensor.get("psi", 0.0)
                kappa = tensor.get("kappa", 0.0)
                T = tensor.get("T", 0.0)
                coherence = tensor.get("coherence", 0.0)

                # ── Adaptive symbolic and quantum tuning
                self.tessaris.adjust_resonance(coherence)
                self.qqc.tune_field(lambda_=psi, curvature=kappa, temp_flux=T)

                # ── Optional: log to Morphic Ledger feedback trace
                morphic_ledger.append(
                    {"psi": psi, "kappa": kappa, "T": T, "coherence": coherence,
                     "metadata": {"source": "ConvergenceEngine", "action": "feedback"}},
                    observer="ConvergenceLoop"
                )

                self.last_update = datetime.utcnow()
                logger.debug(
                    f"[CONVERGENCE] ψ={psi:.3f}, κ={kappa:.3f}, T={T:.3f}, C={coherence:.3f}"
                )

                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[CONVERGENCE] Loop error: {e}")
                await asyncio.sleep(self.interval * 2)

        logger.info("[CONVERGENCE] Loop halted.")

    async def stop(self):
        """Stop the convergence loop."""
        self.running = False
        logger.info("[CONVERGENCE] Stop signal received.")