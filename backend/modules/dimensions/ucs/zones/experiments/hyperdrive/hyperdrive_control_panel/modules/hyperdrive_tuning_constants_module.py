# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/hyperdrive_tuning_constants_module.py

"""
🎛 Hyperdrive Tuning Constants Module
--------------------------------------
• Centralizes all Hyperdrive tuning constants and utility methods.
• Shared across ECU runtime, Auto-Tuner, SQI Controllers, Gear Shift, and Engine logic.
• ✅ Supports runtime persistence (load/save last-tuned values).
• 🔮 SQI adjustment integration, particle velocity enforcement, plasma dwell gating.
• 🛡 Auto-validates and injects missing constants to prevent boot-time AttributeErrors.
"""

import os
import json
from typing import List, Dict

# ==========================================
# 🔧 Localized Constants (Legacy-Free)
# ==========================================
STAGE_CONFIGS = {
    "G1": {"gravity": 2.0, "magnetism": 1.0, "wave_frequency": 0.6, "field_pressure": 1.1},  # ✅ Added for engine init
    "idle": {"gravity": 2.0, "magnetism": 1.0},
    "plasma_excitation": {"wave_frequency": 0.8, "field_pressure": 1.2},
    "resonance_lock": {"wave_frequency": 1.0, "field_pressure": 1.5},
    "warp_alignment": {"gravity": 2.5, "magnetism": 1.5},
}

HARMONIC_DEFAULTS = [1, 2, 4, 8]
HARMONIC_GAIN = 1.25
DECAY_RATE = 0.015
DAMPING_FACTOR = 0.005
RESONANCE_DRIFT_THRESHOLD = 0.08
MAX_PARTICLE_SPEED = 2500.0

# ✅ Safety thresholds (aligned to ECU runtime)
THERMAL_MAX = 850.0            # °C
THERMAL_SLOPE_MAX = 5.0        # °C/sec climb rate
POWER_MAX = 1_200_000.0        # Watts
STABILITY_INDEX_MIN = 0.92     # Stability floor

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
    HARMONIC_DEFAULTS: list = list(HARMONIC_DEFAULTS)
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
    THERMAL_MAX: float = THERMAL_MAX
    THERMAL_SLOPE_MAX: float = THERMAL_SLOPE_MAX
    POWER_MAX: float = POWER_MAX
    STABILITY_INDEX_MIN: float = STABILITY_INDEX_MIN

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
        if stage not in HyperdriveTuningConstants.STAGE_CONFIGS:
            print(f"⚠ Unknown stage '{stage}', defaulting harmonic gain to 1.0")
            return 1.0
        return 1.0 + 0.05 * list(HyperdriveTuningConstants.STAGE_CONFIGS.keys()).index(stage)

    @staticmethod
    def apply_drift_damping(drift: float, fields: Dict[str, float], stage: str = None) -> bool:
        """
        Apply drift damping if drift exceeds threshold.
        Returns True if damping was applied.
        """
        if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
            fields["gravity"] *= 0.98
            fields["magnetism"] *= 0.98
            stage_info = f" during stage '{stage}'" if stage else ""
            print(f"🌊 Drift damping applied: Drift={drift:.4f}{stage_info}")
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
        """Clamp particle speeds and log if over-threshold."""
        cls.clamp_particle_velocity(engine.particles)
        fast_particles = [
            p for p in engine.particles
            if ((p["vx"] ** 2 + p["vy"] ** 2 + p["vz"] ** 2) ** 0.5) > cls.MAX_PARTICLE_SPEED
        ]
        if fast_particles:
            print(f"⚠ Particle velocity exceeded limit. {len(fast_particles)} corrected.")

    @staticmethod
    def enforce_plasma_dwell(engine, ticks_since_stage_change: int) -> bool:
        """Enforce minimum dwell in plasma excitation stage before shifting or advancing."""
        if engine.stages[engine.current_stage] == "plasma_excitation" and ticks_since_stage_change < HyperdriveTuningConstants.PLASMA_DWELL_TICKS:
            print(f"⏸ Plasma dwell enforced: {ticks_since_stage_change}/{HyperdriveTuningConstants.PLASMA_DWELL_TICKS} ticks.")
            return False
        return True

    # =========================
    # Harmonic Gain Damping
    # =========================
    @classmethod
    def damp_harmonic_gain_if_stalled(cls, coherence: float):
        """
        If coherence remains zero across multiple boosts, reset harmonic gain to prevent runaway increase.
        """
        if not hasattr(cls, "_gain_boosts"):
            cls._gain_boosts = 0
        if coherence == 0.0:
            cls._gain_boosts += 1
            if cls._gain_boosts > 3:
                cls.HARMONIC_GAIN = 1.0
                print("🔧 Harmonic gain reset to safe baseline due to stalled coherence.")
        else:
            cls._gain_boosts = 0  # reset if coherence recovers

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
            "thermal_slope_max": cls.THERMAL_SLOPE_MAX,
        }
        os.makedirs(os.path.dirname(PERSISTENCE_FILE), exist_ok=True)
        with open(PERSISTENCE_FILE, "w") as f:
            json.dump(constants, f, indent=4)
        print(f"💾 HyperdriveTuningConstants saved: {constants}")

    @classmethod
    def load_runtime(cls):
        """Load last runtime constants and sync into class-level attributes."""
        if os.path.exists(PERSISTENCE_FILE):
            try:
                with open(PERSISTENCE_FILE, "r") as f:
                    constants = json.load(f)
                cls.HARMONIC_GAIN = constants.get("harmonic_gain", cls.HARMONIC_GAIN)
                cls.DECAY_RATE = constants.get("harmonic_decay", cls.DECAY_RATE)
                cls.DAMPING_FACTOR = constants.get("damping_factor", cls.DAMPING_FACTOR)
                cls.RESONANCE_DRIFT_THRESHOLD = constants.get("drift_threshold", cls.RESONANCE_DRIFT_THRESHOLD)
                cls.THERMAL_SLOPE_MAX = constants.get("thermal_slope_max", cls.THERMAL_SLOPE_MAX)
                print(f"♻ HyperdriveTuningConstants restored: {constants}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠ Failed to load runtime constants: {e} → Resetting to defaults.")
                cls.safe_defaults()
        cls.validate_constants()

    @classmethod
    def apply_sqi_adjustments(cls, adjustments: dict):
        """Apply SQI tuning results directly to runtime constants and persist."""
        if "harmonic_gain" in adjustments: cls.HARMONIC_GAIN = adjustments["harmonic_gain"]
        if "harmonic_decay" in adjustments: cls.DECAY_RATE = adjustments["harmonic_decay"]
        if "damping_factor" in adjustments: cls.DAMPING_FACTOR = adjustments["damping_factor"]
        if "drift_threshold" in adjustments: cls.RESONANCE_DRIFT_THRESHOLD = adjustments["drift_threshold"]
        if "thermal_slope_max" in adjustments: cls.THERMAL_SLOPE_MAX = adjustments["thermal_slope_max"]
        cls.save_runtime()
        print(f"🔄 SQI-adjusted constants applied: {adjustments}")

    @classmethod
    def debug_harmonics(cls):
        """Log current harmonics for verification."""
        print(f"🎵 Active Harmonic Defaults: {cls.HARMONIC_DEFAULTS}")
        print(f"📊 Gain={cls.HARMONIC_GAIN:.4f} | Decay={cls.DECAY_RATE:.4f} | Damping={cls.DAMPING_FACTOR:.4f}")
        print(f"🌡 Thermal Slope Max={cls.THERMAL_SLOPE_MAX:.2f} °C/sec")

    @classmethod
    def debug_stages(cls):
        """Print all configured stage constants."""
        print("🚀 Hyperdrive Stage Configurations:")
        for stage, cfg in cls.STAGE_CONFIGS.items():
            print(f"  • {stage}: {cfg}")

    # =========================
    # Auto-Validation
    # =========================
    @classmethod
    def validate_constants(cls):
        """Ensure all required constants exist; inject defaults if missing."""
        defaults = {
            "THERMAL_MAX": 850.0,
            "THERMAL_SLOPE_MAX": 5.0,
            "POWER_MAX": 1_200_000.0,
            "STABILITY_INDEX_MIN": 0.92,
        }
        for const, val in defaults.items():
            if not hasattr(cls, const):
                setattr(cls, const, val)
                print(f"⚠ Missing constant '{const}' auto-injected with default {val}")

    @classmethod
    def safe_defaults(cls):
        """Reset constants to baseline safe values if persistence is corrupted."""
        print("🛡 Resetting Hyperdrive constants to safe defaults.")
        cls.HARMONIC_GAIN = 1.25
        cls.DECAY_RATE = 0.015
        cls.DAMPING_FACTOR = 0.005
        cls.RESONANCE_DRIFT_THRESHOLD = 0.08
        cls.THERMAL_SLOPE_MAX = 5.0


# ✅ Validate constants on import
HyperdriveTuningConstants.validate_constants()