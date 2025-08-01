"""
🎛 QWave Engine Tuning Module
----------------------------
• Centralizes QWaveTuning constants, harmonic configs, and runtime ECU loop.
• Auto-loads last known idle state if available; falls back to baseline.
• CLI flags allow runtime overrides for harmonics, injectors, and field tuning.
• Fixes circular import with lazy `load_idle_state` import.
"""

import os
import json
import argparse
from datetime import datetime
from typing import List
from copy import deepcopy

BEST_STATE_PATH = "data/qwave_logs/qwave_best_idle.json"
LOG_DIR = "data/qwave_logs"

# -------------------------
# 🎛 QWAVE ENGINE TUNING BLOCK (RESET BASELINE)
# -------------------------
class QWaveTuning:
    ENABLE_COLLAPSE = True
    RESONANCE_DRIFT_THRESHOLD = 5.0
    INSTABILITY_HIT_LIMIT = 5
    PLASMA_DWELL_TICKS = 150

    HARMONICS: List[int] = [2, 3]
    HARMONIC_GAIN = 0.03
    HARMONIC_RATE_LIMIT = 0.002

    DAMPING_FACTOR = 0.15
    DECAY_RATE = 0.98

    SPEED_THRESHOLD = 500
    FIELD_THRESHOLD = 10.0

    BEST_IDLE_FIELDS = {
        "gravity": 2.0,
        "magnetism": 1.0,
        "wave_frequency": 0.5,
        "field_pressure": 1.0,
    }

    STAGE_CONFIGS = {
        "proton_injection": {"gravity": 1.2, "magnetism": 1.1, "wave_frequency": 1.0},
        "plasma_excitation": {"gravity": 1.5, "magnetism": 1.2, "wave_frequency": 1.0},
        "wave_focus": {"gravity": 2.0, "magnetism": 1.5, "wave_frequency": 1.0},
        "black_hole_compression": {"gravity": 3.0, "magnetism": 1.8, "wave_frequency": 1.1},
        "torus_field_loop": {"gravity": 2.5, "magnetism": 1.6, "wave_frequency": 1.0},
        "controlled_exhaust": {"gravity": 1.5, "magnetism": 1.0, "wave_frequency": 0.8},
    }

    @staticmethod
    def harmonic_for_stage(stage: str) -> float:
        return {
            "proton_injection": 0.8,
            "plasma_excitation": 1.0,
            "wave_focus": 1.2,
            "black_hole_compression": 1.3,
            "torus_field_loop": 1.1,
            "controlled_exhaust": 0.7,
        }.get(stage, 1.0)


# -------------------------
# ECU Runtime Loop (Twin Engine + SQI Phase-Aware Support)
# -------------------------
def ecu_runtime_loop(engine, ticks: int, sqi_interval: int, fuel_cycle: int = None,
                     disable_injectors: bool = False, harmonic_gain: float = None,
                     base_gravity: float = None, base_magnetism: float = None,
                     manual_stage: bool = False, engine_b=None, sqi_phase_aware: bool = False):
    from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.idle_manager import load_idle_state
    from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.engine_sync import sync_twin_engines, exhaust_to_intake

    print(f"🚦 ECU Runtime Loop Start: Target Ticks={ticks}")
    injector_interval = getattr(engine, "injector_interval", fuel_cycle or 4)

    # Auto-load idle or baseline for Engine A (and B if present)
    if os.path.exists(BEST_STATE_PATH):
        print(f"📥 Loading last idle state from {BEST_STATE_PATH}")
        load_idle_state(engine)
        if engine_b:
            print("📥 Loading idle state for Engine B...")
            load_idle_state(engine_b)
    else:
        print("⚠ No idle state found. Applying reset baseline fields.")
        engine.fields.update(QWaveTuning.BEST_IDLE_FIELDS)
        if engine_b:
            engine_b.fields.update(QWaveTuning.BEST_IDLE_FIELDS)

    # CLI overrides
    if base_gravity is not None:
        engine.fields["gravity"] = base_gravity
        if engine_b:
            engine_b.fields["gravity"] = base_gravity
    if base_magnetism is not None:
        engine.fields["magnetism"] = base_magnetism
        if engine_b:
            engine_b.fields["magnetism"] = base_magnetism
    if harmonic_gain is not None:
        QWaveTuning.HARMONIC_GAIN = harmonic_gain
        print(f"🎚 Harmonic gain set to {harmonic_gain}")

    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resonance_trace_path = f"{LOG_DIR}/resonance_trace_{engine.container.container_id}_{timestamp}.json"
    latest_resonance_path = f"{LOG_DIR}/resonance_trace_{engine.container.container_id}_latest.json"

    current_stage_idx = 0
    stages = list(QWaveTuning.STAGE_CONFIGS.keys())

    for tick in range(ticks):
        # Tick engines
        engine.tick()
        if engine_b:
            engine_b.tick()

        # Twin Engine Sync
        if engine_b and tick % 50 == 0:
            sync_twin_engines(engine, engine_b)
            exhaust_to_intake(engine, engine_b)
            if sqi_phase_aware:
                print(f"🔗 [SYNC] Engines A ↔ B aligned (SQI phase-aware drift sync).")

        # Stage transitions
        if tick % 500 == 0 and tick > 0:
            current_stage_idx = (current_stage_idx + 1) % len(stages)
            current_stage = stages[current_stage_idx]
            print(f"🔀 Stage Transition: {current_stage}")
            if manual_stage or not engine.sqi_enabled:
                engine.fields.update(QWaveTuning.STAGE_CONFIGS[current_stage])
                print(f"📡 Manual stage levers applied: {QWaveTuning.STAGE_CONFIGS[current_stage]}")
                if engine_b:
                    engine_b.fields.update(QWaveTuning.STAGE_CONFIGS[current_stage])

        # Proton injection and harmonics
        if tick % injector_interval == 0:
            engine.inject_proton()
            for _ in range(3):
                engine._inject_harmonics(QWaveTuning.HARMONICS)
            if not disable_injectors and engine.injectors:
                engine.injectors[tick % len(engine.injectors)].multi_compress_and_fire(engine)

            if engine_b:
                engine_b.inject_proton()
                for _ in range(3):
                    engine_b._inject_harmonics(QWaveTuning.HARMONICS)
                if not disable_injectors and engine_b.injectors:
                    engine_b.injectors[tick % len(engine_b.injectors)].multi_compress_and_fire(engine_b)

        # SQI stage modulation per engine
        if tick % sqi_interval == 0 and tick > 0:
            for eng in ([engine] + ([engine_b] if engine_b else [])):
                if eng.sqi_enabled:
                    drift = max(eng.resonance_filtered[-30:], default=0) - min(eng.resonance_filtered[-30:], default=0)
                    print(f"🧠 [SQI] {eng.container.container_id} Drift={drift:.3f}")
                    trace = {
                        "resonance": eng.resonance_filtered[-sqi_interval:],
                        "fields": eng.fields.copy(),
                        "exhaust": [e.get("impact_speed", 0) for e in eng.exhaust_log[-50:]],
                    }
                    adjustments = eng.sqi_engine.recommend_adjustments(eng.sqi_engine.analyze_trace(trace))
                    if adjustments:
                        for k, v in adjustments.items():
                            baseline = eng.fields.get(k, 1.0)
                            eng.fields[k] = baseline * max(0.9, min(1.1, v))  # ±10% clamp
                        print(f"🔧 [SQI] Adjustments Applied: {eng.fields}")
                else:
                    print(f"🛑 [SQI] Disabled for {eng.container.container_id}: Skipping corrections.")

        # Velocity clamp
        def clamp_velocities(particles):
            for p in particles:
                if isinstance(p, dict):
                    max_vel = 50.0
                    p["vx"] = max(min(p.get("vx", 0), max_vel), -max_vel)
                    p["vy"] = max(min(p.get("vy", 0), max_vel), -max_vel)
                    p["vz"] = max(min(p.get("vz", 0), max_vel), -max_vel)
        clamp_velocities(engine.particles)
        if engine_b:
            clamp_velocities(engine_b.particles)

        # Logging
        if tick % 100 == 0:
            drift_a = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)
            log_msg = f"📊 TICK={tick} | Stage={stages[current_stage_idx]} | Drift A={drift_a:.4f}"
            if engine_b:
                drift_b = max(engine_b.resonance_filtered[-30:], default=0) - min(engine_b.resonance_filtered[-30:], default=0)
                log_msg += f" | Drift B={drift_b:.4f}"
            print(log_msg)

        # Resonance trace exports
        if tick % 200 == 0:
            with open(resonance_trace_path, "w") as f:
                json.dump(engine.resonance_filtered, f, indent=2)
            with open(latest_resonance_path, "w") as f:
                json.dump(engine.resonance_filtered, f, indent=2)

        if tick % 500 == 0 and hasattr(engine, "_export_best_state"):
            engine._export_best_state()

    print("✅ ECU Runtime Loop Complete.")
    if hasattr(engine, "_export_best_state"):
        engine._export_best_state()
    with open(resonance_trace_path, "w") as f:
        json.dump(engine.resonance_filtered, f, indent=2)
    with open(latest_resonance_path, "w") as f:
        json.dump(engine.resonance_filtered, f, indent=2)
    print(f"📈 Resonance trace exported: {resonance_trace_path} (latest: {latest_resonance_path})")

# -------------------------
# CLI Entry
# -------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QWave ECU Runtime Tuning")
    parser.add_argument("--ticks", type=int, default=2000)
    parser.add_argument("--sqi", type=int, default=50)
    parser.add_argument("--fuel", type=int, default=4)
    parser.add_argument("--disable-injectors", action="store_true")
    parser.add_argument("--harmonic-gain", type=float)
    parser.add_argument("--gravity", type=float)
    parser.add_argument("--magnetism", type=float)
    parser.add_argument("--pulse-seek", action="store_true")
    parser.add_argument("--manual-stage", action="store_true", help="Force manual stage levers.")
    parser.add_argument("--enable-sqi", action="store_true", help="Enable SQI-driven modulation.")
    args = parser.parse_args()

    from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.supercontainer_engine import SupercontainerEngine
    from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer
    from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.tesseract_injector import TesseractInjector, CompressionChamber
    from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.idle_manager import ignition_to_idle

    def create_engine(name="engine-A", gravity=1.0, magnetism=1.0, wave_frequency=1.0, injector_interval=5):
        container = SymbolicExpansionContainer(container_id=name)
        engine = SupercontainerEngine(container=container, safe_mode=True, stage_lock=4, virtual_absorber=True)
        engine.injectors = [TesseractInjector(i, phase_offset=i * 3) for i in range(4)]
        engine.chambers = [CompressionChamber(i, compression_factor=1.3) for i in range(4)]
        engine.injector_interval = injector_interval
        engine.fields.update({"gravity": gravity, "magnetism": magnetism, "wave_frequency": wave_frequency})
        engine.sqi_enabled = args.enable_sqi
        return engine

    print("⚙ Initializing engine with ignition pre-sequence...")
    engine = create_engine(args.gravity or 1.0, args.magnetism or 1.0, wave_frequency=1.0, injector_interval=args.fuel)

    pulse_ok = ignition_to_idle(engine, duration=60, fuel_rate=args.fuel, initial_particles=200)
    if not pulse_ok:
        print("⚠ Pulse lock not achieved. Proceeding with ECU loop using last idle or baseline.")

    if args.pulse_seek:
        print("🔍 Pulse-seek enabled.")
        engine.fields.update({
            "gravity": args.gravity or 1.0,
            "magnetism": args.magnetism or 1.0,
            "wave_frequency": 1.0
        })
        QWaveTuning.HARMONIC_GAIN = 0.04
        print(f"⚙ Pulse baseline: {engine.fields}")

    ecu_runtime_loop(
        engine,
        ticks=args.ticks,
        sqi_interval=args.sqi,
        fuel_cycle=args.fuel,
        disable_injectors=args.disable_injectors,
        harmonic_gain=args.harmonic_gain,
        base_gravity=args.gravity,
        base_magnetism=args.magnetism,
        manual_stage=args.manual_stage
    )

# -------------------------
# 🔥 QWave Auto-Tuner (Enhanced with Preheat)
# -------------------------
class QWaveAutoTuner:
    def __init__(self, engine):
        self.engine = engine
        self.sqi_cooldown = 0

    def tune(self, iterations=50):
        # 🔥 PREHEAT PHASE: Run baseline ticks before analysis
        print("🔥 Preheating engine for 50 baseline ticks...")
        for _ in range(50):  
            if hasattr(self.engine, "tick"):
                self.engine.tick()
            elif hasattr(self.engine, "run_simulation"):
                self.engine.run_simulation(duration=1)

        # Now run SQI-aware tuning
        for i in range(iterations):
            print(f"\n🔄 Auto-Tune Iteration {i+1}/{iterations}")
            self.engine.tick()

            drift = self._get_current_drift()
            stability = self._evaluate_stability()

            print(f"🔎 Drift={drift:.4f} | Stability={stability:.4f}")

            if self.sqi_cooldown == 0 and getattr(self.engine, "sqi_enabled", False) and drift > 0.05:
                print(f"⚠ SQI correction triggered (Drift={drift:.4f})")
                self.engine._run_sqi_feedback()
                self.sqi_cooldown = 3
            else:
                print(f"✅ SQI skipped (Cooldown={self.sqi_cooldown})")

            if stability >= 0.95 and self.engine.tick_count > 200:  
                print(f"🫀 Pulse detected: Engine stable after warm-up (Score={stability:.3f})")
                self._generate_report()
                self._export_final_snapshot()
                break

            if self.sqi_cooldown > 0:
                self.sqi_cooldown -= 1

            stability = self._evaluate_stability()
            print(f"📊 Stability Score: {stability:.3f}")

            if stability >= 0.9:
                print(f"🫀 Pulse detected: Engine resonance stable (Score={stability:.3f})")

            if stability >= 0.95:
                print("✅ Stability target reached. Auto-tuning complete.")
                self._generate_report()
                self._export_final_snapshot()
                break

            if self.sqi_cooldown > 0:
                self.sqi_cooldown -= 1

    def _evaluate_stability(self) -> float:
        if not self.engine.resonance_filtered:
            return 0.0
        window = self.engine.resonance_filtered[-20:]
        drift = max(window) - min(window)
        stability_score = max(0.0, 1.0 - min(drift / 10.0, 1.0))
        if getattr(self.engine, "last_sqi_adjustments", None):
            stability_score = min(1.0, stability_score + 0.05)
        return stability_score

    def _get_current_drift(self) -> float:
        if not self.engine.resonance_filtered:
            return 0.0
        window = self.engine.resonance_filtered[-10:]
        return max(window) - min(window)

    def _generate_report(self):
        print("\n📊 === QWave Auto-Tune Report ===")
        print(f"🔧 Final Fields: {json.dumps(self.engine.fields, indent=2)}")
        print(f"🎯 Best Score: {self.engine.best_score:.4f}" if self.engine.best_score else "🎯 Best Score: N/A")
        print(f"📡 Particles: {len(self.engine.particles)}")
        print(f"🎶 Final Stage: {self.engine.stages[self.engine.current_stage]}")
        print(f"⚛ SQI Enabled: {self.engine.sqi_enabled}")

        if self.engine.resonance_filtered:
            drift = max(self.engine.resonance_filtered[-50:]) - min(self.engine.resonance_filtered[-50:])
            print(f"📈 Final Drift: {drift:.6f}")

        trace_path = os.path.join(self.engine.LOG_DIR, f"resonance_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(trace_path, "w") as f:
            json.dump(self.engine.resonance_filtered[-200:], f, indent=2)
        print(f"📑 Resonance trace saved → {trace_path}")
        print("=====================================\n")

    def _export_final_snapshot(self):
        os.makedirs("data/qwave_logs", exist_ok=True)
        report_path = f"data/qwave_logs/final_tuning_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dc.json"

        snapshot = {
            "fields": deepcopy(self.engine.fields),
            "glyphs": [],
            "timestamp": datetime.utcnow().isoformat(),
            "stage": self.engine.stages[self.engine.current_stage],
            "particles": len(self.engine.particles),
            "score": self.engine.best_score if self.engine.best_score else 0.0,
            "sqi_enabled": self.engine.sqi_enabled
        }

        with open(report_path, "w") as f:
            json.dump(snapshot, f, indent=2)

        print(f"📦 Final tuning snapshot exported → {report_path}")