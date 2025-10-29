# 📁 backend/modules/photon_memory/photon_memory_entry.py
from dataclasses import dataclass, field
from typing import Dict, Any
import time, uuid

@dataclass
class PhotonMemoryEntry:
    wave_id: str
    amplitude: float
    phase: float
    coherence: float
    entropy: float
    operator: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "wave_id": self.wave_id,
            "amplitude": self.amplitude,
            "phase": self.phase,
            "coherence": self.coherence,
            "entropy": self.entropy,
            "operator": self.operator,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }