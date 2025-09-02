# backend/modules/glyphwave/core/wave_glyph.py

from typing import List, Dict, Any
import time
import uuid

class WaveGlyph:
    def __init__(
        self,
        label: str,
        phase: float,
        amplitude: float,
        coherence: float,
        origin_trace: List[str] = None,
        metadata: Dict[str, Any] = None,
        timestamp: float = None,
        uid: str = None,
    ):
        self.uid = uid or str(uuid.uuid4())
        self.label = label
        self.phase = phase              # radians (0 to 2π)
        self.amplitude = amplitude      # normalized: 0.0 to 1.0
        self.coherence = coherence      # 0.0 (incoherent) to 1.0 (perfect)
        self.origin_trace = origin_trace or []  # lineage of glyphs
        self.metadata = metadata or {}  # CodexLang links, goals, SQI states, etc.
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "label": self.label,
            "phase": self.phase,
            "amplitude": self.amplitude,
            "coherence": self.coherence,
            "origin_trace": self.origin_trace,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WaveGlyph":
        return cls(
            uid=data.get("uid"),
            label=data["label"],
            phase=data["phase"],
            amplitude=data["amplitude"],
            coherence=data["coherence"],
            origin_trace=data.get("origin_trace", []),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp"),
        )