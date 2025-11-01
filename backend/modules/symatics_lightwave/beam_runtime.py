"""
BeamRuntime - Photonic Execution Core (v0.5-B3)
-----------------------------------------------
Executes WaveCapsules with mode-specific kernel behavior.
"""

import time
from backend.codexcore_virtual.virtual_wave_engine import VirtualWaveEngine
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent


class BeamRuntime:
    def __init__(self):
        self.engine = VirtualWaveEngine(container_id="symatics.sle.runtime")

    def execute_capsule(self, capsule, mode="generic"):
        self.engine.attach_wave(capsule.wave_state)
        start = time.perf_counter()

        # 🛰 Dispatch Event
        beam_event_bus.publish(
            BeamEvent(
                f"{mode}_dispatch",
                source="SymaticsDispatcher",
                target="VirtualWaveEngine",
                qscore=capsule.wave_state.coherence,
                drift=getattr(capsule.wave_state, "drift", 0.0),
                metadata=capsule.metadata,
            )
        )

        # Simulate photonic kernel
        time.sleep(0.01)
        capsule.wave_state.coherence *= 0.99
        collapse_time_ms = round((time.perf_counter() - start) * 1000, 3)

        # ⚡ Collapse Event
        beam_event_bus.publish(
            BeamEvent(
                f"{mode}_collapse",
                source="VirtualWaveEngine",
                target="SymaticsDispatcher",
                qscore=capsule.wave_state.coherence,
                drift=getattr(capsule.wave_state, "drift", 0.0),
                metadata={"collapse_time_ms": collapse_time_ms, "mode": mode},
            )
        )

        return {
            "opcode": capsule.opcode,
            "mode": mode,
            "coherence": capsule.wave_state.coherence,
            "collapse_time_ms": collapse_time_ms,
            "status": "executed",
        }