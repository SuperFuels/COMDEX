"""
WaveInjector: Hooks into runtime & Codex to emit WaveStates into CarrierMemory.
"""

from typing import Dict, Any
import time

from backend.modules.glyphwave.adapters.wave_adapter import WaveAdapter
from backend.modules.glyphwave.core.carrier_memory import CarrierMemory

class WaveInjector:
    def __init__(self, carrier_memory: CarrierMemory):
        self.adapter = WaveAdapter()
        self.carrier = carrier_memory

    def emit_from_glyph(self, glyph: Dict[str, Any], source: str = "unknown") -> "WaveState":
        """
        Convert glyph into wave and inject into carrier memory.
        """
        from backend.modules.glyphwave.core.wave_state import WaveState  # Lazy import to prevent circular import
        wave = self.adapter.glyph_to_wave(glyph)
        wave.metadata["emitted_by"] = source
        self.carrier.send_wave(wave)
        return wave

    def emit_teleport_wave(self, source: str = "warp_edge") -> "WaveState":
        """
        Emit a symbolic wave glyph for teleportation events at warp boundary.
        """
        from backend.modules.glyphwave.core.wave_state import WaveState  # Lazy import again
        teleport_glyph = {
            "type": "event",
            "name": "warp_edge_teleport",
            "phase_seed": time.time(),  # used by adapter
            "amplitude": 1.0,
            "coherence": 0.99
        }
        return self.emit_from_glyph(teleport_glyph, source=source)