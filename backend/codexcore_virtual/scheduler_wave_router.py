"""
Tessaris • Codex → Symatics Lightwave Router
---------------------------------------------
Intercepts Codex scheduler dispatch calls and routes {kind:"wave"}
instructions to the Symatics Lightwave Engine (SLE).
"""

import logging
import time
from typing import Dict, Any

from backend.codexcore_virtual.virtual_wave_engine import VirtualWaveEngine
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent

logger = logging.getLogger(__name__)


class SchedulerWaveRouter:
    """Routes Codex symbolic instructions into the Lightwave Engine."""

    def __init__(self, container_id="sle.router"):
        self.container_id = container_id
        self.engine = VirtualWaveEngine(container_id)
        logger.info(f"[SchedulerWaveRouter] Initialized for container {container_id}")

    def route(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """
        If instruction.kind == 'wave', execute via Lightwave Engine.
        Otherwise, return {'status':'skipped'} so Codex handles it normally.
        """
        kind = instruction.get("kind", "")
        if kind != "wave":
            return {"status": "skipped", "reason": f"non-wave kind: {kind}"}

        opcode = instruction.get("opcode", "?")
        args = instruction.get("args", [])

        # --- Create a new WaveState dynamically
        from backend.modules.glyphwave.core.wave_state import WaveState
        wave = WaveState()
        wave.metadata["opcode"] = opcode
        wave.metadata["args"] = args
        wave.metadata["wave_id"] = f"wave_{opcode}_{int(time.time()*1000)}"
        wave.amplitude = 1.0
        wave.phase = 0.0
        wave.coherence = 1.0

        # Attach to engine before collapse
        self.engine.attach_wave(wave)

        # Load symbolic op for tracking
        self.engine.load_wave_program([(opcode, args)])

        # Emit beam event for visibility
        beam_event_bus.publish(
            BeamEvent(
                "dispatch_wave",
                source="codex.scheduler",
                target=self.container_id,
                drift=0.0,
                qscore=1.0,
                metadata={
                    "opcode": opcode,
                    "args": args,
                    "wave_id": wave.metadata["wave_id"],
                },
            )
        )

        # Perform symbolic→photonic collapse cycle
        result = self.engine.entangled_wave.collapse_all()

        return {
            "status": "executed",
            "opcode": opcode,
            "args": args,
            "container": self.container_id,
            "collapse_metrics": result.get("collapse_metrics", {}),
            "wave_id": wave.metadata["wave_id"],
            "timestamp": time.time(),
        }