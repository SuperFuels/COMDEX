"""
🎵 Harmonic Coherence Measurement
--------------------------------
* Pure measurement utilities (no runtime tick logic).
* Calculates harmonic coherence & supports harmonic injection/resync.
"""

from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants

_last_coherence: float = 0.0
_stagnation_count: int = 0

def measure_harmonic_coherence(engine) -> float:
    """Calculate harmonic coherence (no runtime logic)."""
    global _last_coherence, _stagnation_count

    if not engine.resonance_filtered:
        return 0.0

    window = engine.resonance_filtered[-50:]
    peak = max(window, default=1e-6)
    drift = peak - min(window, default=0.0)
    coherence = (peak / (drift + 1e-6)) * 0.01 * HyperdriveTuningConstants.HARMONIC_GAIN
    coherence = max(0.0, min(1.0, coherence))

    if abs(coherence - _last_coherence) < 0.0001:
        _stagnation_count += 1
    else:
        _stagnation_count = 0
    _last_coherence = coherence
    return coherence

def inject_harmonics(engine, harmonics):
    """Inject harmonic frequencies into injectors/chambers."""
    if not harmonics: return
    base_freq = engine.fields.get("wave_frequency", 1.0)
    for i, injector in enumerate(engine.injectors):
        harmonic = harmonics[i % len(harmonics)]
        injector.sync_to_frequency(base_freq * harmonic)
    for chamber in engine.chambers:
        chamber.adjust_harmonic(base_freq)

def resync_harmonics(engine):
    """Resynchronize injectors/chambers."""
    base_frequency = engine.fields.get("wave_frequency", 1.0)
    engine.resonance_phase = 0.0
    for i, injector in enumerate(engine.injectors):
        injector.phase_offset = i * (360 / max(len(engine.injectors), 1))
        injector.sync_to_frequency(base_frequency)
    for chamber in engine.chambers:
        chamber.adjust_harmonic(base_frequency)
    engine.log_event(f"🎼 Harmonic resync complete: Base Frequency={base_frequency:.4f}")

# -------------------------
# 🔄 Pre-Runtime Auto-Pulse Hook
# -------------------------
def pre_runtime_autopulse(engine):
    """
    Pre-runtime autopulse logic to stabilize harmonics before main tick loop.
    Used by IdleManager during initialization.
    """
    if not engine or not hasattr(engine, "fields"):
        print("⚠️ [pre_runtime_autopulse] Engine invalid or missing fields.")
        return

    print("🔄 Pre-runtime autopulse: aligning harmonic waveforms...")

    # Slight boost to harmonic wave frequency for alignment
    engine.fields["wave_frequency"] *= 1.02
    engine.gain = getattr(engine, "gain", 1.0) * 1.01

    # Resync harmonics after adjustment
    if hasattr(engine, "resonance_phase"):
        engine.resonance_phase = (engine.resonance_phase + 0.1) % (2 * 3.14159)

    print(f"✅ Harmonic alignment complete: Gain={engine.gain:.4f}, Wave={engine.fields['wave_frequency']:.4f}")