from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants

def measure_harmonic_coherence(engine):
    """
    📊 Calculates harmonic coherence between resonance drift and peak amplitude.
    - Uses ECU-aligned drift window.
    - Factors in harmonic gain from HyperdriveTuningConstants.
    """
    if not engine.resonance_filtered:
        return 0.0

    window = engine.resonance_filtered[-50:]  # ECU-standard window size
    peak = max(window, default=1e-6)
    drift = max(window, default=1e-6) - min(window, default=0.0)

    # Coherence scaled by harmonic gain to track SQI tuning effects
    coherence = (peak / (drift + 1e-6)) * 0.01 * HyperdriveTuningConstants.HARMONIC_GAIN
    return min(1.0, max(0.0, coherence))


def pre_runtime_autopulse(engine):
    """
    🔧 Applies a pre-runtime auto-pulse ramp to stabilize fields & harmonics.
    - Soft field ramping for gravity/magnetism/wave alignment.
    - Injects a harmonic burst (ECU-tuned) if SQI is enabled.
    """
    print("🔧 Pre-runtime Auto-pulse ramp applied.")

    # ✅ Mild stabilization ramp
    engine.fields["gravity"] *= 1.01
    engine.fields["magnetism"] *= 1.01
    engine.fields["wave_frequency"] *= 1.005

    # ✅ Particle safety enforcement
    if hasattr(engine, "particles"):
        HyperdriveTuningConstants.enforce_particle_safety(engine)

    # ✅ Optional SQI harmonic burst before runtime loop
    if getattr(engine, "sqi_enabled", False) and hasattr(engine, "_inject_harmonics"):
        print("🎶 Injecting pre-runtime harmonic burst (SQI-aligned).")
        engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)

    # ✅ Reset drift counters for clean runtime start
    if hasattr(engine, "resonance_filtered"):
        engine.resonance_filtered.clear()