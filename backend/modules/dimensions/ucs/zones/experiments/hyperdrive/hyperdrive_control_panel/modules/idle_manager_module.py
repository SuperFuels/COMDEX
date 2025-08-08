# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/idle_manager_module.py

import os
import time
import json
import matplotlib.pyplot as plt
from datetime import datetime
from statistics import mean
import asyncio

# Core Hyperdrive Modules
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.drift_damping import apply_drift_damping
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_engine_sync import sync_twin_engines
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import pre_runtime_autopulse
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonics_module import update_harmonics
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence

# Paths
IDLE_STATE_PATH = "data/hyperdrive_idle_state.json"
IGNITION_TRACE_DIR = "data/qwave_logs/ignition_traces"
os.makedirs(IGNITION_TRACE_DIR, exist_ok=True)


# ==========================
# IGNITION TO IDLE
# ==========================
def ignition_to_idle(engine, sqi=None, duration=60, fuel_rate=3, initial_particles=200,
                     slowmode=False, engine_b=None):
    """
    Ignites engine and stabilizes resonance into idle state with:
    - Detailed ignition trace logging
    - Dual-engine SQI sync support
    - Harmonic autopulse stabilization
    """
    name = getattr(engine, "name", "engine")
    print(f"\n🚀 Ignition sequence initiated for {name}...")
    engine.log_event(f"🔥 Ignition sequence started for {name}.")

    # Initial particle seeding
    print(f"💠 Seeding {initial_particles} ignition particles...")
    injector = engine.injectors[0] if hasattr(engine, "injectors") and engine.injectors else None
    for _ in range(initial_particles):
        if injector:
            injector.multi_compress_and_fire(engine)
        elif hasattr(engine, "inject_proton"):
            engine.inject_proton()
        if hasattr(engine, "_inject_harmonics"):
            engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)
    engine.log_event(f"💠 Seeded {initial_particles} ignition particles.")

    # 🔧 Harmonic pre-pulse stabilization
    pre_runtime_autopulse(engine)

    ignition_trace = []
    resonance_trace = []

    # Main ignition loop
    start_time = time.time()
    while time.time() - start_time < duration:
        # ✅ Async-safe tick invocation for Engine A
        if hasattr(engine, "_single_tick"):
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(engine._single_tick())
            else:
                loop.run_until_complete(engine._single_tick())
        else:
            engine.tick()

        # Harmonic coherence and drift calculation
        coherence = measure_harmonic_coherence(engine)
        drift_window = engine.resonance_filtered[-30:]
        drift = (max(drift_window) - min(drift_window)) if drift_window else 0.0
        pulse_detected = drift <= (HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD * 0.5)

        # Record ignition trace tick
        avg_density = mean([p.get("density", 1.0) for p in engine.particles]) if engine.particles else 0.0
        ignition_trace.append({
            "tick": engine.tick_count,
            "resonance": engine.resonance_phase,
            "drift": drift,
            "pulse": pulse_detected,
            "fields": engine.fields.copy(),
            "particle_count": len(engine.particles),
            "avg_density": round(avg_density, 4)
        })
        resonance_trace.append(engine.resonance_phase)

        engine.log_event(f"Harmonic Coherence: {coherence:.3f} | Drift: {drift:.4f}")

        # Twin-engine sync (if Engine B provided)
        if engine_b:
            if hasattr(engine_b, "_single_tick"):
                if loop.is_running():
                    loop.create_task(engine_b._single_tick())
                else:
                    loop.run_until_complete(engine_b._single_tick())
            else:
                engine_b.tick()
            sync_twin_engines(engine, engine_b)

        # SQI stabilization
        if sqi and sqi.engine.sqi_enabled:
            engine._run_sqi_feedback()
            if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
                # ✅ FIXED: Pass engine instead of (drift, fields)
                apply_drift_damping(engine)

        # Fuel cycle
        if int((time.time() - start_time) * 10) % (fuel_rate * 10) == 0:
            if injector:
                injector.multi_compress_and_fire(engine)
            elif hasattr(engine, "inject_proton"):
                engine.inject_proton()

        if slowmode:
            time.sleep(0.1)

        # Idle lock detection
        if len(engine.resonance_filtered) > 50:
            drift_check = max(engine.resonance_filtered[-50:]) - min(engine.resonance_filtered[-50:])
            if drift_check < 0.01:
                print(f"✅ Idle stabilized for {name} (SQI drift lock).")
                engine._resync_harmonics()
                save_idle_state(engine)
                break

    # ✅ Export ignition + resonance trace logs
    export_traces(name, ignition_trace, resonance_trace)

    return True


# ==========================
# EXPORT TRACES (JSON + PLOT)
# ==========================
def export_traces(engine_name: str, ignition_trace, resonance_trace):
    """Exports ignition and resonance traces to JSON + PNG plots."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ign_path = os.path.join(IGNITION_TRACE_DIR, f"ignition_trace_{engine_name}_{ts}.json")
    res_path = os.path.join(IGNITION_TRACE_DIR, f"resonance_trace_{engine_name}_{ts}.json")
    ign_plot = os.path.join(IGNITION_TRACE_DIR, f"ignition_trace_{engine_name}_{ts}.png")
    res_plot = os.path.join(IGNITION_TRACE_DIR, f"resonance_trace_{engine_name}_{ts}.png")

    # ✅ Export JSON
    with open(ign_path, "w") as f:
        json.dump(ignition_trace, f, indent=4)
    with open(res_path, "w") as f:
        json.dump(resonance_trace, f, indent=4)

    print(f"📊 Ignition trace saved → {ign_path}")
    print(f"📈 Resonance trace saved → {res_path}")

    # ✅ Plot Ignition Trace (Resonance, Drift, Threshold)
    ticks = [entry["tick"] for entry in ignition_trace]
    resonance = [entry["resonance"] for entry in ignition_trace]
    drift = [entry["drift"] for entry in ignition_trace]
    drift_threshold = [HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD] * len(ticks)

    plt.figure(figsize=(10, 6))
    plt.plot(ticks, resonance, label="Resonance Phase", color="cyan")
    plt.plot(ticks, drift, label="Drift", color="orange")
    plt.plot(ticks, drift_threshold, label="Drift Threshold", linestyle="--", color="green")
    plt.xlabel("Tick")
    plt.ylabel("Value")
    plt.title(f"Ignition Trace: Engine {engine_name}")
    plt.legend()
    plt.grid(True)
    plt.savefig(ign_plot)
    plt.close()
    print(f"📉 Ignition graph saved → {ign_plot}")

    # ✅ Plot Resonance Trace (Raw Resonance)
    plt.figure(figsize=(10, 4))
    plt.plot(resonance_trace, color="magenta")
    plt.xlabel("Tick")
    plt.ylabel("Resonance")
    plt.title(f"Resonance Trace: Engine {engine_name}")
    plt.grid(True)
    plt.savefig(res_plot)
    plt.close()
    print(f"📈 Resonance graph saved → {res_plot}")


# ==========================
# SAVE & LOAD IDLE STATE
# ==========================
def save_idle_state(engine, label="idle_state"):
    snapshot = {
        "fields": engine.fields,
        "resonance_phase": engine.resonance_phase,
        "particles": len(engine.particles),
        "timestamp": datetime.utcnow().isoformat(),
        "label": label,
    }
    os.makedirs(os.path.dirname(IDLE_STATE_PATH), exist_ok=True)
    with open(IDLE_STATE_PATH, "w") as f:
        json.dump(snapshot, f, indent=4)
    print(f"💾 Idle state saved → {IDLE_STATE_PATH}")
    engine.log_event(f"💾 Idle snapshot saved: {label}")


def load_idle_state(engine):
    if not os.path.exists(IDLE_STATE_PATH):
        raise FileNotFoundError("❌ No idle state file found.")
    with open(IDLE_STATE_PATH, "r") as f:
        state = json.load(f)
    engine.fields.update(state["fields"])
    engine.resonance_phase = state.get("resonance_phase", engine.resonance_phase)
    print(f"📥 Idle state restored from {IDLE_STATE_PATH}")
    engine.log_event("📥 Idle state loaded from file.")