from datetime import datetime
import os, json
from typing import Dict, Any
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants

def run_sqi_feedback(engine):
    """
    SQI Feedback Loop:
    • Runs SQI symbolic analysis & field adjustments.
    • Integrates harmonic coherence scoring into tuning.
    • Auto-pauses SQI on low drift stability lock.
    • Auto-reactivates SQI on drift or coherence spikes.
    • Syncs with engine.handle_sqi_lock() if coherence locks.
    """
    # -----------------------
    # SQI Toggle Check
    # -----------------------
    if not getattr(engine, "sqi_enabled", True):
        print("🛑 SQI is currently disabled (set engine.sqi_enabled=True to re-enable).")
        return

    # Require resonance history
    if not engine.resonance_filtered or len(engine.resonance_filtered) < 5:
        print("⚠️ SQI skipped: Insufficient resonance data.")
        return

    # -----------------------
    # Harmonic Coherence Measurement
    # -----------------------
    coherence = measure_harmonic_coherence(engine)
    engine.last_harmonic_coherence = coherence
    print(f"🎼 SQI Harmonic Coherence: {coherence:.3f}")

    # -----------------------
    # SQI Symbolic Analysis
    # -----------------------
    print("🧠 Running SQI symbolic fine-tuning...")
    trace = {
        "resonance": engine.resonance_filtered[-50:],  
        "fields": engine.fields.copy(),
        "exhaust": [e.get("impact_speed", 0) for e in engine.exhaust_log[-20:]],
        "harmonic_coherence": coherence
    }

    reasoning = engine.sqi_engine.analyze_trace(trace)
    adjustments = engine.sqi_engine.recommend_adjustments(reasoning)

    if not adjustments:
        print("✅ SQI skipped: No corrective adjustments needed.")
        return

    # -----------------------
    # Clamp & Smooth Adjustments
    # -----------------------
    if "gravity" in adjustments:
        adjustments["gravity"] = min(adjustments["gravity"], HyperdriveTuningConstants.MAX_GRAVITY)
    if "magnetism" in adjustments:
        adjustments["magnetism"] = min(adjustments["magnetism"], HyperdriveTuningConstants.MAX_MAGNETISM)

    # Weighted smoothing for stability
    for k, v in adjustments.items():
        if k in engine.fields:
            adjustments[k] = (engine.fields[k] * 0.7) + (v * 0.3)

    print(f"🔮 SQI Adjustments Applied: {adjustments}")
    engine.fields.update(adjustments)
    engine.last_sqi_adjustments = adjustments

    # -----------------------
    # Drift & Stability Analysis
    # -----------------------
    drift_window = engine.resonance_filtered[-10:]
    drift = (max(drift_window) - min(drift_window)) if drift_window else 0.0
    print(f"📊 SQI Drift: {drift:.4f} | Stability Threshold: {engine.stability_threshold:.4f}")

    # 🛑 Auto-pause if stable drift lock & coherence lock
    if drift < engine.stability_threshold * 0.6 and coherence > 0.7:
        engine._low_drift_ticks = getattr(engine, "_low_drift_ticks", 0) + 1
        if engine._low_drift_ticks >= 5:
            print("🛑 SQI auto-paused: Drift + harmonic lock achieved.")
            engine.sqi_enabled = False
            engine._low_drift_ticks = 0

            # 🔒 Trigger SQI Lock if engine supports it
            if hasattr(engine, "handle_sqi_lock") and not engine.sqi_locked:
                engine.handle_sqi_lock(drift)

    # 🔄 Auto-reactivate if drift spikes or coherence drops
    elif drift > engine.stability_threshold or coherence < 0.5:
        if not engine.sqi_enabled:
            print("🔄 SQI auto-reactivated: Drift/coherence instability detected.")
            engine.sqi_enabled = True
            engine.pending_sqi_ticks = 5  # Grace period before applying heavy tuning

    # -----------------------
    # Harmonic Auto-Boost (if drift lock detected)
    # -----------------------
    if drift < engine.stability_threshold * 0.8 and coherence >= 0.65:
        if hasattr(engine, "_inject_harmonics"):
            engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)
            print("🎵 Harmonic injection boost applied (SQI stable window).")