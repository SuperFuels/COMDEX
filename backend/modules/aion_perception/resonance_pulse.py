# backend/modules/aion_perception/resonance_pulse.py
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ResonancePulse:
    """Encapsulates SQI resonance parameters for feedback injection."""
    epsilon_bias: float = 0.0   # ✅ Default value avoids missing argument crash
    damping: float = 0.9
    gain: float = 0.3
    coherence: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return numeric dictionary form for SQIField.apply()."""
        return {
            "epsilon_bias": float(self.epsilon_bias),
            "damping": float(self.damping),
            "gain": float(self.gain),
            "coherence": float(self.coherence),
            **(self.meta or {})
        }