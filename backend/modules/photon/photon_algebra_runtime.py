"""
💡 Photon Algebra Runtime - SRK-12 Task 1.1
Core computational substrate for Tessaris photonic processing with persistent state logging.

This engine interprets photon capsules, applies symbolic algebraic operations,
and performs wave-based computation entirely in the photonic domain - no binary fallback.

New in SRK-12.1:
 - Integration with PhotonMemoryGrid (entanglement persistence)
 - Asynchronous state persistence after each capsule execution
"""

import math
import random
import time
import asyncio
from typing import Dict, Any, List

from backend.modules.photon.photon_capsule_validator import validate_photon_capsule
from backend.modules.glyphwave.core.coherence_optimizer import DynamicCoherenceOptimizer
from backend.symatics.operators import OPS  # symbolic operator registry
from backend.modules.photon.memory.photon_memory_grid import PhotonMemoryGrid  # 🔷 new import


class PhotonAlgebraRuntime:
    """
    ⚛ Photon Algebra Runtime - executes symbolic operations
    directly over photon capsules (entangled wave representations).
    """

    def __init__(self):
        self.optimizer = DynamicCoherenceOptimizer()
        self.history: List[Dict[str, Any]] = []
        self.memory_grid = PhotonMemoryGrid()  # instantiate persistence layer

    # ────────────────────────────────────────────────────────────────
    def _normalize_wave(self, wave):
        """Normalize wave amplitude to unit coherence."""
        magnitude = math.sqrt(sum(x**2 for x in wave)) or 1.0
        return [x / magnitude for x in wave]

    def _simulate_interference(self, wave_a, wave_b):
        """Compute interference pattern between two waves."""
        return [a + b for a, b in zip(wave_a, wave_b)]

    # ────────────────────────────────────────────────────────────────
    async def execute(self, capsule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a symbolic photon capsule in the photonic domain.

        Args:
            capsule: Validated Photon Capsule.

        Returns:
            dict: Resultant photon state.
        """
        validate_photon_capsule(capsule)
        glyphs = capsule.get("glyphs", [])
        if not glyphs:
            raise ValueError("Photon capsule contains no glyphs.")

        result_wave = [random.random() for _ in range(3)]
        result_wave = self._normalize_wave(result_wave)

        for glyph in glyphs:
            op = glyph.get("operator", "⊕")
            args = glyph.get("args", [])
            meta = glyph.get("meta", {})

            # Adaptive symbolic operation mapping
            if op == "⊕":  # Superposition
                result_wave = self._normalize_wave([x + random.uniform(-0.1, 0.1) for x in result_wave])
            elif op == "↔":  # Entanglement
                result_wave = self._simulate_interference(result_wave, [random.random() for _ in range(3)])
            elif op == "⟲":  # Resonance
                factor = math.sin(time.time() % math.pi)
                result_wave = [x * factor for x in result_wave]
            elif op == "∇":  # Collapse
                result_wave = [round(x, 3) for x in result_wave]
            elif op == "μ":  # Measurement
                meta["measurement"] = sum(result_wave)
            else:
                OPS.apply(op, result_wave, args)

            # Optimize coherence dynamically
            self.optimizer.optimize_if_needed({"wave": result_wave})
            self.history.append({
                "op": op,
                "args": args,
                "meta": meta,
                "result": result_wave,
                "timestamp": time.time(),
            })

        result_state = {
            "final_wave": result_wave,
            "trace": self.history,
            "timestamp": time.time(),
        }

        # 🔷 SRK-12.1 - Persist result state to Photon Memory Grid asynchronously
        asyncio.create_task(
            self.memory_grid.store_capsule_state(
                capsule.get("name", f"capsule_{int(time.time())}"),
                result_state
            )
        )

        return result_state