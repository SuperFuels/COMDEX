# backend/modules/glyphwave/physics/math_model.py
import math
import random
from typing import List


class WaveState:
    def __init__(self, amplitude: float, phase: float, coherence: float):
        self.amplitude = amplitude  # 0.0 to 1.0
        self.phase = phase          # radians (0 to 2pi)
        self.coherence = coherence  # 0.0 to 1.0

    def __repr__(self):
        return f"WaveState(amp={self.amplitude:.2f}, phase={self.phase:.2f}, coh={self.coherence:.2f})"


class SuperpositionEngine:
    @staticmethod
    def merge(waves: List[WaveState]) -> WaveState:
        if not waves:
            return WaveState(0.0, 0.0, 0.0)

        total_real = sum(w.amplitude * math.cos(w.phase) for w in waves)
        total_imag = sum(w.amplitude * math.sin(w.phase) for w in waves)
        result_amplitude = math.sqrt(total_real ** 2 + total_imag ** 2) / len(waves)
        result_phase = math.atan2(total_imag, total_real)
        avg_coherence = sum(w.coherence for w in waves) / len(waves)

        return WaveState(result_amplitude, result_phase, avg_coherence)


class DecoherenceModel:
    def __init__(self, decay_rate: float = 0.05):
        self.decay_rate = decay_rate

    def decay(self, wave: WaveState, time_passed: float) -> WaveState:
        new_coherence = max(0.0, wave.coherence * math.exp(-self.decay_rate * time_passed))
        return WaveState(wave.amplitude, wave.phase, new_coherence)


class CollapseEquation:
    @staticmethod
    def collapse(candidates: List[WaveState]) -> WaveState:
        if not candidates:
            return WaveState(0.0, 0.0, 0.0)

        weights = [w.coherence * w.amplitude for w in candidates]
        total_weight = sum(weights)

        if total_weight == 0:
            return random.choice(candidates)

        r = random.uniform(0, total_weight)
        cumulative = 0.0
        for wave, weight in zip(candidates, weights):
            cumulative += weight
            if cumulative >= r:
                return wave

        return candidates[-1]  # Fallback


# Optional test rig
if __name__ == "__main__":
    waves = [
        WaveState(1.0, 0.0, 1.0),
        WaveState(0.8, math.pi / 2, 0.9),
        WaveState(0.6, math.pi, 0.5)
    ]

    merged = SuperpositionEngine.merge(waves)
    print("Merged:", merged)

    decayed = DecoherenceModel().decay(merged, time_passed=5.0)
    print("Decayed:", decayed)

    collapsed = CollapseEquation.collapse(waves)
    print("Collapsed:", collapsed)