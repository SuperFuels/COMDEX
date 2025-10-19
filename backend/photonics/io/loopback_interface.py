"""
Tessaris Photonic I/O Loopback Interface
────────────────────────────────────────
Abstract layer enabling seamless transition between simulated optical
feedback and real hardware integration (MZM/DAC/PD modules).

Implements:
  • LoopbackInterface   – virtual optical bus bridge
  • HardwareAdapter     – hardware proxy mapping (future)
  • ResonantIOLink      – unified entrypoint for AION/QQC signal exchange

Runtime Modes:
  mode = {"sim", "hardware"}
"""

import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import json

from backend.photonics.hardware.driver_api import OpticalFeedbackLoop

LOG_PATH = Path("backend/logs/photonics/io_activity.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────
# Core I/O Bridge
# ──────────────────────────────────────────────────────────────

class LoopbackInterface:
    """
    Provides a consistent interface for optical signal injection
    and feedback measurement. Works identically in both modes.
    """

    def __init__(self, mode: str = "sim"):
        self.mode = mode
        self.feedback_loop = OpticalFeedbackLoop()
        self.last_intensity = 0.0
        self.log_event("loopback_init", {"mode": mode})

    def transmit(self, data: np.ndarray, phase_bias: float = 0.0):
        """
        Inject a waveform into the optical loop and read back intensity.
        """
        if self.mode == "sim":
            self.last_intensity = self.feedback_loop.run_cycle(data, phase_bias)
        else:
            # In hardware mode, call DAC→MZM→PD through device drivers
            # (future physical API)
            self.last_intensity = self.feedback_loop.run_cycle(data, phase_bias)

        self.log_event("loopback_transmit", {"phase_bias": phase_bias, "intensity": self.last_intensity})
        return self.last_intensity

    def log_event(self, event_type: str, payload: dict):
        """Write event metadata into the I/O log."""
        payload["event"] = event_type
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(payload) + "\n")

    def __repr__(self):
        return f"<LoopbackInterface mode={self.mode}, I={self.last_intensity:.4f}>"


# ──────────────────────────────────────────────────────────────
# Hardware Adapter (Placeholder for Real Instrumentation)
# ──────────────────────────────────────────────────────────────

class HardwareAdapter:
    """
    Placeholder for real instrument control layer.
    Would handle hardware discovery, calibration,
    and analog signal routing.
    """

    def __init__(self):
        self.devices = {"MZM": None, "DAC": None, "PD": None}

    def detect_hardware(self):
        """Simulated discovery of hardware components."""
        self.devices = {k: f"{k}-module" for k in self.devices}
        return self.devices

    def calibrate(self):
        """Perform calibration sequence (simulated)."""
        print("[HardwareAdapter] Calibration complete — nominal alignment achieved.")


# ──────────────────────────────────────────────────────────────
# Resonant I/O Link (AION ↔ QQC ↔ Photon)
# ──────────────────────────────────────────────────────────────

class ResonantIOLink:
    """
    Unified entrypoint for AION/QQC data exchange into the photonic layer.
    Handles waveform encoding, loopback propagation, and coherence readout.
    """

    def __init__(self, mode: str = "sim"):
        self.loop = LoopbackInterface(mode=mode)

    def propagate(self, symbol_wave: np.ndarray, phase_bias: float = 0.0):
        """
        Send a symbolic waveform through the optical domain.
        Returns measured intensity and resonance signature.
        """
        intensity = self.loop.transmit(symbol_wave, phase_bias)
        resonance = {
            "Φ_measured": intensity,
            "ΔΦ_est": float(np.sin(phase_bias) * intensity),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.loop.log_event("resonant_propagation", resonance)
        return resonance


# ──────────────────────────────────────────────────────────────
# Self-Test Entry
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔁 Tessaris Photonic Loopback Interface — Test Run")
    t = np.linspace(0, 2 * np.pi, 128)
    signal = np.sin(2 * t)
    io = ResonantIOLink(mode="sim")
    res = io.propagate(signal, phase_bias=np.pi / 6)
    print(f"[Test] Resonant propagation → Φ_measured={res['Φ_measured']:.4f}, ΔΦ_est={res['ΔΦ_est']:.4f}")