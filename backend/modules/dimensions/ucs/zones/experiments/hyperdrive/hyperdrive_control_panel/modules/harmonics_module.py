"""
🎶 Harmonics Runtime Module
---------------------------
* Handles tick-time harmonic stability control.
* Integrates resonance, coherence, drift damping, and awareness.
* Uses measure_harmonic_coherence from harmonic_coherence_module.
"""

import asyncio
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence
from backend.modules.consciousness.awareness_engine import AwarenessEngine


# =========================
# 🎶 HARMONIC UPDATE (MAIN)
# =========================
async def update_harmonics(engine, dt):
    """
    Tick-time harmonic control:
    - Updates resonance
    - Measures coherence/drift
    - Applies stability/cooldown control
    - Runs drift damping and awareness feedback
    """
    # 🔧 Resonance update first (ensures filtered values are fresh)
    _update_resonance(engine, dt)

    # 🎵 Measure coherence & drift window
    coherence = measure_harmonic_coherence(engine)
    drift = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)

    # ✅ Stability tracking
    if coherence >= 1.0 and drift < 1e-4:
        engine._stability_counter = getattr(engine, "_stability_counter", 0) + 1
    else:
        engine._stability_counter = 0

    # ⏸ Cooldown entry
    if engine._stability_counter >= 10 and not getattr(engine, "_cooldown_active", False):
        engine._cooldown_active = True
        engine.log_event("✅ Harmonic equilibrium locked - entering cooldown.")
        asyncio.create_task(_reset_cooldown(engine))
        return coherence, drift

    # ⚠ Plateau perturbations (3 & 6 ticks in plateau)
    if engine._stability_counter in {3, 6}:
        engine.fields["wave_frequency"] *= 1.002
        engine.fields["magnetism"] *= 0.998
        engine.log_event("⚠ Stability plateau detected - injecting gentle perturbation.")

    # ⚠ Flatline breaker
    if coherence >= 1.0 and drift < 0.0001:
        engine.fields["wave_frequency"] *= 1.0005
        engine.log_event("⚠ Harmonic flatline detected -> micro-perturbation applied.")

    # 🌪 Drift damping
    _entropy_drift_damping(engine)

    # 🧠 Awareness feedback
    _update_awareness(engine, coherence)

    return coherence, drift


# =========================
# 🎶 RESONANCE UPDATE
# =========================
def _update_resonance(engine, dt):
    feedback_voltage = engine.field_bridge.get_feedback_voltage() or 0.0
    engine.resonance_phase = (
        engine.resonance_phase
        + (engine.fields["wave_frequency"] - feedback_voltage * engine.damping_factor) * dt
    ) * (engine.decay_rate * 0.999)  # ✅ micro-decay prevents lock-in

    # Update resonance logs
    engine.resonance_log.append(engine.resonance_phase)
    engine.resonance_filtered.append(
        sum(engine.resonance_log[-10:]) / min(len(engine.resonance_log), 10)
    )

    # Optional: HUD graph snapshot
    if hasattr(engine, "_log_graph_snapshot"):
        engine._log_graph_snapshot()


# =========================
# 🌪 ENTROPY DRIFT DAMPING
# =========================
def _entropy_drift_damping(engine):
    drift = abs(engine.fields.get("wave_frequency", 1.0) - 1.0)
    if drift > 0.1:
        for k in ["gravity", "magnetism", "wave_frequency", "field_pressure"]:
            engine.fields[k] += -0.015 * (engine.fields[k] - 1.0)
        engine.resonance_phase *= 0.95
        engine.log_event(f"🌪 Entropy drift corrected | Δ={drift:.3f}")


# =========================
# 🧠 AWARENESS INTEGRATION
# =========================
def _update_awareness(engine, coherence):
    try:
        if not hasattr(engine, "awareness"):
            engine.awareness = AwarenessEngine(container=engine.container)
        engine.awareness.update_confidence(coherence)
        engine.awareness.record_confidence(
            glyph="🎶",
            coord=f"stage:{engine.stages[engine.current_stage]}",
            container_id=engine.container.id,
            tick=engine.tick_count,
            trigger_type="coherence_update",
        )
        if coherence < 0.6:
            engine.awareness.log_blindspot(
                glyph="⚠",
                coord=f"stage:{engine.stages[engine.current_stage]}",
                container_id=engine.container.id,
                tick=engine.tick_count,
                context="low_coherence_blindspot",
            )
    except Exception as e:
        engine.log_event(f"⚠️ AwarenessEngine integration failed: {e}")


# =========================
# 🔄 COOLDOWN RESET
# =========================
async def _reset_cooldown(engine):
    await asyncio.sleep(2.0)  # Non-blocking wait
    engine._cooldown_active = False
    engine._stability_counter = 0
    engine.log_event("🔄 Cooldown expired - resuming normal tick flow.")