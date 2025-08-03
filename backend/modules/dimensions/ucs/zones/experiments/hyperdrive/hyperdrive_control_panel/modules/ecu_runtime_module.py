import os
import json
import time
import gzip
from datetime import datetime

from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.idle_manager_module import save_idle_state
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_engine_sync import sync_twin_engines
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.drift_damping import apply_drift_damping
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.warp_checks import check_warp_pi
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.tesseract_injector import proton_inject_cycle
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import (
    measure_harmonic_coherence,
    pre_runtime_autopulse,
)

# 🔥 Safety and predictive constants (pulled from HyperdriveTuningConstants where possible)
THERMAL_MAX = HyperdriveTuningConstants.THERMAL_MAX
THERMAL_SLOPE_MAX = HyperdriveTuningConstants.THERMAL_SLOPE_MAX
POWER_MAX = HyperdriveTuningConstants.POWER_MAX
STABILITY_INDEX_MIN = HyperdriveTuningConstants.STABILITY_INDEX_MIN

# 💾 Runtime Persistence File
PERSISTENCE_FILE = "data/runtime_hyperdrive_constants.json"

def save_runtime_constants(constants):
    os.makedirs(os.path.dirname(PERSISTENCE_FILE), exist_ok=True)
    with open(PERSISTENCE_FILE, "w") as f:
        json.dump(constants, f, indent=4)

def load_runtime_constants():
    if os.path.exists(PERSISTENCE_FILE):
        with open(PERSISTENCE_FILE, "r") as f:
            return json.load(f)
    return {}

def ecu_runtime_loop(engine_a, engine_b=None, sqi_phase_aware=False, sqi_interval=200,
                     fuel_cycle=5, manual_stage=False, ticks=12000):
    """
    🚦 ECU Runtime Loop:
    • SQI drift feedback, harmonic/tick-rate tuning, and particle scaling.
    • Predictive PI tuning, thermal slope monitoring, and stability scoring.
    • Thermal/power envelope enforcement for warp safety.
    • Phase-aware dual-engine sync and drift damping.
    • Warp PI milestone detection & segmented telemetry logging.
    """
    tick_counter = 0
    stability_index = 1.0
    prev_fields = None
    prev_thermal = 0.0
    segment_size = 2000
    drift_compensation = getattr(engine_a.sqi_engine, "drift_compensation", 0.2)
    last_drift = None

    print(f"🚦 ECU Runtime Loop Start: Target Ticks={ticks}")
    # 🔧 Pre-runtime harmonic stabilization
    pre_runtime_autopulse(engine_a)
    if engine_b:
        pre_runtime_autopulse(engine_b)

    # Restore persisted runtime constants
    runtime_constants = load_runtime_constants()
    if runtime_constants:
        print(f"♻ Restoring persisted runtime constants: {runtime_constants}")
        if "harmonic_gain" in runtime_constants: set_harmonic_gain(runtime_constants["harmonic_gain"])
        if "harmonic_decay" in runtime_constants: set_decay_rate(runtime_constants["harmonic_decay"])
        if "damping_factor" in runtime_constants: set_damping_factor(runtime_constants["damping_factor"])
        if "drift_threshold" in runtime_constants: set_resonance_threshold(runtime_constants["drift_threshold"])

    # Logging setup
    log_dir = "data/qwave_logs"
    os.makedirs(log_dir, exist_ok=True)
    logger = TelemetryLogger(log_dir=log_dir)

    stages = list(HyperdriveTuningConstants.STAGE_CONFIGS.keys())
    current_stage_idx = 0

    tick_rate = getattr(engine_a, "tick_rate", 10_000)
    ecu_loop_time = getattr(engine_a, "ecu_loop_time", 0.01)

    # ✅ Main ECU Runtime Loop
    while tick_counter < ticks:
        # =============================
        # Core Engine Tick
        # =============================
        if hasattr(engine_a, "tick") and callable(engine_a.tick):
            engine_a.tick()
        if engine_b and hasattr(engine_b, "tick") and callable(engine_b.tick):
            engine_b.tick()
        tick_counter += 1

        # ✅ Telemetry log (every tick)
        telemetry = {
            "tick": tick_counter,
            "stage": stages[current_stage_idx],
            "particles_a": len(engine_a.particles),
            "resonance_a": engine_a.resonance_phase,
            "drift_a": apply_drift_damping(engine_a),
            "thermal": getattr(engine_a, "thermal_load", 0.0),
            "power": getattr(engine_a, "power_draw", 0.0),
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.log(telemetry)

        # =============================
        # Proton Fuel Intake
        # =============================
        if tick_counter % fuel_cycle == 0:
            proton_inject_cycle(engine_a)
            if engine_b:
                proton_inject_cycle(engine_b)

        # =============================
        # Auto-generate resonance to prevent "SQI skipped"
        # =============================
        if len(engine_a.resonance_filtered) < sqi_interval:
            engine_a.resonance_filtered.append(engine_a.resonance_phase or 0.01)
            if engine_b:
                engine_b.resonance_filtered.append(engine_b.resonance_phase or 0.01)

        # =============================
        # Auto Harmonic Injection
        # =============================
        if tick_counter % sqi_interval == 0:
            if getattr(engine_a, "sqi_enabled", False) or getattr(engine_a, "sqi_locked", False):
                engine_a._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)
            if engine_b and (getattr(engine_b, "sqi_enabled", False) or getattr(engine_b, "sqi_locked", False)):
                engine_b._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)

        # =============================
        # SQI Phase-Aware Sync
        # =============================
        if sqi_phase_aware and engine_b:
            sync_twin_engines(engine_a, engine_b)

        # =============================
        # Drift Damping Safeguards
        # =============================
        drift_a = apply_drift_damping(engine_a)
        drift_b = apply_drift_damping(engine_b) if engine_b else None

        drift_trend = "—"
        if last_drift is not None:
            drift_trend = "↑" if drift_a > last_drift else "↓" if drift_a < last_drift else "→"
        last_drift = drift_a

        if drift_a > RESONANCE_DRIFT_THRESHOLD:
            print(f"⚠ Drift spike detected (Engine A): Drift={drift_a:.3f} ({drift_trend}) → SQI damping applied.")
        if drift_b and drift_b > RESONANCE_DRIFT_THRESHOLD:
            print(f"⚠ Drift spike detected (Engine B): Drift={drift_b:.3f} → SQI damping applied.")

        # =============================
        # Stage Rotation (Manual or SQI-disabled)
        # =============================
        if tick_counter % 500 == 0 and tick_counter > 0:
            current_stage_idx = (current_stage_idx + 1) % len(stages)
            stage_name = stages[current_stage_idx]
            print(f"🔀 Stage Transition → {stage_name}")
            if manual_stage or not engine_a.sqi_enabled:
                engine_a.fields.update(HyperdriveTuningConstants.STAGE_CONFIGS[stage_name])
                if engine_b:
                    engine_b.fields.update(HyperdriveTuningConstants.STAGE_CONFIGS[stage_name])
                print(f"📡 Manual stage levers applied: {HyperdriveTuningConstants.STAGE_CONFIGS[stage_name]}")

        # =============================
        # SQI Field, Runtime & Safety Modulation
        # =============================
        if tick_counter % sqi_interval == 0:
            for eng in ([engine_a] + ([engine_b] if engine_b else [])):
                if eng.sqi_enabled:
                    drift = max(eng.resonance_filtered[-30:], default=0) - min(eng.resonance_filtered[-30:], default=0)
                    thermal = getattr(eng, "thermal_load", 0.0)
                    power = getattr(eng, "power_draw", 0.0)
                    thermal_slope = thermal - prev_thermal
                    prev_thermal = thermal

                    stability_index = max(0.0, 1.0 - (drift * 10 + (thermal / THERMAL_MAX) * 0.05))
                    print(f"🧠 [SQI] {eng.container.container_id} Drift={drift:.3f} | Thermal={thermal:.1f}°C | Power={power:.0f}W | Stability={stability_index:.3f}")

                    # 🎶 Measure harmonic coherence
                    coherence = measure_harmonic_coherence(eng)
                    print(f"🎶 Harmonic Coherence={coherence:.3f}")
                    eng.log_event(f"Harmonic Coherence={coherence:.3f}")

                    # 🔧 Auto-boost harmonics if coherence is too low
                    if coherence < 0.6:
                        new_gain = HyperdriveTuningConstants.HARMONIC_GAIN * 1.02
                        set_harmonic_gain(new_gain)
                        print(f"🎵 Auto-boosting harmonic gain: {new_gain:.4f}")

                    trace = {
                        "resonance": eng.resonance_filtered[-sqi_interval:],
                        "fields": eng.fields.copy(),
                        "thermal": thermal,
                        "power": power,
                        "stability_index": stability_index,
                        "exhaust": [e.get("impact_speed", 0) for e in eng.exhaust_log[-50:]],
                        "stage": stages[current_stage_idx],
                    }

                    analysis = eng.sqi_engine.analyze_trace(trace)
                    adjustments = eng.sqi_engine.recommend_adjustments(analysis)
                    if adjustments:
                        # ✅ Field Adjustments
                        if "fields" in adjustments:
                            for k, v in adjustments["fields"].items():
                                baseline = eng.fields.get(k, 1.0)
                                eng.fields[k] = baseline * max(0.9, min(1.1, v))

                        # ✅ Harmonic Constants
                        if "harmonic_gain" in adjustments: set_harmonic_gain(adjustments["harmonic_gain"])
                        if "harmonic_decay" in adjustments: set_decay_rate(adjustments["harmonic_decay"])
                        if "damping_factor" in adjustments: set_damping_factor(adjustments["damping_factor"])
                        if "drift_threshold" in adjustments: set_resonance_threshold(adjustments["drift_threshold"])

                        # ✅ Persist updated constants
                        save_runtime_constants({
                            "harmonic_gain": adjustments.get("harmonic_gain", HyperdriveTuningConstants.HARMONIC_GAIN),
                            "harmonic_decay": adjustments.get("harmonic_decay", HyperdriveTuningConstants.DECAY_RATE),
                            "damping_factor": adjustments.get("damping_factor", HyperdriveTuningConstants.DAMPING_FACTOR),
                            "drift_threshold": adjustments.get("drift_threshold", RESONANCE_DRIFT_THRESHOLD),
                        })
                            # 🔄 Apply SQI adjustments instantly to HyperdriveTuningConstants
                        HyperdriveTuningConstants.apply_sqi_adjustments({
                            "harmonic_gain": adjustments.get("harmonic_gain", HyperdriveTuningConstants.HARMONIC_GAIN),
                            "harmonic_decay": adjustments.get("harmonic_decay", HyperdriveTuningConstants.DECAY_RATE),
                            "damping_factor": adjustments.get("damping_factor", HyperdriveTuningConstants.DAMPING_FACTOR),
                            "drift_threshold": adjustments.get("drift_threshold", HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD),
                        })
                        print(f"🔄 HyperdriveTuningConstants updated live: {adjustments}")

                        # ✅ Tick Rate & ECU Loop (every 30s)
                        if tick_counter % (30 * int(1 / ecu_loop_time)) == 0:
                            if "tick_rate" in adjustments:
                                tick_rate = max(5_000, min(20_000, adjustments["tick_rate"]))
                                eng.tick_rate = tick_rate
                            if "ecu_loop_time" in adjustments:
                                ecu_loop_time = max(0.005, min(0.02, adjustments["ecu_loop_time"]))
                                eng.ecu_loop_time = ecu_loop_time

                        # ✅ Particle Injector Scaling
                        if hasattr(eng, "injector"):
                            if "particle_density" in adjustments:
                                eng.injector.set_particle_density(adjustments["particle_density"])
                            if "particle_decay" in adjustments:
                                eng.injector.set_particle_decay(adjustments["particle_decay"])
                            if "pulse_strength" in adjustments:
                                eng.injector.set_pulse_strength(adjustments["pulse_strength"])
                        else:
                            if "particle_density" in adjustments:
                                eng.particle_density = max(0.5, min(2.0, adjustments["particle_density"]))
                            if "particle_decay" in adjustments:
                                eng.particle_decay = max(0.1, min(1.0, adjustments["particle_decay"]))

                        # ✅ Drift Compensation Scaling
                        if "drift_compensation" in adjustments:
                            drift_compensation = max(0.05, min(0.5, adjustments["drift_compensation"]))
                            eng.sqi_engine.drift_compensation = drift_compensation

                    # ✅ Predictive PI Surge Smoothing
                    if check_warp_pi(eng, threshold=WARP_PI_THRESHOLD * 0.98):
                        set_damping_factor(HyperdriveTuningConstants.DAMPING_FACTOR * 1.02)
                        eng.log_event("🔮 SQI: PI surge detected → Pre-lock damping boost applied.")

                    # ✅ Thermal & Power Enforcement
                    if thermal_slope > THERMAL_SLOPE_MAX or thermal > THERMAL_MAX * 0.95 or power > POWER_MAX * 0.95:
                        eng.particle_density *= 0.98
                        set_harmonic_gain(HyperdriveTuningConstants.HARMONIC_GAIN * 0.98)
                        eng.log_event("⚠ SQI Safety: Thermal/Power near limit or slope spike → Auto-throttle engaged")
                        print(f"🔥 [SQI] Auto-throttle: Density={eng.particle_density:.3f}, Harmonic Gain={HyperdriveTuningConstants.HARMONIC_GAIN:.3f}")

                    # ✅ Runaway Drift Failsafe
                    if stability_index < STABILITY_INDEX_MIN:
                        eng.particle_density *= 0.95
                        set_damping_factor(HyperdriveTuningConstants.DAMPING_FACTOR * 1.05)
                        eng.log_event("🛑 SQI: Stability drop detected → Emergency rollback applied")

        # =============================
        # Particle Velocity Clamp
        # =============================
        HyperdriveTuningConstants.clamp_particle_velocity(engine_a.particles)
        if engine_b:
            HyperdriveTuningConstants.clamp_particle_velocity(engine_b.particles)

        # =============================
        # Warp PI Milestone Detection
        # =============================
        if tick_counter % 500 == 0:
            if check_warp_pi(engine_a, threshold=WARP_PI_THRESHOLD):
                save_idle_state(engine_a, label="warp_milestone_snapshot")
                break

        # ✅ Particle velocity safety enforcement
        HyperdriveTuningConstants.enforce_particle_safety(engine_a)
        if engine_b:
            HyperdriveTuningConstants.enforce_particle_safety(engine_b)

        # =============================
        # Telemetry Logging (every 500 ticks)
        # =============================
        if tick_counter % 500 == 0:
            delta_fields = {k: v for k, v in engine_a.fields.items()} if not prev_fields else {
                k: v for k, v in engine_a.fields.items() if abs(v - prev_fields.get(k, v)) > 0.01
            }
            prev_fields = engine_a.fields.copy()

            telemetry = {
                "tick": tick_counter,
                "stage": stages[current_stage_idx],
                "particles_a": len(engine_a.particles),
                "resonance_a": engine_a.resonance_phase,
                "drift_a": drift_a,
                "particles_b": len(engine_b.particles) if engine_b else None,
                "resonance_b": engine_b.resonance_phase if engine_b else None,
                "delta_fields": delta_fields,
                "tick_rate": tick_rate,
                "ecu_loop_time": ecu_loop_time,
                "thermal": getattr(engine_a, "thermal_load", 0.0),
                "power": getattr(engine_a, "power_draw", 0.0),
                "stability_index": stability_index,
                "timestamp": datetime.utcnow().isoformat()
            }
            logger.log(telemetry)

            drift_b_display = f"{drift_b:.4f}" if drift_b is not None else "N/A"
            print(f"📊 ECU Tick={tick_counter} | Drift A={drift_a:.4f} ({drift_trend}) | Drift B={drift_b_display}")

        # =============================
        # Segment Logs
        # =============================
        if tick_counter % segment_size == 0 and tick_counter > 0:
            if hasattr(logger, "rotate_segment"):
                logger.rotate_segment()
            elif hasattr(logger, "_rotate_segment"):
                logger._rotate_segment()  # fallback to private method

        time.sleep(ecu_loop_time)

    logger.close()
    print(f"✅ ECU Runtime Loop Complete. Logs stored in: {logger.log_dir}")