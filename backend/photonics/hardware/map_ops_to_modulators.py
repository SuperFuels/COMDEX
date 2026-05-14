"""
Tessaris Photonic Operator->Modulator Mapping
────────────────────────────────────────────
Maps Symatics operators (⊕ μ ⟲ ↔) to hardware control signals
for Mach-Zehnder modulators (MZM), DAC voltage patterns, and
photonic phase feedback circuits.

Each operator is represented as:
  * Analog voltage waveform (DAC)
  * Phase modulation depth (MZM bias offset)
  * Feedback factor (⟲ resonance amplitude)
  * Coupling index (↔ entanglement matrix coefficient)

This layer serves as the live translation between symbolic algebra
and physical photonic actuation - the closure of Track B3.
"""

import json
from datetime import datetime, timezone
import numpy as np
from pathlib import Path

LOG_PATH = Path("backend/logs/photonics/operator_mapping.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# Operator -> Hardware Pattern Definitions
# ──────────────────────────────────────────────

OPERATOR_MAP = {
    "⊕": {
        "description": "superpose - additive interference",
        "mzm_phase_offset": 0.25 * np.pi,
        "dac_waveform": lambda t: np.sin(2 * np.pi * 10e6 * t),
        "feedback_gain": 0.0,
        "coupling_index": 0.0,
    },
    "μ": {
        "description": "measure - collapse/observe",
        "mzm_phase_offset": 0.0,
        "dac_waveform": lambda t: np.sign(np.sin(2 * np.pi * 5e6 * t)),
        "feedback_gain": 0.0,
        "coupling_index": 0.0,
    },
    "⟲": {
        "description": "resonate - closed-loop amplification",
        "mzm_phase_offset": 0.5 * np.pi,
        "dac_waveform": lambda t: np.sin(2 * np.pi * 2e6 * t) ** 3,
        "feedback_gain": 0.8,
        "coupling_index": 0.0,
    },
    "↔": {
        "description": "entangle - mode coupling",
        "mzm_phase_offset": 0.75 * np.pi,
        "dac_waveform": lambda t: np.sin(2 * np.pi * 1e6 * t + np.pi / 4),
        "feedback_gain": 0.2,
        "coupling_index": 1.0,
    },
}


# ──────────────────────────────────────────────
# Pattern Generator / Preview
# ──────────────────────────────────────────────

def generate_waveform(symbol: str, duration=1e-6, sample_rate=1e9):
    """Generate a DAC waveform for a given operator symbol."""
    if symbol not in OPERATOR_MAP:
        raise ValueError(f"Unknown operator symbol: {symbol}")
    t = np.linspace(0, duration, int(sample_rate * duration))
    wf = OPERATOR_MAP[symbol]["dac_waveform"](t)
    return t, wf


def simulate_modulator_drive(symbol: str):
    """Simulate a single operator-to-hardware mapping run."""
    t, wf = generate_waveform(symbol)
    data = {
        "operator": symbol,
        "mean_voltage": float(np.mean(wf)),
        "std_voltage": float(np.std(wf)),
        "mzm_phase_offset": float(OPERATOR_MAP[symbol]["mzm_phase_offset"]),
        "feedback_gain": OPERATOR_MAP[symbol]["feedback_gain"],
        "coupling_index": OPERATOR_MAP[symbol]["coupling_index"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(data) + "\n")
    return data


# ──────────────────────────────────────────────
# Hardware Bridge Integration Stub
# ──────────────────────────────────────────────

def send_to_hardware(symbol: str, driver="MZM/DAC"):
    """
    Stub for real hardware bridge. In lab mode, this would
    transmit waveform buffers and phase offsets to the MZM driver.
    """
    sim = simulate_modulator_drive(symbol)
    print(f"[PhotonicBridge::{driver}] {symbol} -> "
          f"⟲={sim['feedback_gain']:.2f}, Φ_offset={sim['mzm_phase_offset']:.2f} rad, "
          f"meanV={sim['mean_voltage']:.3f}")
    return sim


# ──────────────────────────────────────────────
# CLI Entry Point for test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("📡 Tessaris - Operator->Modulator Mapping Test Run")
    results = {}
    for sym in OPERATOR_MAP:
        results[sym] = send_to_hardware(sym)
    print(json.dumps(results, indent=2))