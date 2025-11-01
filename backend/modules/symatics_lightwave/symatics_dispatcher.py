"""
SymaticsDispatcher - Symbolic ↔ Photonic Translator (v0.5-B3)
--------------------------------------------------------------
Now includes operator mapping to VirtualWaveEngine kernels.
"""

import random, time
from backend.modules.symatics_lightwave.wave_capsule import WaveCapsule
from backend.modules.symatics_lightwave.beam_runtime import BeamRuntime


class SymaticsDispatcher:
    def __init__(self):
        self.runtime = BeamRuntime()
        self.operator_map = {
            "⊕": self._op_superposition,
            "μ": self._op_measurement,
            "↔": self._op_entanglement,
            "⟲": self._op_resonance,
            "π": self._op_projection,
        }

    def dispatch(self, instruction: dict):
        opcode = instruction.get("opcode")
        handler = self.operator_map.get(opcode)

        if not handler:
            print(f"[SymaticsDispatcher] ⚠️ Unknown opcode: {opcode}")
            return {"opcode": opcode, "status": "unknown"}

        capsule = WaveCapsule.from_symbolic_instruction(instruction)
        capsule.metadata.update({
            "opcode": opcode,
            "timestamp": time.time(),
            "entropy_seed": random.random(),
        })
        return handler(capsule)

    #────────────────────────────────────────────
    # Operator Implementations
    #────────────────────────────────────────────
    def _op_superposition(self, capsule):
        """⊕ Combine amplitudes and phases of all active waves."""
        result = self.runtime.execute_capsule(capsule, mode="superposition")
        capsule.wave_state.amplitude *= 1.05
        capsule.wave_state.phase += 0.1
        return result

    def _op_measurement(self, capsule):
        """μ Collapse wave and log metrics."""
        result = self.runtime.execute_capsule(capsule, mode="measurement")
        capsule.wave_state.coherence *= 0.97
        return result

    def _op_entanglement(self, capsule):
        """↔ Entangle current wave with others in engine."""
        result = self.runtime.execute_capsule(capsule, mode="entanglement")
        capsule.wave_state.coherence = (capsule.wave_state.coherence + 0.9) / 2
        return result

    def _op_resonance(self, capsule):
        """⟲ Reinforce amplitude under SQI feedback."""
        result = self.runtime.execute_capsule(capsule, mode="resonance")
        capsule.wave_state.amplitude *= 1.1
        return result

    def _op_projection(self, capsule):
        """π Project wave collapse to holographic container."""
        result = self.runtime.execute_capsule(capsule, mode="projection")
        capsule.wave_state.coherence *= 0.95
        return result

"""
Photon-Symatics Bridge
─────────────────────────────────────────────
Connects Photon executor operators (⊕, ↔, μ, ⟲, π)
to the Symatics runtime (Lightwave or Symbolic).
"""

from backend.modules.symatics_lightwave.symatics_dispatcher import SymaticsDispatcher

_dispatcher = SymaticsDispatcher()


def run_symatics_wavecapsule(spec):
    """
    Entry point called by photon_executor plugin handlers.

    Args:
        spec (dict): {"opcode": "⊕", "args": ["ψ1", "ψ2"], "engine": "symbolic"|"lightwave"}
    Returns:
        dict: Result envelope {"status", "engine", "opcode", ...}
    """

    try:
        # ─────────────────────────────────────────────
        # 🔀 Runtime selector: symbolic vs. lightwave
        # ─────────────────────────────────────────────
        if spec.get("engine") == "symbolic":
            # Use the original algebraic Symatics core
            from backend.symatics.symatics_dispatcher import evaluate_symatics_expr
            return evaluate_symatics_expr(spec)

        # Default to Lightwave (photonic) dispatcher
        result = _dispatcher.dispatch(spec)

        if isinstance(result, dict):
            result.setdefault("engine", "symatics_lightwave")
            result.setdefault("opcode", spec.get("opcode"))
        return result

    except Exception as e:
        return {
            "status": "error",
            "engine": spec.get("engine", "symatics_lightwave"),
            "error": str(e),
        }