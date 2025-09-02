# backend/modules/glyphwave/models/wave_glyph.py
from dataclasses import dataclass, field
from typing import List
import time

@dataclass
class WaveGlyph:
    phase: float                      # radians
    amplitude: float                 # unitless
    coherence: float                 # 0.0 to 1.0
    origin_trace: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)