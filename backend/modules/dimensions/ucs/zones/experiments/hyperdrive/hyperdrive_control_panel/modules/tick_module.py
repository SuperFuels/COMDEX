# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/tick_module.py

import time
import math
from copy import deepcopy
from datetime import datetime
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import SQIReasoningEngine
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.dc_io import DCContainerIO
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants


def tick(engine):
    """
    🔄 Modular Hyperdrive Tick:
    - Executes resonance, SQI reasoning, and control-panel-driven adjustments in real-time.
    - Supports SQI auto-tuning, particle physics, harmonic feedback, and graph logging.
    """
    dt = time.time() - engine.last_update
    if dt < engine.tick_delay:
        return

    engine.last_update = time.time()
    engine.tick_count += 1

    # =========================
    # 🧬 PARTICLE INJECTION & SEEDING
    # =========================
    if hasattr(engine, "intake_rate") and engine.intake_rate > 0:
        for _ in range(engine.intake_rate):
            engine.inject_proton()

    if len(engine.particles) < 200:
        print(f"⚠ Low particle count ({len(engine.particles)}). Injecting 50 baseline protons.")
        for _ in range(50):
            engine.inject_proton()

    # =========================
    # 🛑 TICK LIMIT SAFEGUARD
    # =========================
    if engine.tick_limit and engine.tick_count >= engine.tick_limit:
        print("🛑 Tick limit reached. Auto-collapsing engine.")
        engine.collapse()
        return

    # =========================
    # ⚠ INSTABILITY CHECK
    # =========================
    if engine._check_instability():
        return

    # =========================
    # 🎯 RESONANCE UPDATE
    # =========================
    feedback_voltage = engine.field_bridge.get_feedback_voltage() or 0.0
    engine.resonance_phase = (
        engine.resonance_phase +
        (engine.fields["wave_frequency"] - feedback_voltage * engine.damping_factor) * dt
    ) * engine.decay_rate

    engine.resonance_log.append(engine.resonance_phase)
    engine.resonance_filtered.append(
        sum(engine.resonance_log[-10:]) / min(len(engine.resonance_log), 10)
    )

    # 📈 Telemetry Logging Hook
    if hasattr(engine, "_log_graph_snapshot"):
        engine._log_graph_snapshot()

    # Drift Calculation
    drift = max(engine.resonance_filtered[-20:], default=0) - min(engine.resonance_filtered[-20:], default=0)
    print(f"📊 Tick={engine.tick_count} | Resonance={engine.resonance_phase:.4f} | Drift={drift:.4f} | Particles={len(engine.particles)}")

    # =========================
    # 🔬 PARTICLE PHYSICS UPDATE
    # =========================
    _update_particles(engine, dt)

    # =========================
    # 🫀 SQI PULSE + LOCK
    # =========================
    _pulse_detection(engine, drift)

    # =========================
    # 🔧 INLINE SQI AUTOTUNE
    # =========================
    _sqi_correction(engine)

    # =========================
    # 🎛 CONTROL PANEL HOOK (REALTIME SQI)
    # =========================
    if hasattr(engine, "sqi_controller"):
        engine.sqi_controller._sync_and_damp()

    # =========================
    # 🚀 STAGE ADVANCEMENT
    # =========================
    _stage_advance(engine)


def _update_particles(engine, dt):
    """Particle dynamics update."""
    for p in engine.particles:
        if not isinstance(p, dict):
            continue
        p.setdefault("charge", 1.0)
        p.setdefault("density", 1.0)
        p.setdefault("vx", 0.0); p.setdefault("vy", 0.0); p.setdefault("vz", 0.0)
        p.setdefault("x", 0.0); p.setdefault("y", 0.0); p.setdefault("z", 0.0)
        p.setdefault("mass", 1.0)

        gx, gy, gz = engine._gravity_force(p)
        mx, my, mz = engine._magnetic_force(p)
        wx, wy, wz = engine._wave_push(p)

        p["vx"] += (gx + mx + wx) * dt
        p["vy"] += (gy + my + wy) * dt
        p["vz"] += (gz + mz + wz) * dt

        speed = math.sqrt(p["vx"] ** 2 + p["vy"] ** 2 + p["vz"] ** 2)
        p["velocity_delta"] = speed - p.get("last_speed", 0)
        p["last_speed"] = speed

        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        p["z"] += p["vz"] * dt


def _pulse_detection(engine, drift):
    """
    Detect stability pulses and trigger SQI lock, harmonic resync,
    and control-panel preset sync when conditions are met.
    """
    if len(engine.resonance_filtered) >= 30 and engine.tick_count > 200:
        drift = max(engine.resonance_filtered[-30:]) - min(engine.resonance_filtered[-30:])
        if drift <= engine.stability_threshold:
            if not engine.sqi_enabled:
                print(f"🫀 Pulse detected: drift={drift:.3f}, enabling SQI...")
                engine.sqi_enabled = True
                engine.pending_sqi_ticks = 20
            else:
                print(f"🫀 Pulse stable: SQI active (drift={drift:.3f})")

            # ✅ SQI Lock State Integration
            if drift <= 0.05 and not getattr(engine, "sqi_locked", False):
                print(f"🔒 SQI LOCKED: Resonance={engine.resonance_phase:.4f} | Drift={drift:.4f}")
                engine.sqi_locked = True

                # Save idle state on lock
                if hasattr(engine, "save_idle_state"):
                    engine.save_idle_state(engine)
                    print(f"💾 SQI idle state saved at drift={drift:.4f}")

                # Harmonic Resync
                if hasattr(engine, "_resync_harmonics"):
                    engine._resync_harmonics()

                # Control Panel Preset Sync
                if hasattr(engine, "sqi_controller"):
                    try:
                        engine.sqi_controller.engage_feedback()
                        engine.sqi_controller.apply_preset(f"{int(drift * 100)}%")
                        print(f"🎛 SQI Controller preset applied at lock: drift={drift:.4f}")
                    except Exception as e:
                        print(f"⚠️ SQI Controller sync failed: {e}")


def _sqi_correction(engine):
    """Apply inline SQI field adjustments via reasoning engine."""
    if engine.sqi_enabled and engine.pending_sqi_ticks is not None:
        engine.pending_sqi_ticks -= 1
        if engine.pending_sqi_ticks <= 0:
            trace = {
                "resonance": engine.resonance_filtered[-30:],
                "fields": engine.fields.copy(),
                "exhaust": [e.get("impact_speed", 0) for e in engine.exhaust_log[-20:]],
                "stage": engine.stages[engine.current_stage],
            }
            analysis = engine.sqi_engine.analyze_trace(trace)
            adjustments = engine.sqi_engine.recommend_adjustments(analysis)
            if adjustments:
                engine.fields.update(adjustments)
                engine.log_event(f"🔧 [SQI-inline] Micro-adjust applied: {adjustments}")
            engine.pending_sqi_ticks = 50


def _stage_advance(engine):
    """Handle stage advancement and state export."""
    if engine._check_stage_stability():
        prev_stage = engine.stages[engine.current_stage]
        if engine.current_stage == len(engine.stages) - 1:
            print("🔒 SQI micro-tune: Final stage reached.")
        else:
            engine.advance_stage()

        new_stage = engine.stages[engine.current_stage]
        if new_stage != prev_stage:
            print(f"🚀 Stage advanced: {prev_stage} ➝ {new_stage}")
            engine._resync_harmonics()
            engine.last_dc_trace = f"data/qwave_logs/{new_stage}_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dc.json"
            DCContainerIO.export({
                "fields": deepcopy(engine.fields),
                "glyphs": [],
                "timestamp": datetime.utcnow().isoformat(),
                "stage": new_stage,
                "particles": len(engine.particles),
                "score": engine.best_score or 0.0,
                "sqi_enabled": engine.sqi_enabled
            }, engine.last_dc_trace, stage=new_stage, sqi_enabled=engine.sqi_enabled)