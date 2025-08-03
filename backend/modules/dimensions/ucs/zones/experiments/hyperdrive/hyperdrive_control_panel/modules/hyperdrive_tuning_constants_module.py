# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/hyperdrive_tuning_constants_module.py

"""
🎛 Hyperdrive Tuning Constants Module
--------------------------------------
• Centralizes all Hyperdrive tuning constants and utility methods.
• Shared across ECU runtime, Auto-Tuner, SQI Controllers, Gear Shift, and Engine logic.
• Prevents circular imports by isolating constants and helper functions.
• ✅ Now supports runtime persistence (load/save last-tuned values).
• 🔮 NEW: SQI adjustment integration, particle velocity enforcement, and plasma dwell gating.
"""

import os
import json
from typing import List, Dict
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_legacy_constants_adapter import (
    STAGE_CONFIGS,
    HARMONIC_DEFAULTS as BASE_HARMONIC_DEFAULTS,
    HARMONIC_GAIN,
    DECAY_RATE,
    DAMPING_FACTOR,
    RESONANCE_DRIFT_THRESHOLD,
    MAX_PARTICLE_SPEED,
)

__all__ = ["HyperdriveTuningConstants"]

# 💾 Persistence file shared with ECU runtime
PERSISTENCE_FILE = "data/runtime_hyperdrive_constants.json"


class HyperdriveTuningConstants:
    """
    🧩 Provides hyperdrive tuning constants and physics helper utilities.
    Designed for direct import into ECU runtime, Gear Shift, Auto-Tuner, and SQI modules.
    """

    # =========================
    # Core Stability Thresholds
    # =========================
    ENABLE_COLLAPSE: bool = True
    RESONANCE_DRIFT_THRESHOLD: float = RESONANCE_DRIFT_THRESHOLD
    INSTABILITY_HIT_LIMIT: int = 5
    PLASMA_DWELL_TICKS: int = 150  # Minimum dwell time in plasma_excitation stage

    # =========================
    # Harmonic & Field Config
    # =========================
    # ✅ Ensure harmonics is always a list of integers
    HARMONIC_DEFAULTS: list = list(BASE_HARMONIC_DEFAULTS) if not isinstance(BASE_HARMONIC_DEFAULTS, list) else BASE_HARMONIC_DEFAULTS
    HARMONIC_GAIN: float = HARMONIC_GAIN
    HARMONIC_RATE_LIMIT: float = 0.002
    DAMPING_FACTOR: float = DAMPING_FACTOR
    DECAY_RATE: float = DECAY_RATE

    # =========================
    # Particle Physics
    # =========================
    SPEED_THRESHOLD: float = 600.0
    FIELD_THRESHOLD: float = 10.0
    MAX_PARTICLE_SPEED: float = MAX_PARTICLE_SPEED

    # =========================
    # Safety Limits (ECU-aligned)
    # =========================
    THERMAL_MAX: float = 850.0           # °C (matches ECU)
    POWER_MAX: float = 1_200_000.0       # Watts (matches ECU)
    STABILITY_INDEX_MIN: float = 0.92    # Stability floor (matches ECU)

    # =========================
    # Idle Baseline Fields
    # =========================
    BEST_IDLE_FIELDS: dict = {
        "gravity": 2.0,
        "magnetism": 1.0,
        "wave_frequency": 0.5,
        "field_pressure": 1.0,
    }

    # =========================
    # Stage Configurations
    # =========================
    STAGE_CONFIGS: dict = STAGE_CONFIGS

    # =========================
    # Utility Methods
    # =========================
    @staticmethod
    def harmonic_for_stage(stage: str) -> float:
        """Return harmonic gain multiplier for a given stage."""
        return 1.0 + 0.05 * list(HyperdriveTuningConstants.STAGE_CONFIGS.keys()).index(stage)

    @staticmethod
    def apply_drift_damping(drift: float, fields: Dict[str, float]) -> bool:
        """
        Apply drift damping if drift exceeds threshold.
        Returns True if damping was applied.
        """
        if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
            fields["gravity"] *= 0.98
            fields["magnetism"] *= 0.98
            print(f"🌊 Drift damping applied: Drift={drift:.4f}")
            return True
        return False

    @staticmethod
    def clamp_particle_velocity(particles: List[dict]) -> None:
        """Clamp particle velocities to MAX_PARTICLE_SPEED (in-place)."""
        for p in particles:
            if isinstance(p, dict) and all(k in p for k in ("vx", "vy", "vz")):
                speed = (p["vx"] ** 2 + p["vy"] ** 2 + p["vz"] ** 2) ** 0.5
                if speed > HyperdriveTuningConstants.MAX_PARTICLE_SPEED:
                    scale = HyperdriveTuningConstants.MAX_PARTICLE_SPEED / speed
                    p["vx"] *= scale
                    p["vy"] *= scale
                    p["vz"] *= scale
                    print(f"⚠ Particle speed clamped: New speed={HyperdriveTuningConstants.MAX_PARTICLE_SPEED:.2f}")

    @classmethod
    def enforce_particle_safety(cls, engine):
        """
        Clamp particle speeds and log if over-threshold.
        Used in ECU runtime and Gear Shift stabilization.
        """
        cls.clamp_particle_velocity(engine.particles)
        fast_particles = [
            p for p in engine.particles
            if ((p["vx"] ** 2 + p["vy"] ** 2 + p["vz"] ** 2) ** 0.5) > cls.MAX_PARTICLE_SPEED
        ]
        if fast_particles:
            print(f"⚠ Particle velocity exceeded limit. {len(fast_particles)} corrected.")

    @staticmethod
    def enforce_plasma_dwell(engine, ticks_since_stage_change: int) -> bool:
        """
        Enforce minimum dwell in plasma excitation stage before shifting or advancing.
        Returns False if dwell not satisfied.
        """
        if engine.stages[engine.current_stage] == "plasma_excitation" and ticks_since_stage_change < HyperdriveTuningConstants.PLASMA_DWELL_TICKS:
            print(f"⏸ Plasma dwell enforced: {ticks_since_stage_change}/{HyperdriveTuningConstants.PLASMA_DWELL_TICKS} ticks.")
            return False
        return True

    # =========================
    # Runtime Persistence
    # =========================
    @classmethod
    def save_runtime(cls):
        """Persist current harmonic and drift constants to disk."""
        constants = {
            "harmonic_gain": cls.HARMONIC_GAIN,
            "harmonic_decay": cls.DECAY_RATE,
            "damping_factor": cls.DAMPING_FACTOR,
            "drift_threshold": cls.RESONANCE_DRIFT_THRESHOLD,
        }
        os.makedirs(os.path.dirname(PERSISTENCE_FILE), exist_ok=True)
        with open(PERSISTENCE_FILE, "w") as f:
            json.dump(constants, f, indent=4)
        print(f"💾 HyperdriveTuningConstants saved: {constants}")

    @classmethod
    def load_runtime(cls):
        """Load last runtime constants and sync into class-level attributes."""
        if os.path.exists(PERSISTENCE_FILE):
            with open(PERSISTENCE_FILE, "r") as f:
                constants = json.load(f)
            cls.HARMONIC_GAIN = constants.get("harmonic_gain", cls.HARMONIC_GAIN)
            cls.DECAY_RATE = constants.get("harmonic_decay", cls.DECAY_RATE)
            cls.DAMPING_FACTOR = constants.get("damping_factor", cls.DAMPING_FACTOR)
            cls.RESONANCE_DRIFT_THRESHOLD = constants.get("drift_threshold", cls.RESONANCE_DRIFT_THRESHOLD)
            print(f"♻ HyperdriveTuningConstants restored: {constants}")

    @classmethod
    def apply_sqi_adjustments(cls, adjustments: dict):
        """
        🔮 Apply SQI tuning results directly to runtime constants and persist.
        Keeps ECU and SQI harmonics in sync across sessions.
        """
        if "harmonic_gain" in adjustments: cls.HARMONIC_GAIN = adjustments["harmonic_gain"]
        if "harmonic_decay" in adjustments: cls.DECAY_RATE = adjustments["harmonic_decay"]
        if "damping_factor" in adjustments: cls.DAMPING_FACTOR = adjustments["damping_factor"]
        if "drift_threshold" in adjustments: cls.RESONANCE_DRIFT_THRESHOLD = adjustments["drift_threshold"]
        cls.save_runtime()
        print(f"🔄 SQI-adjusted constants applied: {adjustments}")

    @classmethod
    def debug_harmonics(cls):
        """Log current harmonics for verification."""
        print(f"🎵 Active Harmonic Defaults: {cls.HARMONIC_DEFAULTS}")
        print(f"📊 Gain={cls.HARMONIC_GAIN:.4f} | Decay={cls.DECAY_RATE:.4f} | Damping={cls.DAMPING_FACTOR:.4f}")