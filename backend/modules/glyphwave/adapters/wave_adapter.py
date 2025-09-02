# backend/modules/glyphwave/adapters/wave_adapter.py
"""
WaveAdapter: Translates symbolic glyphs into WaveState signals.
Supports container glyphs, Codex instructions, and runtime-triggered emissions.
"""

from typing import Dict, Any
import time
import math

# ✅ Inline updated WaveState class to accept phase, amplitude, etc.
class WaveState:
    def __init__(
        self,
        phase: float,
        amplitude: float,
        coherence: float,
        origin_trace: list,
        metadata: dict,
        timestamp: float
    ):
        self.phase = phase
        self.amplitude = amplitude
        self.coherence = coherence
        self.origin_trace = origin_trace
        self.metadata = metadata
        self.timestamp = timestamp

    def __repr__(self):
        return (
            f"WaveState(phase={self.phase:.2f}, amplitude={self.amplitude}, "
            f"coherence={self.coherence}, origin={self.origin_trace}, "
            f"timestamp={self.timestamp})"
        )

class WaveAdapter:
    def __init__(self):
        self.default_amplitude = 1.0
        self.default_coherence = 1.0

    def glyph_to_wave(self, glyph: Dict[str, Any]) -> WaveState:
        """
        Convert a symbolic glyph (dict form) into a WaveState.
        Handles phase/amplitude/coherence extraction or synthesis.
        """
        label = glyph.get("label", "unknown")
        metadata = glyph.get("metadata", {})

        # Phase can be derived from hash or symbolic value
        phase = self.estimate_phase(label, metadata)
        amplitude = self.estimate_amplitude(label, metadata)
        coherence = metadata.get("coherence", self.default_coherence)

        origin_trace = [label]
        timestamp = time.time()

        return WaveState(
            phase=phase,
            amplitude=amplitude,
            coherence=coherence,
            origin_trace=origin_trace,
            metadata={"source": "glyph", "label": label, **metadata},
            timestamp=timestamp
        )

    def estimate_phase(self, label: str, metadata: Dict[str, Any]) -> float:
        """
        Estimate phase using a deterministic symbolic hash.
        Ensures similar symbols are phase-aligned.
        """
        h = hash(label + str(metadata)) % 360
        return math.radians(h)

    def estimate_amplitude(self, label: str, metadata: Dict[str, Any]) -> float:
        """
        Estimate amplitude based on symbol type or metadata energy.
        """
        if "amplitude" in metadata:
            return float(metadata["amplitude"])
        if label.lower() in {"truth", "axiom", "core"}:
            return 2.0
        return self.default_amplitude