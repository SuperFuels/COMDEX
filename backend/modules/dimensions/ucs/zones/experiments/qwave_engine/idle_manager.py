"""
🛠 Idle Manager Module
----------------------
* Manages ignition-to-idle stabilization with SQI feedback (toggle-aware).
* Handles saving/loading of idle resonance state for recovery.
* Captures ignition traces (resonance, drift, density) for diagnostics.
* Integrates particle injectors, compression chambers, and harmonic tuning.
* Provides auto-recovery by reloading last known good idle state if lock fails.

🔥 Features:
    * Ignition-to-idle stabilization loop with pulse detection.
    * SQI drift-based auto-correction (toggle-aware).
    * Safe density logging from particle history (last 10).
    * Auto-save & reload of idle state after collapse.
    * Logs ignition traces with resonance, drift, density, and particle counts.
    * Exports resonance traces, graphs, and best idle state.
"""

import os
import json
import time
import matplotlib.pyplot as plt
from datetime import datetime
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.supercontainer_engine import QWaveTuning

BEST_STATE_PATH = "data/qwave_logs/qwave_best_idle.json"
IGNITION_LOG_PATH = "data/qwave_logs/qwave_ignition_trace.json"

def save_idle_state(engine):
    """Save current engine state (fields + resonance + drift + particles) for future recovery."""
    state = {
        "timestamp": datetime.now().isoformat(),
        "fields": engine.fields,
        "resonance_phase": engine.resonance_phase,
        "drift": getattr(engine, "drift", 0.0),
        "particles": engine.particles,
        "sqi_locked": getattr(engine, "sqi_locked", False)
    }
    os.makedirs(os.path.dirname(BEST_STATE_PATH), exist_ok=True)
    with open(BEST_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
    print(f"💾 Idle state saved: {BEST_STATE_PATH}")


def load_idle_state(engine):
    """Reload the previously saved idle state (fields + resonance + drift + particles)."""
    if os.path.exists(BEST_STATE_PATH):
        with open(BEST_STATE_PATH, "r") as f:
            state = json.load(f)
        engine.fields.update(state.get("fields", {}))
        engine.resonance_phase = state.get("resonance_phase", 0.0)
        engine.drift = state.get("drift", 0.0)
        engine.particles = state.get("particles", [])
        engine.sqi_locked = state.get("sqi_locked", False)
        print(f"✅ Idle restored: Resonance={engine.resonance_phase:.4f} | Drift={engine.drift:.4f} | Particles={len(engine.particles)}")
        if engine.sqi_locked:
            print("🔒 SQI lock restored from idle state.")
    else:
        print("⚠ No saved idle state found. Skipping reload.")


def export_ignition_graph(log_data, engine_id):
    """Generate and save ignition graphs for resonance & drift trends."""
    ticks = [entry["tick"] for entry in log_data]
    resonance = [entry["resonance"] for entry in log_data]
    drift = [entry["drift"] for entry in log_data]

    plt.figure(figsize=(10, 6))
    plt.plot(ticks, resonance, label="Resonance Phase", color="cyan")
    plt.plot(ticks, drift, label="Drift", color="orange")
    plt.axhline(y=0.05, color="green", linestyle="--", label="Drift Threshold")
    plt.xlabel("Tick")
    plt.ylabel("Value")
    plt.title(f"Ignition Trace: Engine {engine_id}")
    plt.legend()
    plt.grid(True)
    graph_path = f"data/qwave_logs/ignition_graph_{engine_id}.png"
    plt.savefig(graph_path)
    plt.close()
    print(f"📈 Ignition graph exported: {graph_path}")


def ignition_to_idle(engine, duration=60, fuel_rate=3, initial_particles=200, slowmode=False):
    """
    Spin up engine ignition and stabilize resonance to idle pulse lock.
    Applies drift-based SQI corrections (toggle-aware) and logs ignition trace.
    """
    print(f"\n🔑 Ignition: Spooling engine '{engine.container.container_id}' to Idle...")

    # ✅ Load last known stable idle state (if exists)
    load_idle_state(engine)

    ignition_log, tick_counter, pulse_detected = [], 0, False
    stable_ticks = 0  # ✅ Initialize drift stability counter

    # Prime engine with particles
    for _ in range(initial_particles):
        engine.inject_proton()

    start_time = time.time()
    while time.time() - start_time < duration:
        engine.tick()
        tick_counter += 1

        # ✅ Drift must be calculated early in each loop iteration
        drift = max(engine.resonance_filtered[-20:], default=0) - min(engine.resonance_filtered[-20:], default=0)

        # ✅ SQI Lock Detection: Save idle state & exit early with drift stability
        if getattr(engine, "sqi_locked", False):
            if not pulse_detected:
                print("🔒 SQI lock detected during ignition. Saving idle state...")
                save_idle_state(engine)
                pulse_detected = True

            # Check for stable drift before exiting
            if drift < 0.06:
                stable_ticks += 1
                print(f"✅ SQI lock confirmed and drift stable for {stable_ticks} ticks.")
                if stable_ticks >= 5:  # Require 5 stable drift ticks before exit
                    print(f"🚀 Exiting ignition loop early after {stable_ticks} stable ticks.")
                    break
            else:
                stable_ticks = 0  # Reset if drift fluctuates

            if slowmode:
                print("🐢 Slowmode: SQI lock reached, holding stable...")
                time.sleep(1)

        # ✅ Injectors & Compression Chambers
        for injector in engine.injectors:
            injector.tick(engine, tick_counter)
        for chamber in engine.chambers:
            if chamber.load:
                compressed = chamber.compress_and_release()
                if compressed:
                    engine.particles.append(compressed)

        # ✅ Harmonics & Fuel Injection
        if engine.stages[engine.current_stage] in ["plasma_excitation", "wave_focus"]:
            engine._resync_harmonics()
        if tick_counter % fuel_rate == 0:
            engine.inject_proton()

        # ✅ Drift & SQI Toggle-Aware Corrections
        print(f"🔎 Resonance Phase={engine.resonance_phase:.4f} | Drift={drift:.4f}")

        if getattr(engine, "sqi_enabled", False):
            if drift > 0.08:
                engine.fields["gravity"] *= 1.005
                engine.fields["magnetism"] *= 1.003
                print(f"⚠ SQI auto-correction: gravity={engine.fields['gravity']:.3f}, magnetism={engine.fields['magnetism']:.3f}")
        else:
            if drift > 0.08:
                print("🛑 SQI disabled: Drift detected (gravity/magnetism unchanged).")

        # ✅ Drift dampener
        if drift > 0.12:
            engine.fields["gravity"] *= 0.995
            print(f"🛠 Drift dampener applied: gravity={engine.fields['gravity']:.3f}")

        # ✅ Pulse Detection
        if drift < 0.05 and engine.resonance_phase > 2.5:
            pulse_detected = True

        # ✅ Safe Density Logging
        valid_particles = [p for p in engine.particles[-10:] if isinstance(p, dict) and "density" in p]
        avg_density = sum(p.get("density", 1.0) for p in valid_particles) / max(1, len(valid_particles) or 1)

        # ✅ Log ignition trace
        ignition_log.append({
            "tick": tick_counter,
            "resonance": engine.resonance_phase,
            "drift": drift,
            "pulse": pulse_detected,
            "fields": engine.fields.copy(),
            "particle_count": len(engine.particles),
            "avg_density": avg_density
        })

        # ✅ Runtime scoring & best-state export (every 50 ticks)
        if tick_counter % 50 == 0:
            if hasattr(engine, "_compute_score"):
                score = engine._compute_score()
                print(f"🏆 Ignition Score: {score:.3f}")
            if hasattr(engine, "_export_best_state"):
                engine._export_best_state()

        # ✅ Periodic trace export & graph generation
        if tick_counter % 100 == 0:
            with open(f"data/qwave_logs/resonance_trace_{engine.container.container_id}.json", "w") as f:
                json.dump(engine.resonance_filtered, f, indent=2)
            print(f"📈 Resonance trace updated @tick {tick_counter}")
            export_ignition_graph(ignition_log, engine.container.container_id)

        if slowmode:
            time.sleep(0.05)

    # ✅ Export ignition trace & graph AFTER loop
    print(f"✅ Ignition complete after {tick_counter} ticks. SQI Locked: {pulse_detected}")
    trace_path = f"data/qwave_logs/qwave_ignition_trace_{engine.container.container_id}.json"
    with open(trace_path, "w") as f:
        json.dump(ignition_log, f, indent=2)
    print(f"📄 Ignition trace saved: {trace_path}")

    # ✅ Final resonance trace export & graph
    with open(f"data/qwave_logs/resonance_trace_{engine.container.container_id}.json", "w") as f:
        json.dump(engine.resonance_filtered, f, indent=2)
    print(f"📈 Resonance trace exported for {engine.container.container_id}")

    export_ignition_graph(ignition_log, engine.container.container_id)
    return pulse_detected