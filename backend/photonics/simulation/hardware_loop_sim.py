"""
Tessaris Hardware Loop Simulation
─────────────────────────────────
Real-time optical feedback bench (NumPy/JAX-ready) modeling dynamic
resonance evolution in the Tessaris Photonic Runtime.

Simulates:
  • Optical propagation delay through τ-frame cycles
  • Phase drift and feedback stabilization (⟲)
  • Gain saturation and coherence damping
  • Adaptive ε-clock synchronization with AION Heartbeat

Used for:
  - Closed-loop resonance experiments
  - RLK training feedback benchmarks
  - Hardware drop-in readiness testing
"""

import numpy as np
import json
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path("backend/logs/photonics/hardware_loop_sim.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
# Core Simulation Parameters
# ──────────────────────────────────────────────
TAU_FRAME = 1e-6        # base optical frame (s)
PHASE_NOISE = 0.002     # random phase noise
GAIN = 0.95             # loop gain
COHERENCE_DECAY = 0.001 # per-frame coherence loss


class HardwareLoopSim:
    """Continuous-time photonic feedback simulation."""

    def __init__(self, n_modes: int = 64):
        self.n_modes = n_modes
        self.phase = np.zeros(n_modes)
        self.coherence = np.ones(n_modes)
        self.time = 0.0
        self.last_output = 0.0
        print(f"[RQC::Sim] Initialized hardware loop with {n_modes} optical modes.")

    # ──────────────────────────────────────────────
    def step(self, input_signal: np.ndarray, phase_bias: float = 0.0):
        """
        Advance the optical loop by one τ-frame.
        Applies phase evolution, gain feedback, and coherence damping.
        """
        noise = np.random.normal(0, PHASE_NOISE, size=self.n_modes)
        self.phase += phase_bias + noise

        # Resonant interference (field summation)
        field = np.sin(input_signal + self.phase)
        intensity = np.mean(field ** 2) * GAIN

        # Coherence damping
        self.coherence *= (1 - COHERENCE_DECAY)
        coherence_level = np.mean(self.coherence)

        # Feedback adjustment
        feedback_signal = intensity * coherence_level
        self.last_output = feedback_signal

        # Time evolution
        self.time += TAU_FRAME

        # Log
        self._log_event({
            "time": self.time,
            "phase_bias": phase_bias,
            "intensity": float(intensity),
            "coherence": float(coherence_level),
            "feedback": float(feedback_signal)
        })

        return feedback_signal, coherence_level

    # ──────────────────────────────────────────────
    def run_cycle(self, signal: np.ndarray, phase_bias: float = 0.0, steps: int = 100):
        """Run a continuous feedback cycle for multiple τ-frames."""
        outputs, coherences = [], []
        for _ in range(steps):
            out, coh = self.step(signal, phase_bias)
            outputs.append(out)
            coherences.append(coh)
            time.sleep(TAU_FRAME * 0.01)  # real-time pacing
        return np.array(outputs), np.array(coherences)

    # ──────────────────────────────────────────────
    def _log_event(self, payload: dict):
        """Persist a single frame’s feedback telemetry."""
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(payload) + "\n")

    # ──────────────────────────────────────────────
    def summary(self):
        """Return current simulation state summary."""
        return {
            "time": self.time,
            "avg_phase": float(np.mean(self.phase)),
            "avg_coherence": float(np.mean(self.coherence)),
            "last_output": self.last_output,
        }


# ──────────────────────────────────────────────
# Test Harness
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("🧠 Tessaris — Hardware Loop Simulation Test")
    sim = HardwareLoopSim(n_modes=128)

    t = np.linspace(0, 2 * np.pi, 128)
    signal = np.sin(4 * t)

    outputs, coherences = sim.run_cycle(signal, phase_bias=np.pi / 12, steps=50)

    print(f"[Test] Final ⟲ loop → avg_intensity={np.mean(outputs):.4f}, "
          f"avg_coherence={np.mean(coherences):.4f}")
    print(json.dumps(sim.summary(), indent=2))