# backend/modules/glyphwave/core/carrier_memory.py
"""
CarrierMemory: GlyphWave signal buffer and routing interface.
Handles active propagation, wave storage, and `.gip` serialization.
"""

from typing import List, Optional, Dict
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.core.entangled_wave import EntangledWave
import time
import uuid

class CarrierMemory:
    def __init__(self):
        self.live_buffer: List[WaveState] = []
        self.entangled_buffer: List[EntangledWave] = []
        self.timestamped_packets: Dict[str, float] = {}  # wave_id → timestamp

    def send_wave(self, wave: WaveState) -> str:
        """Emit a WaveState into carrier memory with trace timestamp."""
        wave_id = str(uuid.uuid4())
        wave.metadata["wave_id"] = wave_id
        wave.timestamp = time.time()
        self.live_buffer.append(wave)
        self.timestamped_packets[wave_id] = wave.timestamp
        return wave_id

    def send_entangled(self, entangled: EntangledWave) -> str:
        """Store an entangled wave structure."""
        entangled_id = str(uuid.uuid4())
        entangled.metadata["entangled_id"] = entangled_id
        entangled.timestamp = time.time()
        self.entangled_buffer.append(entangled)
        self.timestamped_packets[entangled_id] = entangled.timestamp
        return entangled_id

    def receive_latest(self, count: int = 1) -> List[WaveState]:
        """Retrieve the most recent wave signals."""
        return self.live_buffer[-count:]

    def receive_all(self) -> List[WaveState]:
        """Return all wave packets in buffer."""
        return list(self.live_buffer)

    def clear(self):
        """Flush all stored wave data."""
        self.live_buffer.clear()
        self.entangled_buffer.clear()
        self.timestamped_packets.clear()

    def as_gip_packets(self) -> List[Dict]:
        """Export buffered waves as serialized `.gip` packet format."""
        packets = []
        for wave in self.live_buffer:
            packets.append({
                "wave_id": wave.metadata.get("wave_id"),
                "phase": wave.phase,
                "amplitude": wave.amplitude,
                "coherence": wave.coherence,
                "origin_trace": wave.origin_trace,
                "timestamp": wave.timestamp,
                "carrier": "glyphwave"
            })
        return packets

    def get_wave_by_id(self, wave_id: str) -> Optional[WaveState]:
        for wave in self.live_buffer:
            if wave.metadata.get("wave_id") == wave_id:
                return wave
        return None

    def debug_summary(self) -> Dict:
        return {
            "wave_count": len(self.live_buffer),
            "entangled_count": len(self.entangled_buffer),
            "latest_wave": self.live_buffer[-1].metadata if self.live_buffer else None
        }
