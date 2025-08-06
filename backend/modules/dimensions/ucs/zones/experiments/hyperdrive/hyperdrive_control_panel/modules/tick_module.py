# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/tick_module.py

import time
import math
import asyncio
from typing import Dict, Any
from copy import deepcopy
from datetime import datetime

# Core modules
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_module import update_sqi_inline
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.dc_io import DCContainerIO
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.drift_damping import apply_drift_damping
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.virtual_exhaust_module import ExhaustModule
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.safe_tuning_module import safe_qwave_tuning
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.warp_checks import check_warp_pi

# Awareness, DNA/SoulLaw, Prediction
from backend.modules.consciousness.awareness_engine import AwarenessEngine
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator
from backend.modules.dna_chain.dna_switch import DNA_SWITCH

# ECU Orchestration
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.orchestrator.tick_orchestrator import TickOrchestrator

# Glyph Trace Logger
try:
    from backend.modules.glyphnet import glyph_trace_logger
except ImportError:
    glyph_trace_logger = None


# =========================
# 🔄 CORE TICK HANDLER
# =========================
def tick(engine_a, engine_b=None):
    """
    🔄 Unified Hyperdrive Tick (Single + Dual Engine):
    • SQI inline correction, drift damping, harmonic coherence.
    • DNA/SoulLaw modulation, awareness, predictive foresight.
    • TickOrchestrator sync, warp PI checks, safe tuning.
    • Dual-engine glyph trace logging (Engine A & B split traces).
    """
    now = time.time()
    dt_a = now - engine_a.last_update
    if dt_a < engine_a.tick_delay:
        return

    engine_a.last_update = now
    engine_a.tick_count += 1

    if engine_b:
        dt_b = now - engine_b.last_update
        if dt_b >= engine_b.tick_delay:
            engine_b.last_update = now
            engine_b.tick_count += 1

    # 🌱 SQI Inline Correction
    update_sqi_inline(engine_a, dt_a)
    if engine_b:
        update_sqi_inline(engine_b, dt_b)

    # 🛠 Virtual Exhaust
    ExhaustModule().simulate(engine_a)
    if engine_b:
        ExhaustModule().simulate(engine_b)

    # ♻️ Particle Physics
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.physics_module import (
        update_particles, decay_particles, seed_particles_if_low,
    )
    decay_particles(engine_a, dt_a)
    seed_particles_if_low(engine_a)
    update_particles(engine_a, dt_a)

    if engine_b:
        decay_particles(engine_b, dt_b)
        seed_particles_if_low(engine_b)
        update_particles(engine_b, dt_b)

    # 🎶 Harmonic Coherence & Drift
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonics_module import update_harmonics
    coherence_a, drift_a = asyncio.run(update_harmonics(engine_a, dt_a))
    coherence_b, drift_b = (0.0, 0.0)
    if engine_b:
        coherence_b, drift_b = asyncio.run(update_harmonics(engine_b, dt_b))

    # 🌪 Drift Damping
    apply_drift_damping(engine_a)
    if engine_b:
        apply_drift_damping(engine_b)

    # 🧠 Awareness Update
    _update_awareness(engine_a, coherence_a)
    if engine_b:
        _update_awareness(engine_b, coherence_b)

    # 🧬 DNA/SoulLaw Modulation
    _dna_soullaw_modulation(engine_a)
    if engine_b:
        _dna_soullaw_modulation(engine_b)

    # 🔮 Predictive Glyph Foresight
    asyncio.create_task(_inject_predictions(engine_a))
    if engine_b:
        asyncio.create_task(_inject_predictions(engine_b))

    # 🛡 Safe Tuning
    if engine_a.tick_count % 25 == 0:
        safe_qwave_tuning(engine_a)
        engine_a.log_event("🛡 Safe tuning enforced.")
    if engine_b and engine_b.tick_count % 25 == 0:
        safe_qwave_tuning(engine_b)
        engine_b.log_event("🛡 Safe tuning enforced.")

    # ⚙ ECU Orchestration
    if engine_a.tick_count % 50 == 0:
        TickOrchestrator(engine_a, getattr(engine_a, "stage_controller", None)).tick()
        engine_a.log_event("⚙ TickOrchestrator tick executed (Engine A).")
    if engine_b and engine_b.tick_count % 50 == 0:
        TickOrchestrator(engine_b, getattr(engine_b, "stage_controller", None)).tick()
        engine_b.log_event("⚙ TickOrchestrator tick executed (Engine B).")

    # 🚀 Warp PI Checks
    if engine_a.tick_count % 50 == 0:
        _warp_pi_check(engine_a)
    if engine_b and engine_b.tick_count % 50 == 0:
        _warp_pi_check(engine_b)

    # 🎛 SQI Controller Sync
    if hasattr(engine_a, "sqi_controller"):
        engine_a.sqi_controller._sync_and_damp()
    if engine_b and hasattr(engine_b, "sqi_controller"):
        engine_b.sqi_controller._sync_and_damp()

    # 📝 Glyph Trace Logging (Dual Engine)
    _log_glyph_trace(engine_a, coherence_a, drift_a, label="Engine A")
    if engine_b:
        _log_glyph_trace(engine_b, coherence_b, drift_b, label="Engine B")

    # 🚦 Tick Limit Guard
    if engine_a.tick_limit and engine_a.tick_count >= engine_a.tick_limit:
        print(f"⚠ Engine A tick limit reached: {engine_a.tick_limit}")
        return
    if engine_b and engine_b.tick_limit and engine_b.tick_count >= engine_b.tick_limit:
        print(f"⚠ Engine B tick limit reached: {engine_b.tick_limit}")
        return

    # 🚀 Stage Advancement
    _stage_advance(engine_a)
    if engine_b:
        _stage_advance(engine_b)


# =========================
# 🧠 AWARENESS UPDATE
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
            trigger_type="coherence_update"
        )
        if coherence < 0.6:
            engine.awareness.log_blindspot(
                glyph="⚠",
                coord=f"stage:{engine.stages[engine.current_stage]}",
                container_id=engine.container.id,
                tick=engine.tick_count,
                context="low_coherence_blindspot"
            )
    except Exception as e:
        engine.log_event(f"⚠️ AwarenessEngine integration failed: {e}")


# =========================
# 🧬 DNA/SOULLAW MODULATION
# =========================
def _dna_soullaw_modulation(engine):
    try:
        validator = get_soul_law_validator()
        avatar_state = engine.safe_mode_avatar if engine.safe_mode else {
            "id": "hyperdrive_runtime",
            "role": "engine_operator",
            "level": validator.MIN_AVATAR_LEVEL,
        }
        if validator.validate_avatar_with_context(avatar_state=avatar_state, context="hyperdrive_field_modulation"):
            active_switches = len(DNA_SWITCH.list())
            scale_factor = 1.0 + (0.02 * active_switches)
            engine.fields["gravity"] *= scale_factor
            engine.fields["magnetism"] *= scale_factor
            engine.log_event(f"🧬 DNA/SoulLaw modulation applied: scale={scale_factor:.3f} | Switches={active_switches}")
        else:
            engine.log_event("⚠️ DNA/SoulLaw modulation skipped: Avatar failed validation.")
    except Exception as e:
        engine.log_event(f"⚠️ DNA/SoulLaw modulation error: {e}")


# =========================
# 🔮 PREDICTIVE GLYPH INJECTION
# =========================
async def _inject_predictions(engine):
    try:
        predictor = PredictionEngine(engine=engine)
        prediction = predictor.forecast_tick(engine)
        if prediction:
            inject_from_prediction(engine, prediction)
    except Exception as e:
        engine.log_event(f"⚠️ Prediction injection failed: {e}")


def inject_from_prediction(engine, prediction: Dict[str, Any]):
    glyphs = prediction.get("glyphs", [])
    adjustments = prediction.get("adjustments", {})

    for field, value in adjustments.items():
        if field in engine.fields:
            engine.fields[field] = value
            engine.log_event(f"🔮 Predictive adjustment applied: {field}={value:.4f}")

    if hasattr(engine, "injectors") and engine.injectors:
        for i, glyph in enumerate(glyphs):
            pulse_params = _glyph_to_pulse(glyph)
            injector = engine.injectors[i % len(engine.injectors)]
            injector.set_pulse_strength(pulse_params["pulse"])
            injector.set_particle_density(pulse_params["density"])
            injector.multi_compress_and_fire(engine)
            engine.log_event(f"🚀 Predictive glyph injected via Injector {injector.id}: {glyph}")


def _glyph_to_pulse(glyph: str) -> Dict[str, float]:
    glyph_map = {
        "⚛": {"density": 1.5, "pulse": 1.0},
        "↯": {"density": 1.2, "pulse": 0.8},
        "🎶": {"density": 1.0, "pulse": 0.6},
    }
    return glyph_map.get(glyph, {"density": 1.0, "pulse": 0.5})


# =========================
# 📝 GLYPH TRACE LOGGER
# =========================
def _log_glyph_trace(engine, coherence: float, drift: float, label: str = "Engine"):
    if glyph_trace_logger:
        try:
            glyph_trace_logger.log_trace({
                "tick": engine.tick_count,
                "engine_label": label,
                "stage": getattr(engine, "current_stage", "N/A"),
                "container_id": getattr(engine.container, "id", "N/A"),
                "resonance": getattr(engine, "resonance_phase", 0.0),
                "coherence": coherence,
                "drift": drift,
                "particles": len(engine.particles),
                "timestamp": datetime.utcnow().isoformat(),
                "fields": deepcopy(engine.fields),
                "glyphs": getattr(engine, "glyphs", []),
            })
        except Exception as e:
            engine.log_event(f"⚠️ Glyph trace logging failed: {e}")


# =========================
# 🚀 WARP PI CHECK
# =========================
def _warp_pi_check(engine):
    warp_ready = check_warp_pi(engine=engine, window=500, label=f"warp_snapshot_tick_{engine.tick_count}")
    if warp_ready:
        engine.log_event(f"🚀 Warp PI milestone achieved (PI ≥ {HyperdriveTuningConstants.WARP_PI_THRESHOLD})")
    else:
        engine.log_event(f"ℹ Warp PI not yet achieved (PI < {HyperdriveTuningConstants.WARP_PI_THRESHOLD})")


# =========================
# 🚀 STAGE ADVANCEMENT
# =========================
def _stage_advance(engine):
    if hasattr(engine, "stage_controller") and callable(getattr(engine.stage_controller, "advance", None)):
        engine.stage_controller.advance(engine)