# ================================================================
# 💡 QEquation - Symbolic equation container
# ================================================================
import time
from dataclasses import dataclass, field

@dataclass
class QEquation:
    expr: str
    coherence: float = 1.0
    intensity: float = 1.0
    phase: float = 0.0
    timestamp: float = field(default_factory=lambda: time.time())

    def as_dict(self):
        return {
            "expr": self.expr,
            "ρ": self.coherence,
            "I": self.intensity,
            "φ": self.phase,
            "timestamp": self.timestamp,
        }