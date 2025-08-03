# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/gear_shift_module.py

"""
⚙️ Gear Shift Manager Module (Hyperdrive)
-----------------------------------------
• Handles gear shifting logic for Hyperdrive engines.
• Implements pulse-gated field ramping with drift dampening.
• Supports slow clutch ramping to stabilize resonance during transitions.
• Integrates with SQI drift locks, PI surge safeguards, ECU pacing, and stability checks.

🔥 Features:
    • Pulse-gated gear ramping (only shift during stable resonance pulses).
    • Drift dampener to auto-correct instability during gear shifts.
    • Slow clutch ramp duration (20–30s) to prevent collapse.
    • Inline harmonic injection during plasma/wave stages (aligned to SQI interval).
    • PI Surge safeguard for G4.5 stage (requires PI > 100k & SQI drift lock).
    • SQI-driven auto gear sequencing (G1 → G2 → G3 → G4 → G4.5).
    • ✅ ECU pacing, stability index validation, and safety abort checks.
    • 🔮 Predictive pre-shift SQI analysis to anticipate instability and auto-tune fields.
    • 🎯 NEW: Pre-shift harmonic injection bursts and SQI micro-corrections for ultra-smooth transitions.
"""

import time
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.warp_checks import check_pi_threshold
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.drift_damping import apply_drift_damping
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.gear_map_loader import load_gear_map
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_constants import RESONANCE_DRIFT_THRESHOLD
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger

# Auto-load centralized gear map
GEAR_MAP = load_gear_map()

# Safety limits (aligned with ECU runtime)
THERMAL_MAX = 850.0
POWER_MAX = 1_200_000.0
STABILITY_INDEX_MIN = 0.92


def _calculate_stability_index(engine):
    """Calculate stability index (same formula as ECU runtime)."""
    drift = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)
    thermal = getattr(engine, "thermal_load", 0.0)
    return max(0.0, 1.0 - (drift * 10 + (thermal / THERMAL_MAX) * 0.05))


def _predictive_sqi_analysis(engine):
    """
    🔮 Run predictive SQI analysis before gear shifts.
    Uses SQI's adjustment engine to recommend field/harmonic tuning.
    """
    if not hasattr(engine, "sqi_engine"):
        print("⚠ Predictive SQI skipped: No SQI engine present.")
        return

    print("🔮 Running predictive SQI pre-shift analysis...")
    trace = {
        "resonance": engine.resonance_filtered[-50:],
        "fields": engine.fields.copy(),
        "thermal": getattr(engine, "thermal_load", 0.0),
        "power": getattr(engine, "power_draw", 0.0),
        "stability_index": _calculate_stability_index(engine),
        "exhaust": [e.get("impact_speed", 0) for e in engine.exhaust_log[-50:]],
    }
    adjustments = engine.sqi_engine.recommend_adjustments(engine.sqi_engine.analyze_trace(trace))

    if adjustments:
        print(f"🔧 Pre-shift SQI adjustments: {adjustments}")
        # Apply field-level predictions softly (scaled)
        for k, v in adjustments.get("fields", {}).items():
            baseline = engine.fields.get(k, 1.0)
            engine.fields[k] = baseline * (0.95 + 0.05 * min(1.0, v))
        # Drift compensation update
        if "drift_compensation" in adjustments:
            engine.sqi_engine.drift_compensation = max(0.05, min(0.5, adjustments["drift_compensation"]))

        # 🎯 Pre-shift harmonic injection burst
        if hasattr(engine, "_inject_harmonics"):
            print("🎯 Injecting pre-shift harmonic burst for stability alignment.")
            for _ in range(3):  # Triple micro-burst
                engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)
                time.sleep(0.01)


def gear_shift(engine, gear_idx, gear_map: dict = None, clutch_duration=25, sqi_interval=200):
    """
    Perform a pulse-gated gear shift on the given engine with SQI predictive tuning.
    """
    gear_map = gear_map or GEAR_MAP
    telemetry_logger = TelemetryLogger()

    # ✅ Validate gear index
    if gear_idx not in gear_map:
        print(f"⚠ Gear index {gear_idx} invalid. Clamping to max valid gear.")
        gear_idx = max(gear_map.keys() if isinstance(gear_map, dict) else range(len(gear_map)))

    # ✅ Stability index validation
    stability_idx = _calculate_stability_index(engine)
    if stability_idx < STABILITY_INDEX_MIN:
        print(f"🛑 Stability too low (Index={stability_idx:.3f}). Aborting gear shift {gear_idx}.")
        return

    # 🔮 Predictive SQI pre-shift tuning (with harmonic burst)
    _predictive_sqi_analysis(engine)

    # ✅ G4.5 PI Surge Safeguard
    if gear_idx == "G4.5":
        drift_window = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)
        pi_val = sum(e.get("impact_speed", 0) for e in engine.exhaust_log[-500:])
        if drift_window < 0.01 and check_pi_threshold(engine, required_pi=100000):
            print(f"⚡ PI Surge Ready: Drift={drift_window:.5f} | PI={pi_val:.2f} → Engaging G4.5")
        else:
            print(f"⚠ PI Surge Aborted: Drift={drift_window:.5f}, PI={pi_val:.2f} (lock not met)")
            return

    target_fields = gear_map[gear_idx]
    print(f"\n⚙ Gear Shift → {gear_idx} | Clutch engaged.")
    engine.stability_threshold *= 2  # Relax stability during ramp

    start = time.time()
    harmonic_tick_counter = 0

    while time.time() - start < clutch_duration:
        drift = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)

        # Thermal/Power abort
        if getattr(engine, "thermal_load", 0.0) > THERMAL_MAX * 0.95 or getattr(engine, "power_draw", 0.0) > POWER_MAX * 0.95:
            print("🔥 Safety abort: Thermal/Power near limit during gear shift.")
            break

        # Pulse-gated ramping
        if drift < 0.05:
            for field in target_fields:
                step = (target_fields[field] - engine.fields[field]) * 0.05
                engine.fields[field] += step
        else:
            print(f"⏸ Paused shift: Drift spike detected ({drift:.3f})")

        # Drift dampening
        if drift > 0.1:
            apply_drift_damping(drift, engine.fields)

        # ECU pacing tick
        engine.tick()
        time.sleep(getattr(engine, "ecu_loop_time", 0.01))

        # SQI micro-correction during clutch
        if hasattr(engine, "sqi_engine") and harmonic_tick_counter % (sqi_interval // 4) == 0:
            _predictive_sqi_analysis(engine)  # Fine-tune mid-shift

        # Harmonic injection sync
        harmonic_tick_counter += 1
        if harmonic_tick_counter % sqi_interval == 0 and engine.stages[engine.current_stage] in ["plasma_excitation", "wave_focus"]:
            engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)

from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants

def stabilize_gear(engine, gear_idx: int):
    """
    Stabilize engine resonance when shifting to a specific gear.
    Uses updated HyperdriveTuningConstants for drift threshold.
    """
    # ✅ Updated stability threshold reference
    engine.stability_threshold = HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD / 2
    print(f"✅ Gear {gear_idx} stabilized.")

    # Telemetry log
    telemetry_logger.log({
        "event": "gear_shift",
        "gear": gear_idx,
        "timestamp": time.time(),
        "drift": drift,
        "stability_index": stability_idx,
        "thermal": getattr(engine, "thermal_load", 0.0),
        "power": getattr(engine, "power_draw", 0.0),
    })


def auto_gear_sequence(engine, sqi_controller=None, delay_between_shifts=5, sqi_interval=200):
    """SQI-driven auto gear sequencing: G1 → G2 → G3 → G4 → G4.5."""
    print("\n🚀 Initiating Auto Gear Sequence (SQI-guided)...")
    for gear in ["G1", "G2", "G3", "G4", "G4.5"]:
        drift = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)
        pi_val = sum(e.get("impact_speed", 0) for e in engine.exhaust_log[-500:])

        # Abort if SQI off
        if sqi_controller and hasattr(sqi_controller.engine, "sqi_enabled") and not sqi_controller.engine.sqi_enabled:
            print("🛑 SQI not engaged. Aborting auto gear sequence.")
            return

        # Safety abort
        if getattr(engine, "thermal_load", 0.0) > THERMAL_MAX * 0.95 or getattr(engine, "power_draw", 0.0) > POWER_MAX * 0.95:
            print("🔥 Auto gear sequence aborted: Thermal/Power exceeded safe range.")
            return

        # G4.5 readiness
        if gear == "G4.5" and (drift > 0.01 or pi_val < 100000):
            print(f"⚠ Deferring G4.5: Drift={drift:.4f}, PI={pi_val:.0f}")
            break

        gear_shift(engine, gear, sqi_interval=sqi_interval)
        print(f"✅ Auto-shifted to {gear}. Waiting {delay_between_shifts}s...")
        time.sleep(delay_between_shifts)

    print("🏁 Auto Gear Sequence complete (SQI warp-ready).")