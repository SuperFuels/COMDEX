"""
SymaticsDispatcher - Symbolic ↔ Photonic Translator (v0.5-B3)
--------------------------------------------------------------
Operator mapping to VirtualWaveEngine kernels via BeamRuntime.

Determinism:
- If TESSARIS_DETERMINISTIC_TIME=1:
  - MUST NOT stamp wall-clock timestamps into capsule metadata.
  - MUST NOT draw ambient randomness for capsule metadata.
"""

from __future__ import annotations

import os
import hashlib
from typing import Any, Dict

from backend.modules.symatics_lightwave.wave_capsule import WaveCapsule
from backend.modules.symatics_lightwave.beam_runtime import BeamRuntime

_DETERMINISTIC_TIME = os.getenv("TESSARIS_DETERMINISTIC_TIME", "") == "1"


def _stable_unit_float(*parts: object) -> float:
    blob = "|".join("" if p is None else str(p) for p in parts).encode("utf-8")
    d = hashlib.sha256(blob).digest()
    n = int.from_bytes(d[:8], "big", signed=False)
    return n / 2**64


class SymaticsDispatcher:
    def __init__(self):
        self.runtime = BeamRuntime()
        self.operator_map = {
            "⊕": self._op_superposition,
            "μ": self._op_measurement,
            "↔": self._op_entanglement,
            "⟲": self._op_resonance,
            "π": self._op_projection,
            # NOTE: holo.run is handled as a special opcode (see dispatch)
        }

    def dispatch_capsule(self, capsule: WaveCapsule) -> Dict[str, Any]:
        """
        Execute an already-built WaveCapsule through the operator handlers.

        This is the B03 path: SLEAdapter -> WaveCapsule -> SymaticsDispatcher -> BeamRuntime.
        """
        opcode = getattr(capsule, "opcode", None)
        handler = self.operator_map.get(opcode)

        if not handler:
            # Avoid print spam; return a stable envelope.
            return {"opcode": opcode, "status": "unknown"}

        return handler(capsule)

    def dispatch(self, instruction: dict) -> Dict[str, Any]:
        """
        Back-compat: accepts symbolic instruction dict, builds capsule internally.
        Prefer dispatch_capsule() for deterministic integration paths.
        """
        opcode = instruction.get("opcode")

        if opcode == "holo.run":
            return self._op_holo_run(instruction)

        capsule = WaveCapsule.from_symbolic_instruction(instruction)

        if _DETERMINISTIC_TIME:
            # Deterministic metadata (no wall clock / no ambient random)
            seed = capsule.metadata.get("seed")
            scenario_id = capsule.metadata.get("scenario_id")
            channel = capsule.metadata.get("channel")
            tick = capsule.metadata.get("tick")
            t = capsule.metadata.get("t")
            capsule.metadata.update(
                {
                    "opcode": opcode,
                    "timestamp": "0000-00-00T00:00:00Z",
                    "entropy_seed": _stable_unit_float("entropy", seed, scenario_id, channel, tick, t, opcode),
                }
            )
        else:
            import time
            import random
            capsule.metadata.update(
                {
                    "opcode": opcode,
                    "timestamp": time.time(),
                    "entropy_seed": random.random(),
                }
            )

        return self.dispatch_capsule(capsule)

    #────────────────────────────────────────────
    # Operator Implementations
    #────────────────────────────────────────────
    def _op_superposition(self, capsule: WaveCapsule) -> Dict[str, Any]:
        """⊕ Combine amplitudes and phases of all active waves."""
        result = self.runtime.execute_capsule(capsule, mode="superposition")
        capsule.wave_state.amplitude *= 1.05
        capsule.wave_state.phase += 0.1
        return result

    def _op_measurement(self, capsule: WaveCapsule) -> Dict[str, Any]:
        """μ Collapse wave and log metrics."""
        result = self.runtime.execute_capsule(capsule, mode="measurement")
        capsule.wave_state.coherence *= 0.97
        return result

    def _op_entanglement(self, capsule: WaveCapsule) -> Dict[str, Any]:
        """↔ Entangle current wave with others in engine."""
        result = self.runtime.execute_capsule(capsule, mode="entanglement")
        capsule.wave_state.coherence = (capsule.wave_state.coherence + 0.9) / 2
        return result

    def _op_resonance(self, capsule: WaveCapsule) -> Dict[str, Any]:
        """⟲ Reinforce amplitude under SQI feedback."""
        result = self.runtime.execute_capsule(capsule, mode="resonance")
        capsule.wave_state.amplitude *= 1.1
        return result

    def _op_projection(self, capsule: WaveCapsule) -> Dict[str, Any]:
        """π Project wave collapse to holographic container."""
        result = self.runtime.execute_capsule(capsule, mode="projection")
        capsule.wave_state.coherence *= 0.95
        return result

    def _op_holo_run(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        # Intentionally disabled in this benchmark path (kept for legacy compatibility).
        holo = instruction.get("holo")
        if not holo:
            return {
                "status": "error",
                "engine": "symatics_lightwave",
                "opcode": "holo.run",
                "error": "missing_holo",
            }
        return {
            "status": "error",
            "engine": "symatics_lightwave",
            "opcode": "holo.run",
            "error": "holo.run disabled in GX1 benchmark path",
        }
