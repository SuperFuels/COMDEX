from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants as HyperdriveTuning
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence

def check_stage_stability(engine, extended: bool = True) -> bool:
    """
    Stage stability check:
    - Basic: Drift check vs HyperdriveTuning threshold
    - Extended: Adds harmonic coherence scoring, SQI lock triggers, and stability rollbacks
    """
    # -----------------------
    # ✅ Basic Stability Mode
    # -----------------------
    if not extended:
        drift = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)
        if drift <= HyperdriveTuning.RESONANCE_DRIFT_THRESHOLD:
            print(f"✅ Stage stability confirmed: Drift={drift:.4f} <= Threshold={HyperdriveTuning.RESONANCE_DRIFT_THRESHOLD}")
            return True
        else:
            print(f"⚠ Instability detected: Drift={drift:.3f} exceeds threshold ({HyperdriveTuning.RESONANCE_DRIFT_THRESHOLD}).")
            return False

    # -----------------------
    # 🔧 Extended Stability Mode
    # -----------------------
    if len(engine.resonance_filtered) < engine.stage_stability_window:
        print("⏳ Insufficient resonance data for stability evaluation.")
        return False

    # Drift window calculation
    window = engine.resonance_filtered[-engine.stage_stability_window:]
    drift = max(window) - min(window)

    # 🎼 Harmonic coherence score
    coherence = measure_harmonic_coherence(engine)
    engine.last_harmonic_coherence = coherence
    print(f"🎼 Harmonic Coherence={coherence:.3f} | Drift={drift:.4f}")

    # 🫀 Pulse detection (stable harmonic lock signature)
    if drift <= (engine.stability_threshold * 0.5) and coherence >= 0.7:
        print(f"🫀 Pulse detected: Drift={drift:.4f}, Coherence={coherence:.3f}")
        if not engine.sqi_enabled:
            print("🔓 Auto-enabling SQI: Pulse stability confirmed.")
            engine.sqi_enabled = True
            engine.pending_sqi_ticks = 10

    # ✅ Stage advancement (SQI lock + coherence alignment)
    if drift <= engine.stability_threshold and coherence >= 0.65:
        print(f"✅ Resonance stable (Drift={drift:.3f}, Coherence={coherence:.3f}) → Advancing stage.")
        engine._log_graph_snapshot()

        # 🔒 Auto SQI lock if stability persists
        if hasattr(engine, "handle_sqi_lock") and not engine.sqi_locked:
            engine.handle_sqi_lock(drift)
        return True

    # 🛡 Safety rollback if drift unstable or coherence poor
    if drift > engine.stability_threshold * 1.5 or coherence < 0.4:
        print(f"🛑 Stability degraded: Drift={drift:.3f}, Coherence={coherence:.3f} → Triggering SQI damping.")
        if hasattr(engine, "sqi_engine") and hasattr(engine.sqi_engine, "apply_damping"):
            engine.sqi_engine.apply_damping(engine.fields)

    print(f"⚠ Drift unstable: Drift={drift:.3f} exceeds stage threshold ({engine.stability_threshold:.3f})")
    return False