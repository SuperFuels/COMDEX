# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/safe_tuning_module.py

import json
import os
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants


def safe_qwave_tuning() -> dict:
    """
    Returns only safe, serializable hyperdrive tuning constants.
    Intended for UIs, APIs, or telemetry dashboards that must read QWave runtime constants
    without exposing full engine state or sensitive control hooks.
    """
    return {
        "STAGE_CONFIGS": getattr(HyperdriveTuningConstants, "STAGE_CONFIGS", []),
        "HARMONIC_DEFAULTS": getattr(HyperdriveTuningConstants, "HARMONIC_DEFAULTS", []),
        "HARMONIC_GAIN": getattr(HyperdriveTuningConstants, "HARMONIC_GAIN", 1.0),
        "DECAY_RATE": getattr(HyperdriveTuningConstants, "DECAY_RATE", 0.99),
        "DAMPING_FACTOR": getattr(HyperdriveTuningConstants, "DAMPING_FACTOR", 0.9),
        "RESONANCE_DRIFT_THRESHOLD": getattr(HyperdriveTuningConstants, "RESONANCE_DRIFT_THRESHOLD", 0.01),
        "MAX_PARTICLE_SPEED": getattr(HyperdriveTuningConstants, "MAX_PARTICLE_SPEED", 10.0),
        "MAX_GRAVITY": getattr(HyperdriveTuningConstants, "MAX_GRAVITY", 5.0),
        "MAX_MAGNETISM": getattr(HyperdriveTuningConstants, "MAX_MAGNETISM", 5.0),
        "THERMAL_MAX": getattr(HyperdriveTuningConstants, "THERMAL_MAX", 250.0),  # 🔥 Added from updated constants
        "HYPERDRIVE_TUNING_VERSION": getattr(HyperdriveTuningConstants, "VERSION", "1.0.0"),
        "HARMONIC_COHERENCE_MIN": getattr(HyperdriveTuningConstants, "HARMONIC_COHERENCE_MIN", 0.65),
    }


def export_safe_constants_to_json(path: str = "data/qwave_safe_constants.json") -> str:
    """
    Exports safe constants to JSON for UI or external API sync.
    This allows dashboards or control interfaces to load verified tuning values.
    """
    constants = safe_qwave_tuning()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(constants, f, indent=4)
    print(f"✅ Safe QWave tuning constants exported → {path}")
    return path


def validate_constant_ranges(engine_fields: dict) -> bool:
    """
    Validates engine field values against safe constant bounds.
    This can be used by idle_manager or SQI feedback loops to auto-correct out-of-range fields.
    """
    if not engine_fields:
        print("⚠ Engine fields missing for validation.")
        return False

    max_gravity = getattr(HyperdriveTuningConstants, "MAX_GRAVITY", 5.0)
    max_magnetism = getattr(HyperdriveTuningConstants, "MAX_MAGNETISM", 5.0)
    wave_min, wave_max = 0.1, 10.0

    gravity = engine_fields.get("gravity", 0)
    magnetism = engine_fields.get("magnetism", 0)
    wave_freq = engine_fields.get("wave_frequency", 1.0)

    if not (0.0 < gravity <= max_gravity):
        print(f"⚠ Gravity field out of safe range: {gravity} (Max={max_gravity})")
        return False
    if not (0.0 < magnetism <= max_magnetism):
        print(f"⚠ Magnetism field out of safe range: {magnetism} (Max={max_magnetism})")
        return False
    if not (wave_min <= wave_freq <= wave_max):
        print(f"⚠ Wave frequency out of range: {wave_freq} (Allowed={wave_min}-{wave_max})")
        return False

    return True