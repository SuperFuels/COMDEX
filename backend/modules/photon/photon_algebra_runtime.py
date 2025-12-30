"""
💡 Photon Algebra Runtime - SRK-12 Task 1.1
Core computational substrate for Tessaris photonic processing with persistent state logging.

This engine interprets photon capsules, applies symbolic algebraic operations,
and performs wave-based computation entirely in the photonic domain.

Truth Chain (normative):
  - μ  : measurement / selection / collapse
  - ∇  : RESERVED for geometric gradient/divergence (MUST NOT be treated as collapse)
  - Δ  : Born weight / intensity (NOT collapse)

New in SRK-12.1:
 - Integration with PhotonMemoryGrid (entanglement persistence)
 - Asynchronous state persistence after each capsule execution
"""

from __future__ import annotations

import asyncio
import math
import random
import time
from typing import Any, Dict, List, Optional

from backend.modules.photon.photon_capsule_validator import validate_photon_capsule
from backend.modules.glyphwave.core.coherence_optimizer import DynamicCoherenceOptimizer
from backend.symatics.operators import OPS  # symbolic operator registry
from backend.modules.photon.memory.photon_memory_grid import PhotonMemoryGrid


# Truth Chain symbols (string form; keep runtime enforcement obvious)
SYM_SUPERPOSE = "⊕"
SYM_ENTANGLE = "↔"
SYM_RESONANCE = "⟲"
SYM_MEASURE = "μ"
SYM_GRAD = "∇"  # RESERVED (must not be used as collapse/selection)


class PhotonAlgebraRuntime:
    """
    ⚛ Photon Algebra Runtime - executes symbolic operations
    directly over photon capsules (entangled wave representations).
    """

    def __init__(self, *, seed: Optional[int] = None):
        self.optimizer = DynamicCoherenceOptimizer()
        self.memory_grid = PhotonMemoryGrid()
        self._rng = random.Random(seed)

    # ────────────────────────────────────────────────────────────────
    @staticmethod
    def _normalize_wave(wave: List[float]) -> List[float]:
        """Normalize wave amplitude to unit norm (coherence placeholder)."""
        magnitude = math.sqrt(sum(x * x for x in wave)) or 1.0
        return [x / magnitude for x in wave]

    @staticmethod
    def _simulate_interference(wave_a: List[float], wave_b: List[float]) -> List[float]:
        """Compute interference pattern between two waves (component-wise add)."""
        return [a + b for a, b in zip(wave_a, wave_b)]

    def _rand_wave(self, n: int = 3) -> List[float]:
        return [self._rng.random() for _ in range(n)]

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

        # IMPORTANT: history is per-execution (avoid cross-capsule trace bleed)
        history: List[Dict[str, Any]] = []

        # Initial wave state (deterministic if runtime seeded)
        result_wave = self._normalize_wave(self._rand_wave(3))

        for glyph in glyphs:
            op = glyph.get("operator", SYM_SUPERPOSE)
            args = glyph.get("args", [])
            meta = glyph.get("meta", {}) or {}

            # Adaptive symbolic operation mapping
            if op == SYM_SUPERPOSE:  # Superposition
                result_wave = self._normalize_wave(
                    [x + self._rng.uniform(-0.1, 0.1) for x in result_wave]
                )

            elif op == SYM_ENTANGLE:  # Entanglement
                result_wave = self._simulate_interference(result_wave, self._rand_wave(3))
                result_wave = self._normalize_wave(result_wave)

            elif op == SYM_RESONANCE:  # Resonance
                factor = math.sin(time.time() % math.pi)
                result_wave = [x * factor for x in result_wave]
                result_wave = self._normalize_wave(result_wave)

            elif op == SYM_GRAD:
                # Truth Chain: ∇ is RESERVED for geometric gradient/divergence only.
                # It MUST NOT be treated as collapse/selection.
                raise ValueError(
                    "Truth Chain violation: '∇' is reserved for gradient; use 'μ' for measurement/selection."
                )

            elif op == SYM_MEASURE:  # Measurement / Selection (Truth Chain)
                # Minimal placeholder: record a measurement scalar derived from wave state.
                # NOTE: governed selection (Born weights Δ + policy modulation + renormalization)
                # is validated by SRK12_GOVERNED_SELECTION scene / runner.
                meta["measurement"] = float(sum(result_wave))

            else:
                # Delegate to operator registry for any additional glyphs
                OPS.apply(op, result_wave, args)

            # Optimize coherence dynamically (side-effect only)
            self.optimizer.optimize_if_needed({"wave": result_wave})

            history.append(
                {
                    "op": op,
                    "args": args,
                    "meta": meta,
                    "result": list(result_wave),
                    "timestamp": time.time(),
                }
            )

        result_state: Dict[str, Any] = {
            "final_wave": list(result_wave),
            "trace": history,
            "timestamp": time.time(),
        }

        # 🔷 SRK-12.1 - Persist result state to Photon Memory Grid asynchronously
        asyncio.create_task(
            self.memory_grid.store_capsule_state(
                capsule.get("name", f"capsule_{int(time.time())}"),
                result_state,
            )
        )

        return result_state