"""
Tessaris Photonic Hardware Bridge — Driver API Stubs
────────────────────────────────────────────────────
Provides unified interfaces for simulated or physical photonic components:
  • MZMDriver  → Mach–Zehnder Modulator (phase modulation)
  • DACDriver  → Digital-to-Analog Conversion for optical signal control
  • PDDriver   → Photodiode readout (intensity / interference)
Supports both simulation and eventual lab hardware integration.

Runtime Modes:
  mode = {"sim", "hardware"}   # toggled in config or CLI
"""

import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import json

LOG_PATH = Path("backend/logs/photonics/driver_activity.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────
# Base Hardware Interface
# ──────────────────────────────────────────────────────────────

class PhotonicDevice:
    def __init__(self, name: str, mode: str = "sim"):
        self.name = name
        self.mode = mode
        self.last_output = None

    def log(self, data: dict):
        """Append structured log to JSONL."""
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        data["device"] = self.name
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(data) + "\n")

    def __repr__(self):
        return f"<{self.__class__.__name__}:{self.name}, mode={self.mode}>"


# ──────────────────────────────────────────────────────────────
# Device Drivers
# ──────────────────────────────────────────────────────────────

class MZMDriver(PhotonicDevice):
    """Mach–Zehnder Modulator driver stub."""

    def modulate(self, signal: np.ndarray, phase_bias: float = 0.0) -> np.ndarray:
        """Applies phase modulation to input waveform."""
        modulated = np.cos(signal + phase_bias)
        self.last_output = modulated
        self.log({"action": "modulate", "phase_bias": phase_bias})
        return modulated


class DACDriver(PhotonicDevice):
    """Digital-to-Analog Converter driver stub."""

    def output_waveform(self, data: np.ndarray, gain: float = 1.0):
        """Generate analog waveform from digital data."""
        waveform = data * gain
        self.last_output = waveform
        self.log({"action": "dac_output", "gain": gain})
        return waveform


class PDDriver(PhotonicDevice):
    """Photodiode detector stub."""

    def detect(self, optical_field: np.ndarray) -> float:
        """Measure intensity (power = |E|²)."""
        intensity = float(np.mean(optical_field**2))
        self.last_output = intensity
        self.log({"action": "detect", "intensity": intensity})
        return intensity


# ──────────────────────────────────────────────────────────────
# Composite Optical Loop (for simulation mode)
# ──────────────────────────────────────────────────────────────

class OpticalFeedbackLoop:
    """Simulated optical feedback path (DAC→MZM→PD)."""

    def __init__(self):
        self.dac = DACDriver("DAC-1")
        self.mzm = MZMDriver("MZM-1")
        self.pd = PDDriver("PD-1")

    def run_cycle(self, signal: np.ndarray, phase_bias: float = 0.0) -> float:
        """Propagate a signal through DAC→MZM→PD."""
        analog = self.dac.output_waveform(signal)
        modulated = self.mzm.modulate(analog, phase_bias=phase_bias)
        intensity = self.pd.detect(modulated)
        return intensity


# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🧩 Tessaris Photonic Driver API Test Run")
    t = np.linspace(0, 2 * np.pi, 128)
    signal = np.sin(3 * t)
    loop = OpticalFeedbackLoop()
    I = loop.run_cycle(signal, phase_bias=np.pi / 4)
    print(f"[Test] Detected intensity = {I:.6f}")