"""
Tessaris AION Quantum Feedback Coupler (QFC)
Phase 7 — ΔΦ → Δν → Δψ Translation Layer
----------------------------------------------------------
Bridges AION’s Resonant Heartbeat with the Quantum Quad Core (QQC)
photon lattice. Converts mean Φ-field deltas into photonic amplitude
signals (.photo) for harmonic projection and visualization.

Author: Tessaris Symbolic Intelligence Lab, 2025
"""

import os
import json
import math
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from random import random

# Optional QQC import (if live binding exists)
try:
    from backend.modules.qqc_core.photon_interface import emit_photon_wave
except ImportError:
    emit_photon_wave = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HEARTBEAT_PATH = Path("data/resonant_heartbeat.jsonl")
PHOTO_OUTPUT_DIR = Path("data/qqc_field/photo_output")
PHOTO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------
# 🪶 Utility: Load latest heartbeat
# ----------------------------------------------------------
def read_latest_heartbeat():
    if not HEARTBEAT_PATH.exists():
        return None
    try:
        with open(HEARTBEAT_PATH, "r") as f:
            lines = f.readlines()
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception as e:
        logger.warning(f"⚠️ Could not read heartbeat: {e}")
        return None


# ----------------------------------------------------------
# 🌈 Convert ΔΦ → Δψ (Amplitude Translation)
# ----------------------------------------------------------
def phi_to_psi_mapping(delta_phi_coh: float, stability: float) -> dict:
    """
    Translate cognitive resonance (ΔΦ_coh, stability) into
    photonic amplitude and phase patterns (Δψ vector).
    """
    base_amplitude = 1.0 + delta_phi_coh * 20
    coherence_mod = stability * math.cos(delta_phi_coh * math.pi)
    phase_shift = (1.0 - stability) * 90.0  # degrees

    pattern = {
        "Δψ₁": base_amplitude * math.sin(math.radians(phase_shift)),
        "Δψ₂": base_amplitude * math.cos(math.radians(phase_shift)),
        "Δψ₃": coherence_mod,
        "phase_shift": round(phase_shift, 3),
        "stability": round(stability, 4),
    }
    return pattern


# ----------------------------------------------------------
# 💡 Emit .photo Signal
# ----------------------------------------------------------
def emit_photo_signal(pattern: dict):
    """
    Emit photonic signal to QQC layer or local .photo file.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    filename = PHOTO_OUTPUT_DIR / f"photon_{timestamp}.photo"
    payload = {
        "timestamp": timestamp,
        "pattern": pattern,
        "source": "AION_QFC",
    }

    # Optional live emission to QQC
    if emit_photon_wave:
        try:
            emit_photon_wave(payload)
            logger.info("⚡ Photon wave emitted to QQC lattice.")
        except Exception as e:
            logger.warning(f"⚠️ Photon emission failed: {e}")

    # Always store local .photo artifact
    with open(filename, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info(f"🪶 Photon pattern written → {filename.name}")


# ----------------------------------------------------------
# 🌀 Main Feedback Loop
# ----------------------------------------------------------
async def quantum_feedback_loop(interval: int = 60):
    """
    Continuously reads latest heartbeat, maps ΔΦ→Δψ,
    and emits photonic resonance packets.
    """
    logger.info("🌌 Starting Quantum Feedback Coupler (QFC)...")

    while True:
        hb = read_latest_heartbeat()
        if hb:
            delta_phi_coh = float(hb.get("mean_coherence_delta", 0.0))
            stability = float(hb.get("mean_stability", 1.0))
            pattern = phi_to_psi_mapping(delta_phi_coh, stability)
            emit_photo_signal(pattern)
            logger.info(
                f"🧠 ΔΦ→Δψ mapping complete | ΔΦ={delta_phi_coh:+.4f} | Stability={stability:.4f}"
            )
        await asyncio.sleep(interval)


# ----------------------------------------------------------
# 🚀 Entry Point
# ----------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(quantum_feedback_loop(interval=60))
    except KeyboardInterrupt:
        logger.info("🛑 QFC stopped manually.")