# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/virtual_exhaust_module.py

from datetime import datetime  # ✅ Added for timestamp logging
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_auto_tuner_module import HyperdriveAutoTuner
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger

def simulate_virtual_exhaust(engine):
    """
    Simulates exhaust events:
    - Harmonic coherence monitoring
    - Adaptive coil tuning
    - SQI drift + oscillation damp
    - Exhaust wave emission & auto harmonic injection
    """
    impacts = []

    for p in engine.particles[-100:]:
        # ==========================
        # Velocity clamp
        # ==========================
        vx, vy, vz = p.get("vx", 0), p.get("vy", 0), p.get("vz", 0)
        speed_sq = vx * vx + vy * vy + vz * vz
        if speed_sq > HyperdriveTuningConstants.MAX_PARTICLE_SPEED ** 2:
            scale = HyperdriveTuningConstants.MAX_PARTICLE_SPEED / (speed_sq ** 0.5)
            vx, vy, vz = vx * scale, vy * scale, vz * scale
            p["vx"], p["vy"], p["vz"] = vx, vy, vz

        # ==========================
        # Impact energy & log
        # ==========================
        speed = (vx * vx + vy * vy + vz * vz) ** 0.5
        energy = 0.5 * p["mass"] * speed ** 2
        impacts.append({"speed": round(speed, 3), "energy": round(energy, 3)})
        engine.exhaust_log.append({"tick": engine.tick_count, "impact_speed": speed, "energy": energy})

        # ==========================
        # Harmonic coherence measure
        # ==========================
        coherence = measure_harmonic_coherence(engine)
        if coherence < 0.5:
            print(f"🎼 Harmonic coherence low ({coherence:.3f}) → Injecting harmonics")
            engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)

        # ==========================
        # Adaptive coil tuning
        # ==========================
        adjustment = engine.field_bridge.auto_calibrate(target_voltage=1.0)
        if adjustment:
            recent_drift = abs(engine.resonance_filtered[-1] - engine.resonance_filtered[-5]) if len(engine.resonance_filtered) > 5 else 0
            if recent_drift > 0.8:
                adjustment *= 0.5
            print(f"🔧 Coil auto-tuned by {adjustment:+.2f}")

        # ==========================
        # SQI Drift Damp
        # ==========================
        if energy > 5.0:
            engine.fields["gravity"] = max(engine.fields["gravity"] - 0.02, 0.1)
            engine.fields["magnetism"] = max(engine.fields["magnetism"] - 0.01, 0.1)
            print(f"🫀 SQI Damp: High exhaust energy ({energy:.3f}) → Gravity/Magnetism reduced")

        # ==========================
        # SQI Oscillation Damp
        # ==========================
        if engine.sqi_enabled and len(engine.exhaust_log) > 10:
            last_exhaust = [e["impact_speed"] for e in engine.exhaust_log[-10:]]
            oscillation = max(last_exhaust) - min(last_exhaust)
            if oscillation > 50:
                engine.fields["wave_frequency"] *= 0.98
                print(f"🔧 [SQI-inline] Oscillation damp: wave_frequency → {engine.fields['wave_frequency']:.3f}")

        # ==========================
        # Exhaust Wave Emission
        # ==========================
        phase = engine.resonance_filtered[-1] if engine.resonance_filtered else 0
        engine.field_bridge.emit_exhaust_wave(phase, energy)

        # ==========================
        # Proton recycle (reset particle)
        # ==========================
        p.update({"x": 0.0, "y": 0.0, "z": 0.0, "vx": 0.0, "vy": 0.0, "vz": 0.0})

    # ==========================
    # Impact signature + tuner hook
    # ==========================
    if impacts:
        last_impact = impacts[-1]
        print(f"📡 Virtual Exhaust Impact: {last_impact}")
        recent_energies = [imp["energy"] for imp in impacts[-5:]]
        if len(recent_energies) >= 5 and max(recent_energies) - min(recent_energies) < 0.2:
            print("🫀 Pulse signature confirmed in exhaust oscillation → SQI tuning engaged")
            HyperdriveAutoTuner.dynamic_adjust(engine, measure_harmonic_coherence(engine))

    # ==========================
    # Log exhaust snapshot
    # ==========================
    TelemetryLogger(log_dir="data/qwave_logs").log({
        "tick": engine.tick_count,
        "harmonic_coherence": measure_harmonic_coherence(engine),
        "last_impact": impacts[-1] if impacts else None,
        "wave_frequency": engine.fields.get("wave_frequency", 0.0),
        "gravity": engine.fields.get("gravity", 0.0),
        "magnetism": engine.fields.get("magnetism", 0.0),
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Maintain graph snapshots
    engine._log_graph_snapshot()