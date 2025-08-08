import random
from datetime import datetime
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_auto_tuner_module import HyperdriveAutoTuner
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence, inject_harmonics
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger

class ExhaustModule:
    """
    Handles Virtual Exhaust simulation:
    - Harmonic coherence monitoring & auto-injection
    - Adaptive coil tuning
    - SQI drift/oscillation damping
    - Particle Δv kicks and impact metrics
    - Telemetry logging + SQI tuning hooks
    """

    def __init__(self, log_dir: str = "data/qwave_logs"):
        self.logger = TelemetryLogger(log_dir=log_dir)

    def simulate(self, engine):
        """Run exhaust simulation for the given engine state."""
        impacts = []

        for p in engine.particles[-100:]:
            self._ensure_particle_integrity(p)
            self._clamp_velocity(p)

            # Calculate impact energy & log
            speed, energy = self._compute_energy(p)
            impacts.append({"speed": round(speed, 3), "energy": round(energy, 3)})
            engine.exhaust_log.append({"tick": engine.tick_count, "impact_speed": speed, "energy": energy})

            # Harmonic coherence check
            self._check_and_inject_harmonics(engine)

            # Adaptive coil tuning
            self._auto_tune_coils(engine)

            # SQI damping
            self._apply_sqi_damping(engine, energy)

            # Oscillation damp
            self._apply_oscillation_damp(engine)

            # Emit exhaust wave
            self._emit_exhaust_wave(engine, energy)

            # Proton recycle
            self._reset_particle(p)

        # Particle motion kick and SQI tuning hook
        if impacts:
            self._apply_particle_kick(engine, impacts[-1])
            self._check_sqi_signature(engine, impacts)

        # Log telemetry snapshot
        self._log_snapshot(engine, impacts)

    def _ensure_particle_integrity(self, p):
        p.setdefault("vx", 0.0)
        p.setdefault("vy", 0.0)
        p.setdefault("vz", 0.0)
        p.setdefault("x", 0.0)
        p.setdefault("y", 0.0)
        p.setdefault("z", 0.0)
        p.setdefault("mass", 1.0)
        p.setdefault("charge", 1.0)
        p.setdefault("density", 1.0)

    def _clamp_velocity(self, p):
        vx, vy, vz = p["vx"], p["vy"], p["vz"]
        speed_sq = vx * vx + vy * vy + vz * vz
        if speed_sq > HyperdriveTuningConstants.MAX_PARTICLE_SPEED ** 2:
            scale = HyperdriveTuningConstants.MAX_PARTICLE_SPEED / (speed_sq ** 0.5)
            p["vx"], p["vy"], p["vz"] = vx * scale, vy * scale, vz * scale

    def _compute_energy(self, p):
        speed = (p["vx"] ** 2 + p["vy"] ** 2 + p["vz"] ** 2) ** 0.5
        energy = 0.5 * p["mass"] * speed ** 2
        return speed, energy

    def _check_and_inject_harmonics(self, engine):
        coherence = measure_harmonic_coherence(engine)
        if coherence < 0.5:
            print(f"🎼 Harmonic coherence low ({coherence:.3f}) → Injecting harmonics")
            if hasattr(engine, "injectors") and hasattr(engine, "chambers"):
                inject_harmonics(engine, HyperdriveTuningConstants.HARMONIC_DEFAULTS)
            else:
                engine.log_event("⚠ Harmonic injection skipped: Missing injectors or chambers.")

    def _auto_tune_coils(self, engine):
        adjustment = engine.field_bridge.auto_calibrate(target_voltage=1.0)
        if adjustment:
            recent_drift = abs(engine.resonance_filtered[-1] - engine.resonance_filtered[-5]) if len(engine.resonance_filtered) > 5 else 0
            if recent_drift > 0.8:
                adjustment *= 0.5
            print(f"🔧 Coil auto-tuned by {adjustment:+.2f}")

    def _apply_sqi_damping(self, engine, energy):
        if energy > 5.0:
            engine.fields["gravity"] = max(engine.fields["gravity"] - 0.02, 0.1)
            engine.fields["magnetism"] = max(engine.fields["magnetism"] - 0.01, 0.1)
            print(f"🫀 SQI Damp: High exhaust energy ({energy:.3f}) → Gravity/Magnetism reduced")

    def _apply_oscillation_damp(self, engine):
        if engine.sqi_enabled and len(engine.exhaust_log) > 10:
            last_exhaust = [e["impact_speed"] for e in engine.exhaust_log[-10:] if "impact_speed" in e]
            oscillation = max(last_exhaust) - min(last_exhaust)
            if oscillation > 50:
                engine.fields["wave_frequency"] *= 0.98
                print(f"🔧 [SQI-inline] Oscillation damp: wave_frequency → {engine.fields['wave_frequency']:.3f}")

    def _emit_exhaust_wave(self, engine, energy):
        phase = engine.resonance_filtered[-1] if engine.resonance_filtered else 0
        engine.field_bridge.emit_exhaust_wave(phase, energy)

    def _reset_particle(self, p):
        p.update({"x": 0.0, "y": 0.0, "z": 0.0, "vx": 0.0, "vy": 0.0, "vz": 0.0})

    def _apply_particle_kick(self, engine, last_impact):
        impact_speed = last_impact["speed"]
        avg_impact = impact_speed * 0.5
        for p in engine.particles:
            p["vx"] += avg_impact * (0.5 - random.random())
            p["vy"] += avg_impact * (0.5 - random.random())
        engine.log_event(f"💨 Exhaust impact applied | Δv~{avg_impact:.5f} | PI={impact_speed:.2f}")
        print(f"📡 Virtual Exhaust Impact: {last_impact}")

    def _check_sqi_signature(self, engine, impacts):
        recent_energies = [imp["energy"] for imp in impacts[-5:] if "energy" in imp]
        if len(recent_energies) >= 5 and max(recent_energies) - min(recent_energies) < 0.2:
            print("🫀 Pulse signature confirmed in exhaust oscillation → SQI tuning engaged")
            HyperdriveAutoTuner.dynamic_adjust(engine, measure_harmonic_coherence(engine))

    def _log_snapshot(self, engine, impacts):
        self.logger.log({
            "tick": engine.tick_count,
            "harmonic_coherence": measure_harmonic_coherence(engine),
            "last_impact": impacts[-1] if impacts else None,
            "wave_frequency": engine.fields.get("wave_frequency", 0.0),
            "gravity": engine.fields.get("gravity", 0.0),
            "magnetism": engine.fields.get("magnetism", 0.0),
            "timestamp": datetime.utcnow().isoformat(),
        })
        if hasattr(engine, "_log_graph_snapshot"):
            engine._log_graph_snapshot()

# -------------------------
# 🛠 Virtual Exhaust Simulation (Standalone Helper)
# -------------------------
def simulate_virtual_exhaust(engine):
    """
    Simulates virtual exhaust to regulate particle flow, resonance drift,
    and maintain SQI harmonic balance. Delegated for HyperdriveEngine.
    """
    if not engine or not hasattr(engine, "particles"):
        print("⚠️ [simulate_virtual_exhaust] Engine missing particle system.")
        return

    print("💨 Simulating virtual exhaust...")

    # Apply exhaust effect to reduce excess particle density
    if len(engine.particles) > engine.max_particles:
        removed = len(engine.particles) - engine.max_particles
        engine.particles = engine.particles[:engine.max_particles]
        engine.log_event(f"💨 Exhaust vented {removed} particles to maintain stability.")

    # Minor harmonic correction during exhaust
    if hasattr(engine, "fields"):
        engine.fields["wave_frequency"] *= 0.999
        engine.fields["field_pressure"] *= 0.998

    # Log particle density and exhaust impact
    engine.exhaust_log.append({
        "tick": engine.tick_count,
        "particles": len(engine.particles),
        "resonance": getattr(engine, "resonance_phase", None)
    })

    print(f"✅ Virtual exhaust complete | Particles: {len(engine.particles)}")