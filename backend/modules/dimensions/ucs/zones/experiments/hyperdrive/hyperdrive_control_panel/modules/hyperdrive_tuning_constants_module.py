"""
🎛 Hyperdrive Tuning Constants Module
--------------------------------------
• Centralizes all Hyperdrive + QWave tuning constants and utility methods.
• Shared across ECU runtime, Auto-Tuner, SQI Controllers, Gear Shift, and Engine logic.
• ✅ Supports runtime persistence (load/save last-tuned values).
• 🔮 SQI adjustment integration, particle velocity enforcement, plasma dwell gating.
• 🛡 Auto-validates and injects missing constants to prevent boot-time AttributeErrors.
• 🔧 Fully merged with QWave tuning (legacy harmonic maps, stages, auto-tuning).
"""

import os
import json
from typing import List, Dict
from datetime import datetime
from copy import deepcopy

# ==========================================
# 🏗 Stage Configurations
# ==========================================
STAGE_CONFIGS = {
    "G1": {"gravity": 2.0, "magnetism": 1.0, "wave_frequency": 0.6, "field_pressure": 1.1},
    "idle": {"gravity": 2.0, "magnetism": 1.0},
    "plasma_excitation": {"wave_frequency": 0.8, "field_pressure": 1.2},
    "resonance_lock": {"wave_frequency": 1.0, "field_pressure": 1.5},
    "warp_alignment": {"gravity": 2.5, "magnetism": 1.5},
    "proton_injection": {"gravity": 1.2, "magnetism": 1.1, "wave_frequency": 1.0},
    "wave_focus": {"gravity": 2.0, "magnetism": 1.5, "wave_frequency": 1.0},
    "black_hole_compression": {"gravity": 3.0, "magnetism": 1.8, "wave_frequency": 1.1},
    "torus_field_loop": {"gravity": 2.5, "magnetism": 1.6, "wave_frequency": 1.0},
    "controlled_exhaust": {"gravity": 1.5, "magnetism": 1.0, "wave_frequency": 0.8},
}

# ==========================================
# 🎼 Harmonic Defaults
# ==========================================
HARMONIC_DEFAULTS = [1, 2, 4, 8]   # Hyperdrive
QWAVE_HARMONICS = [2, 3]           # Legacy
HARMONIC_GAIN = 0.9275
QWAVE_HARMONIC_GAIN = 0.03
DECAY_RATE = 0.996
DAMPING_FACTOR = 0.981

# ==========================================
# 🌊 Drift & Warp Thresholds
# ==========================================
RESONANCE_DRIFT_THRESHOLD = 2.4
QWAVE_DRIFT_THRESHOLD = 5.0
WARP_PI_THRESHOLD = 3.14159

# ==========================================
# 🔒 Safety & Physical Limits
# ==========================================
MAX_MAGNETISM = 2.5
MAX_PARTICLE_SPEED = 2500.0
IGNITION_PARTICLE_SPEED = 50.0
THERMAL_MAX = 850.0
THERMAL_SLOPE_MAX = 5.0
POWER_MAX = 1_200_000.0
STABILITY_INDEX_MIN = 0.92

# ==========================================
# 💾 Persistence
# ==========================================
PERSISTENCE_FILE = "data/runtime_hyperdrive_constants.json"
__all__ = ["HyperdriveTuningConstants", "HyperdriveAutoTuner"]


class HyperdriveTuningConstants:
    """
    🧩 Shared constant library for ECU runtime, SQI, Drift Damping, Gear Shift, Tick Orchestrator.
    """

    # =========================
    # Core Stability Thresholds
    # =========================
    ENABLE_COLLAPSE: bool = True
    RESONANCE_DRIFT_THRESHOLD: float = RESONANCE_DRIFT_THRESHOLD
    INSTABILITY_HIT_LIMIT: int = 5
    PLASMA_DWELL_TICKS: int = 150
    MAX_MAGNETISM: float = MAX_MAGNETISM
    WARP_PI_THRESHOLD: float = WARP_PI_THRESHOLD

    # =========================
    # Harmonic & Field Config
    # =========================
    HARMONIC_DEFAULTS: list = list(HARMONIC_DEFAULTS)
    QWAVE_HARMONICS: list = list(QWAVE_HARMONICS)
    HARMONIC_GAIN: float = HARMONIC_GAIN
    QWAVE_HARMONIC_GAIN: float = QWAVE_HARMONIC_GAIN
    HARMONIC_RATE_LIMIT: float = 0.002
    DAMPING_FACTOR: float = DAMPING_FACTOR
    DECAY_RATE: float = DECAY_RATE

    # =========================
    # Particle Physics
    # =========================
    MAX_PARTICLE_SPEED: float = MAX_PARTICLE_SPEED
    IGNITION_PARTICLE_SPEED: float = IGNITION_PARTICLE_SPEED

    # =========================
    # Safety Limits (ECU-aligned)
    # =========================
    THERMAL_MAX: float = THERMAL_MAX
    THERMAL_SLOPE_MAX: float = THERMAL_SLOPE_MAX
    POWER_MAX: float = POWER_MAX
    STABILITY_INDEX_MIN: float = STABILITY_INDEX_MIN

    MAX_GRAVITY: float = 3.5
    MIN_GRAVITY: float = 0.1

    # =========================
    # Idle Baseline Fields
    # =========================
    BEST_IDLE_FIELDS = {
        "gravity": 1.94,
        "magnetism": 1.0,
        "wave_frequency": 0.541,
        "field_pressure": 1.0,
    }

    # =========================
    # Stage Configurations
    # =========================
    STAGE_CONFIGS: dict = STAGE_CONFIGS

    # =========================
    # Harmonic Stage Map (QWave legacy)
    # =========================
    HARMONIC_STAGE_MAP = {
        "proton_injection": 0.8,
        "plasma_excitation": 1.0,
        "wave_focus": 1.2,
        "black_hole_compression": 1.3,
        "torus_field_loop": 1.1,
        "controlled_exhaust": 0.7,
    }

    def __init__(self, harmonic_gain, harmonic_decay, damping_factor, drift_threshold, thermal_slope_max):
        self.harmonic_gain = harmonic_gain
        self.harmonic_decay = harmonic_decay
        self.damping_factor = damping_factor
        self.drift_threshold = drift_threshold
        self.thermal_slope_max = thermal_slope_max

    # =========================
    # Utility Methods
    # =========================
    @staticmethod
    def harmonic_for_stage(stage: str) -> float:
        if stage in HyperdriveTuningConstants.HARMONIC_STAGE_MAP:
            return HyperdriveTuningConstants.HARMONIC_STAGE_MAP[stage]
        elif stage in HyperdriveTuningConstants.STAGE_CONFIGS:
            return 1.0 + 0.05 * list(HyperdriveTuningConstants.STAGE_CONFIGS.keys()).index(stage)
        print(f"⚠ Unknown stage '{stage}', default harmonic=1.0")
        return 1.0

    @staticmethod
    def apply_drift_damping(drift: float, fields: Dict[str, float], stage: str = None) -> bool:
        if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
            fields["gravity"] *= 0.98
            fields["magnetism"] *= 0.98
            print(f"🌊 Drift damping applied: Drift={drift:.4f} (Stage={stage})")
            return True
        return False

    @staticmethod
    def clamp_particle_velocity(particles: List[dict]) -> None:
        for p in particles:
            if isinstance(p, dict) and all(k in p for k in ("vx", "vy", "vz")):
                speed = (p["vx"] ** 2 + p["vy"] ** 2 + p["vz"] ** 2) ** 0.5
                if speed > HyperdriveTuningConstants.MAX_PARTICLE_SPEED:
                    scale = HyperdriveTuningConstants.MAX_PARTICLE_SPEED / speed
                    p["vx"] *= scale
                    p["vy"] *= scale
                    p["vz"] *= scale
                    print(f"⚠ Particle speed clamped: {HyperdriveTuningConstants.MAX_PARTICLE_SPEED:.2f}")
    
    @classmethod
    def restore(cls):
        # You can replace this with real logic later
        return cls(
            harmonic_gain=0.9,
            harmonic_decay=0.995,
            damping_factor=0.98,
            drift_threshold=8.711723292255693,
            thermal_slope_max=5.0
        )

    @staticmethod
    def ignition_velocity_clamp(particles: List[dict], max_speed: float = IGNITION_PARTICLE_SPEED):
        for p in particles:
            if isinstance(p, dict):
                p["vx"] = max(min(p.get("vx", 0), max_speed), -max_speed)
                p["vy"] = max(min(p.get("vy", 0), max_speed), -max_speed)
                p["vz"] = max(min(p.get("vz", 0), max_speed), -max_speed)

    @classmethod
    def enforce_particle_safety(cls, engine):
        cls.clamp_particle_velocity(engine.particles)

    @staticmethod
    def enforce_plasma_dwell(engine, ticks_since_stage_change: int) -> bool:
        if engine.stages[engine.current_stage] == "plasma_excitation" and ticks_since_stage_change < HyperdriveTuningConstants.PLASMA_DWELL_TICKS:
            print(f"⏸ Plasma dwell enforced: {ticks_since_stage_change}/{HyperdriveTuningConstants.PLASMA_DWELL_TICKS}")
            return False
        return True

    @classmethod
    def damp_harmonic_gain_if_stalled(cls, coherence: float):
        if not hasattr(cls, "_gain_boosts"):
            cls._gain_boosts = 0
        if coherence == 0.0:
            cls._gain_boosts += 1
            if cls._gain_boosts > 3:
                cls.HARMONIC_GAIN = 1.0
                print("🔧 Harmonic gain reset due to stalled coherence.")
        else:
            cls._gain_boosts = 0

    @classmethod
    def apply_profile(cls, profile: str):
        if profile == "idle":
            cls.HARMONIC_GAIN, cls.DECAY_RATE, cls.DAMPING_FACTOR = 0.9, 0.995, 0.98
        elif profile == "warp":
            cls.HARMONIC_GAIN, cls.DECAY_RATE, cls.DAMPING_FACTOR = 1.05, 1.002, 0.975
            cls.WARP_PI_THRESHOLD = 3.5
        elif profile == "safe":
            cls.safe_defaults()
        print(f"🔧 Applied tuning profile: {profile}")

    # =========================
    # Runtime Persistence
    # =========================
    @classmethod
    def save_runtime(cls):
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
                cls.seed_defaults()
        else:
            print("🔄 No runtime file found → Seeding with known stable constants.")
            cls.seed_defaults()
        cls.validate_constants()

    @classmethod
    def debug_pi_threshold(cls):
        print(f"🚀 WARP_PI_THRESHOLD currently set to {cls.WARP_PI_THRESHOLD}")

    @classmethod
    def seed_defaults(cls):
        cls.HARMONIC_GAIN = 0.9275
        cls.DECAY_RATE = 0.996
        cls.DAMPING_FACTOR = 0.981
        cls.RESONANCE_DRIFT_THRESHOLD = 2.4
        cls.THERMAL_SLOPE_MAX = 5.0
        print("✅ Seeded stable constants.")

    @classmethod
    def apply_sqi_adjustments(cls, adjustments: dict):
        if "harmonic_gain" in adjustments: cls.HARMONIC_GAIN = adjustments["harmonic_gain"]
        if "harmonic_decay" in adjustments: cls.DECAY_RATE = adjustments["harmonic_decay"]
        if "damping_factor" in adjustments: cls.DAMPING_FACTOR = adjustments["damping_factor"]
        if "drift_threshold" in adjustments: cls.RESONANCE_DRIFT_THRESHOLD = adjustments["drift_threshold"]
        if "thermal_slope_max" in adjustments: cls.THERMAL_SLOPE_MAX = adjustments["thermal_slope_max"]
        cls.save_runtime()
        print(f"🔄 SQI-adjusted constants applied: {adjustments}")

    @classmethod
    def debug_harmonics(cls):
        print(f"🎵 Harmonic Defaults: {cls.HARMONIC_DEFAULTS} | QWave Harmonics: {cls.QWAVE_HARMONICS}")
        print(f"📊 Gain={cls.HARMONIC_GAIN:.4f} | QWave Gain={cls.QWAVE_HARMONIC_GAIN:.4f}")
        print(f"Decay={cls.DECAY_RATE:.4f} | Damping={cls.DAMPING_FACTOR:.4f}")

    @classmethod
    def debug_stages(cls):
        print("🚀 Hyperdrive Stage Configurations:")
        for stage, cfg in cls.STAGE_CONFIGS.items():
            print(f"  • {stage}: {cfg}")

    @classmethod
    def validate_constants(cls):
        defaults = {
            "THERMAL_MAX": 850.0,
            "THERMAL_SLOPE_MAX": 5.0,
            "POWER_MAX": 1_200_000.0,
            "STABILITY_INDEX_MIN": 0.92,
            "MAX_GRAVITY": 3.5,
            "MIN_GRAVITY": 0.1,
            "MAX_MAGNETISM": 2.5,
            "WARP_PI_THRESHOLD": 3.14159,
        }
        for const, val in defaults.items():
            if not hasattr(cls, const):
                setattr(cls, const, val)
                print(f"⚠ Missing constant '{const}' auto-injected with default {val}")

    @classmethod
    def safe_defaults(cls):
        print("🛡 Resetting Hyperdrive constants to safe defaults.")
        cls.HARMONIC_GAIN = 1.25
        cls.DECAY_RATE = 0.015
        cls.DAMPING_FACTOR = 0.005
        cls.RESONANCE_DRIFT_THRESHOLD = 0.08
        cls.THERMAL_SLOPE_MAX = 5.0
        cls.MAX_GRAVITY = 3.5
        cls.MIN_GRAVITY = 0.1


# ✅ Validate constants on import
HyperdriveTuningConstants.validate_constants()


# =========================
# 🔥 Hyperdrive Auto-Tuner
# =========================
class HyperdriveAutoTuner:
    def __init__(self, engine):
        self.engine = engine
        self.cooldown = 0

    def tune(self, iterations=50):
        print("🔥 Preheating engine (QWave baseline)...")
        for _ in range(50):
            if hasattr(self.engine, "tick"):
                self.engine.tick()

        for i in range(iterations):
            drift = self._get_drift()
            stability = self._evaluate_stability()
            print(f"🔄 Iter {i+1}/{iterations} | Drift={drift:.4f} | Stability={stability:.4f}")

            if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD and self.cooldown == 0:
                print("⚠ SQI drift correction triggered.")
                if hasattr(self.engine, "_run_sqi_feedback"):
                    self.engine._run_sqi_feedback()
                self.cooldown = 3
            elif stability >= 0.95:
                print("✅ Stability achieved. Auto-tuning complete.")
                self._export_snapshot()
                break

            if self.cooldown > 0:
                self.cooldown -= 1

    def _get_drift(self) -> float:
        if not self.engine.resonance_filtered:
            return 0.0
        window = self.engine.resonance_filtered[-10:]
        return max(window) - min(window)

    def _evaluate_stability(self) -> float:
        if not self.engine.resonance_filtered:
            return 0.0
        window = self.engine.resonance_filtered[-20:]
        drift = max(window) - min(window)
        return min(1.0, max(0.0, 1.0 - min(drift / 10.0, 1.0)))

    def _export_snapshot(self):
        os.makedirs("data/hyperdrive_logs", exist_ok=True)
        snapshot_path = f"data/hyperdrive_logs/final_tuning_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dc.json"
        snapshot = {
            "fields": deepcopy(self.engine.fields),
            "particles": len(self.engine.particles),
            "stage": self.engine.stages[self.engine.current_stage],
            "score": getattr(self.engine, "best_score", 0.0),
            "timestamp": datetime.utcnow().isoformat(),
        }
        with open(snapshot_path, "w") as f:
            json.dump(snapshot, f, indent=2)
        print(f"📦 Final tuning snapshot exported → {snapshot_path}")