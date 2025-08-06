"""
Tick Orchestrator:
Centralized tick controller that delegates engine updates to modular subsystems.
"""

import time
from datetime import datetime

# Modular subsystem imports
from .physics_module import PhysicsModule
from .virtual_exhaust_module import ExhaustModule
from .harmonics_module import update_harmonics
from .sqi_module import SQIModule
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.pulse_module import tick_pulse_handler
from backend.modules.consciousness.awareness_engine import AwarenessEngine

# 🔁 Idle Manager Hook
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.idle_manager_module import save_idle_state

# 🌊 Drift Damping Integration
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.drift_damping import apply_drift_damping

# 📐 Tuning Constants for Auto-Profile Switching
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants

# ⚙️ Gear Shift Module Integration
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.gear_shift_module import auto_gear_sequence, gear_shift

# 🧩 Tesseract Injector Integration
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.tesseract_injector import TesseractInjector, CompressionChamber

# 🧮 State Manager Scoring Integration
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.state_manager_module import compute_score, export_best_state

# ✅ Stage Stability Module
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.stage_stability_module import check_stage_stability

# ⚠️ Instability Detection Module
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.instability_check_module import check_instability

# 💾 Runtime Persistence (import from ECU runtime file)
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.ecu_runtime_module import (
    ECUDriftRegulator,
    HyperdriveInstabilityMonitor,
)

# ✅ TICK ORCHESTRATOR MAIN ENTRY POINT
async def run_tick_orchestration(engine):
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.tick_module import tick

    # 🛑 Pre-tick instability check
    if check_instability(engine):
        engine.log_event("⚠️ Instability detected: Tick skipped for stabilization.")
        return

    # 🌊 Drift damping
    drift = ECUDriftRegulator(engine).apply()

    # 🧠 Awareness feedback
    if engine.awareness:
        try:
            engine.awareness.update_confidence(max(0.0, 1.0 - drift))
            engine.awareness.record_confidence(
                glyph="🎶",
                coord=f"stage:{engine.stages[engine.current_stage]}",
                container_id=getattr(engine.container, "id", "N/A"),
                tick=engine.tick_count,
                trigger_type="sqi_drift_feedback"
            )
            if drift > engine.sqi_engine.target_resonance_drift:
                engine.awareness.log_blindspot(
                    glyph="⚠",
                    coord=f"stage:{engine.stages[engine.current_stage]}",
                    container_id=getattr(engine.container, "id", "N/A"),
                    tick=engine.tick_count,
                    context="high_drift_blindspot"
                )
        except Exception as e:
            engine.log_event(f"⚠️ AwarenessEngine drift logging failed: {e}")

    # ✅ Core stateless tick
    tick(engine)

    # 🔗 Twin engine sync
    if engine.twin_engine:
        await engine.twin_engine._single_tick()

# ✅ Bound _single_tick variant
async def _single_tick(self):
    await run_tick_orchestration(self)

class TickOrchestrator:
    def __init__(self, engine, stage):
        self.engine = engine
        self.stage = stage  # ✅ Stage controller injected externally
        self.physics = PhysicsModule()
        self.exhaust = ExhaustModule()
        self.sqi = SQIModule(engine=engine)  # ✅ Engine passed into SQI module
        self.last_tick_time = time.time()
        self.tick_counter = 0
        self.last_stage = None  # Track last stage for profile switching

        # Awareness Engine Initialization (IGI Integration)
        if not hasattr(engine, "awareness"):
            self.engine.awareness = AwarenessEngine(container=getattr(engine, "container", None))

        # ♻ Load persisted harmonic constants on init
        runtime_constants = load_runtime_constants()
        if runtime_constants:
            print(f"♻ Restoring persisted harmonic constants: {runtime_constants}")
            HyperdriveTuningConstants.HARMONIC_GAIN = runtime_constants.get("harmonic_gain", HyperdriveTuningConstants.HARMONIC_GAIN)
            HyperdriveTuningConstants.DECAY_RATE = runtime_constants.get("harmonic_decay", HyperdriveTuningConstants.DECAY_RATE)
            HyperdriveTuningConstants.DAMPING_FACTOR = runtime_constants.get("damping_factor", HyperdriveTuningConstants.DAMPING_FACTOR)
            HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD = runtime_constants.get("drift_threshold", HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD)

    async def initialize(self, dt):
        """Async init hook to set up harmony state."""
        await update_harmonics(self.engine, dt)

    def tick(self):
        """Run one orchestrated tick cycle."""
        dt = time.time() - self.last_tick_time
        if dt < self.engine.tick_delay:
            return  # Enforce engine delay for safe timing

        self.last_tick_time = time.time()
        self.tick_counter += 1
        print(f"\n⚡ Tick {self.tick_counter} [{datetime.utcnow().isoformat()}]")

        # 🛑 Instability Pre-Check
        if check_instability(self.engine):
            print("⚠️ Instability detected: Tick halted or dampened for stabilization.")
            return

        # 1️⃣ Particle Physics Update
        self.physics.update(self.engine, dt)

        # 2️⃣ Injector & Compression Chamber Cycle
        self._injector_cycle()
        
        # 🔥 Engine Ignition
        if hasattr(self.engine, "ignite"):
            self.engine.ignite()

        # 3️⃣ Resonance + Harmonic Control
        self.harmonics.update_resonance(self.engine, dt)

        # 4️⃣ Exhaust Simulation & Feedback
        self.exhaust.simulate(self.engine)

        # 🧲 Particle Velocity Clamp (Primary + Dual Engine)
        HyperdriveTuningConstants.clamp_particle_velocity(self.engine.particles)
        if hasattr(self.stage, "engine_b") and self.stage.engine_b:
            HyperdriveTuningConstants.clamp_particle_velocity(self.stage.engine_b.particles)

        # 5️⃣ Pulse Detection (Stage Advancement + Gear Progression w/ Stability Gate)
        if tick_pulse_handler(self.engine):
            if check_stage_stability(self.engine, extended=True):  # ✅ Stability-gated stage advancement
                self.stage.advance(self.engine)
                self._auto_gear_progression()
            else:
                print("⚠️ Stage advancement skipped: stability criteria not met.")

        # 6️⃣ Auto-Apply Stage Profile Changes (Idle/Warp/Safe)
        self._auto_stage_profile()

        # 7️⃣ SQI Feedback (Drift Analysis + Micro-Adjustments)
        self.sqi.feedback()

        # -------------------------
        # 🎵 Auto Harmonic Injection (SQI-Aware)
        # -------------------------
        if self.tick_counter % getattr(self.sqi.sqi_engine, "interval", 200) == 0:
            if getattr(self.engine, "sqi_enabled", False) or getattr(self.engine, "sqi_locked", False):
                if hasattr(self.engine, "_inject_harmonics"):
                    self.engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)
                    self.engine.gain = HyperdriveTuningConstants.HARMONIC_GAIN
                    print("🎵 Auto harmonic injection applied (SQI active).")

            # 🔗 SQI Phase-Aware Sync (if twin engines exist)
            if hasattr(self.engine, "twin_engine") and self.engine.twin_engine:
                twin = self.engine.twin_engine
                if getattr(twin, "sqi_enabled", False) or getattr(twin, "sqi_locked", False):
                    if hasattr(twin, "_inject_harmonics"):
                        twin._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)
                        twin.gain = HyperdriveTuningConstants.HARMONIC_GAIN
                        print("🎵 Auto harmonic injection applied (Twin Engine).")

                # SQI Phase Sync Alignment
                from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_engine_sync import sync_twin_engines
                sync_twin_engines(self.engine, twin)
                print("🔗 SQI Phase Sync: Primary ↔ Twin aligned.")

        # 🌊 Drift Damping Hook
        drift = apply_drift_damping(self.engine)

        # Drift Trend Tracking
        if not hasattr(self, "_last_drift"):
            self._last_drift = None

        drift_trend = "—"
        if self._last_drift is not None:
            drift_trend = "↑" if drift > self._last_drift else "↓" if drift < self._last_drift else "→"
        self._last_drift = drift

        if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
            print(f"⚠ Drift spike detected: Drift={drift:.3f} ({drift_trend}) → SQI damping applied.")

        # ✅ Telemetry Snapshot (per tick)
        telemetry = {
            "tick": self.tick_counter,
            "stage": getattr(self.stage, "current_stage", "N/A"),
            "particles": len(self.engine.particles),
            "resonance": getattr(self.engine, "resonance_phase", 0.0),
            "drift": drift,
            "thermal": getattr(self.engine, "thermal_load", 0.0),
            "power": getattr(self.engine, "power_draw", 0.0),
            "timestamp": datetime.utcnow().isoformat()
        }
        if hasattr(self.engine, "logger"):
            self.engine.logger.log(telemetry)

        # 🚀 Warp PI Milestone Detection (every 250 ticks)
        if self.tick_counter % 250 == 0:
            # Extract exhaust-derived PI trend
            exhaust_pi = [
                e.get("impact_speed", 0)
                for e in getattr(self.engine, "exhaust_log", [])[-50:]
                if isinstance(e, dict) and "impact_speed" in e
            ]
            avg_exhaust_pi = sum(exhaust_pi) / max(1, len(exhaust_pi))

            # Warp PI validation
            warp_ready = check_warp_pi(
                self.engine,
                threshold=HyperdriveTuningConstants.WARP_PI_THRESHOLD,
                window=400,
                label=f"tick_pi_{self.tick_counter}"
            )

            if warp_ready:
                self.engine.log_event(
                    f"🚀 [TickOrchestrator] Warp PI milestone achieved! (PI ≥ {HyperdriveTuningConstants.WARP_PI_THRESHOLD:.2f})"
                )
                save_idle_state(self.engine, label="warp_pi_milestone")
                print("✅ Warp PI snapshot saved. Preparing for pre-warp sequence...")
                return  # Exit tick cycle early on warp milestone
            else:
                self.engine.log_event(
                    f"ℹ [TickOrchestrator] Warp PI not yet reached "
                    f"(avg exhaust PI={avg_exhaust_pi:.2f}, threshold={HyperdriveTuningConstants.WARP_PI_THRESHOLD})"
                )

            # 🔮 Pre-lock damping bump if PI is close (within 2% margin)
            if avg_exhaust_pi >= HyperdriveTuningConstants.WARP_PI_THRESHOLD * 0.98:
                new_damping = HyperdriveTuningConstants.DAMPING_FACTOR * 1.015
                self.set_damping_factor(new_damping)
                self.engine.log_event(f"🔮 PI pre-lock detected → Damping boosted ({new_damping:.4f})")

        # ✅ Particle velocity safety enforcement
        HyperdriveTuningConstants.enforce_particle_safety(self.engine)
        if hasattr(self.stage, "engine_b") and self.stage.engine_b:
            HyperdriveTuningConstants.enforce_particle_safety(self.stage.engine_b)

        # 📊 Telemetry Logging (every 500 ticks)
        if self.tick_counter % 500 == 0:
            if not hasattr(self, "_prev_fields"):
                self._prev_fields = {}

            delta_fields = {
                k: v for k, v in self.engine.fields.items()
            } if not self._prev_fields else {
                k: v for k, v in self.engine.fields.items()
                if abs(v - self._prev_fields.get(k, v)) > 0.01
            }
            self._prev_fields = self.engine.fields.copy()

            telemetry = {
                "tick": self.tick_counter,
                "stage": getattr(self.stage, "current_stage", "N/A"),
                "particles": len(self.engine.particles),
                "resonance": getattr(self.engine, "resonance_phase", 0.0),
                "drift": getattr(self, "_last_drift", 0.0),
                "delta_fields": delta_fields,
                "thermal": getattr(self.engine, "thermal_load", 0.0),
                "power": getattr(self.engine, "power_draw", 0.0),
                "timestamp": datetime.utcnow().isoformat(),
            }
            if hasattr(self.engine, "logger"):
                self.engine.logger.log(telemetry)
            print(f"📊 Tick={self.tick_counter} | Drift={telemetry['drift']:.4f}")

        # 📂 Log Segment Rotation (every segment_size ticks)
        segment_size = getattr(self.engine, "segment_size", 2000)
        if self.tick_counter % segment_size == 0 and self.tick_counter > 0:
            if hasattr(self.engine.logger, "rotate_segment"):
                self.engine.logger.rotate_segment()
            elif hasattr(self.engine.logger, "_rotate_segment"):
                self.engine.logger._rotate_segment()  # Fallback

        # 8️⃣ Idle State Auto-Save
        self._idle_manager_hook()

        # 9️⃣ Awareness Drift Confidence Hooks
        self._awareness_hooks(drift)

        # 🔟 Periodic Stability Scoring & Best State Export
        if self.tick_counter % 50 == 0:
            score = compute_score(self.engine)
            if score > (getattr(self.engine, "best_score", float("-inf"))):
                export_best_state(self.engine)

        # 🔟 Periodic Logging Snapshot
        if self.tick_counter % 100 == 0:
            print(f"📊 Snapshot: Drift={drift:.4f}, Particles={len(self.engine.particles)}")

    def _injector_cycle(self):
        """Fire injectors & chambers in sync with tick count."""
        if hasattr(self.engine, "injectors"):
            for injector in self.engine.injectors:
                injector.tick(self.engine, self.tick_counter)
                injector.sync_to_frequency(self.engine.fields.get("wave_frequency", 1.0))

        if hasattr(self.engine, "chambers"):
            for chamber in self.engine.chambers:
                particle = chamber.compress_and_release()
                if particle:
                    self.engine.particles.append(particle)

    # -------------------------
    # 🎛 Live Harmonic Tuners (with persistence)
    # -------------------------
    def set_harmonic_gain(self, value: float):
        HyperdriveTuningConstants.HARMONIC_GAIN = value
        self.engine.gain = value
        self.engine.log_event(f"🎵 Harmonic gain updated → {value:.4f}")
        self._persist_harmonic_constants()

    def set_decay_rate(self, value: float):
        HyperdriveTuningConstants.DECAY_RATE = value
        self.engine.decay_rate = value
        self.engine.log_event(f"🎼 Harmonic decay updated → {value:.4f}")
        self._persist_harmonic_constants()

    def set_damping_factor(self, value: float):
        HyperdriveTuningConstants.DAMPING_FACTOR = value
        self.engine.damping_factor = value
        self.engine.log_event(f"🛡 Damping factor updated → {value:.4f}")
        self._persist_harmonic_constants()

    def set_resonance_threshold(self, value: float):
        HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD = value
        self.engine.stability_threshold = value
        self.engine.log_event(f"🎯 Resonance drift threshold updated → {value:.4f}")
        self._persist_harmonic_constants()

    def _persist_harmonic_constants(self):
        save_runtime_constants({
            "harmonic_gain": HyperdriveTuningConstants.HARMONIC_GAIN,
            "harmonic_decay": HyperdriveTuningConstants.DECAY_RATE,
            "damping_factor": HyperdriveTuningConstants.DAMPING_FACTOR,
            "drift_threshold": HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD,
        })

    def run(self, max_ticks: int = 5000):
        while self.tick_counter < max_ticks:
            self.tick()

    def _idle_manager_hook(self):
        rf = getattr(self.engine, "resonance_filtered", [])
        if len(rf) >= 50:
            window = rf[-50:]
            drift = max(window) - min(window)
            if drift < 0.01:
                save_idle_state(self.engine, label=f"auto_idle_tick_{self.tick_counter}")
                export_best_state(self.engine)

    def _auto_stage_profile(self):
        current_stage = getattr(self.stage, "current_stage", None)
        if current_stage != self.last_stage:
            if current_stage and "warp" in str(current_stage).lower():
                HyperdriveTuningConstants.apply_profile("warp")
            elif current_stage and "idle" in str(current_stage).lower():
                HyperdriveTuningConstants.apply_profile("idle")
            elif current_stage and "safe" in str(current_stage).lower():
                HyperdriveTuningConstants.apply_profile("safe")
            self.last_stage = current_stage

    def _auto_gear_progression(self):
        stage_name = str(getattr(self.stage, "current_stage", "")).lower()
        if "g1" in stage_name or "g2" in stage_name or "g3" in stage_name:
            auto_gear_sequence(self.engine, sqi_controller=self.engine.sqi_controller)
        elif "warp_alignment" in stage_name:
            print("🚀 Warp alignment detected: syncing PI surge lock with G4.5 gear shift.")
            gear_shift(self.engine, "G4.5")

    def _awareness_hooks(self, drift):
        try:
            self.engine.awareness.update_confidence(max(0.0, 1.0 - drift))
            self.engine.awareness.record_confidence(
                glyph="🎶",
                coord=f"stage:{self.stage.current_stage if hasattr(self.stage, 'current_stage') else 'N/A'}",
                container_id=getattr(self.engine.container, "id", "N/A"),
                tick=self.tick_counter,
                trigger_type="sqi_drift_feedback"
            )
            if drift > self.sqi.sqi_engine.target_resonance_drift:
                self.engine.awareness.log_blindspot(
                    glyph="⚠",
                    coord=f"stage:{self.stage.current_stage if hasattr(self.stage, 'current_stage') else 'N/A'}",
                    container_id=getattr(self.engine.container, "id", "N/A"),
                    tick=self.tick_counter,
                    context="high_drift_blindspot"
                )
        except Exception as e:
            self.engine.log_event(f"⚠️ AwarenessEngine drift logging failed: {e}")

async def _single_tick(self):
    await run_tick_orchestration(self)