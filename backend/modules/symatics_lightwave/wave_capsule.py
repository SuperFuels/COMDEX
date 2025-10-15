"""
Tessaris • Symatics Lightwave Capsule (WaveCapsule API)
-------------------------------------------------------
Encapsulates symbolic→photonic wave execution
for ⊕ μ ↔ ⟲ π operators via SymaticsDispatcher.

Provides both:
- WaveCapsule (encapsulation class)
- run_symatics_wavecapsule() (execution entrypoint)
"""

import time
import random
import logging
from typing import Dict, Any

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent

logger = logging.getLogger(__name__)


# ─── WaveCapsule Core ─────────────────────────────────────────────
class WaveCapsule:
    """
    Encapsulates symbolic operation data + photonic carrier (WaveState).
    """

    def __init__(self, opcode, args=None, metadata=None, container_id: str = "wavecapsule.default"):
        self.opcode = opcode
        self.args = args or []
        self.metadata = metadata or {}
        self.container_id = container_id
        self.timestamp = time.time()

        # build wave state with randomized properties
        self.wave_state = WaveState()
        self.wave_state.amplitude = 1.0
        self.wave_state.phase = random.uniform(0.0, 3.14)
        self.wave_state.coherence = random.uniform(0.8, 1.0)
        self.wave_state.metadata.update({
            "capsule_id": f"capsule_{int(random.random()*1e6)}",
            "opcode": opcode,
            "args": self.args,
            "container_id": container_id,
            "timestamp": self.timestamp
        })

    @classmethod
    def from_symbolic_instruction(cls, instr):
        opcode = instr.get("opcode", "NOP")
        args = instr.get("args", [])
        meta = {"origin": "symatics_dispatcher"}
        return cls(opcode, args, meta)

    def run(self) -> Dict[str, Any]:
        """Execute the symbolic opcode via SymaticsDispatcher."""
        from backend.modules.symatics_lightwave import SymaticsDispatcher
        dispatcher = SymaticsDispatcher()

        beam_event_bus.publish(
            BeamEvent(
                event_type="wavecapsule_start",
                source=self.container_id,
                target="symatics_lightwave",
                drift=0.0,
                qscore=1.0,
                metadata=self.wave_state.metadata
            )
        )

        result = dispatcher.dispatch({"opcode": self.opcode, "args": self.args})
        result.update({
            "wave_id": self.wave_state.metadata.get("wave_id", "anon"),
            "container_id": self.container_id,
            "timestamp": self.timestamp
        })

        beam_event_bus.publish(
            BeamEvent(
                event_type="wavecapsule_complete",
                source=self.container_id,
                target="symatics_lightwave",
                drift=0.0,
                qscore=result.get("coherence", 1.0),
                metadata=result
            )
        )

        logger.info(f"[WaveCapsule] {self.opcode} executed → coherence={result.get('coherence'):.3f}")
        return result

    def __repr__(self):
        return f"<WaveCapsule opcode={self.opcode} phase={self.wave_state.phase:.2f} coh={self.wave_state.coherence:.2f}>"


# ─── External API ─────────────────────────────────────────────
def run_symatics_wavecapsule(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single symbolic-photonic op via WaveCapsule API."""
    opcode = spec.get("opcode")
    args = spec.get("args", [])
    container_id = spec.get("container_id", "wavecapsule.default")

    capsule = WaveCapsule(opcode, args, {}, container_id)
    return capsule.run()