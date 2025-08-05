# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/harmonic_coherence_module.py

"""
🎵 Harmonic Coherence Module
----------------------------
• Calculates harmonic coherence with stagnation detection.
• Supports SQI pre-runtime seeding and safe particle injection.
• Auto-adjusts behavior for simulation to avoid infinite loops.
"""

from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants

# Track prior coherence for stagnation detection
_last_coherence: float = 0.0
_stagnation_count: int = 0


def measure_harmonic_coherence(engine) -> float:
    """
    📊 Calculates harmonic coherence with stagnation detection & SIM override.
    - Peak-to-drift normalized by HARMONIC_GAIN.
    - Detects stagnant coherence (flatline) to avoid infinite feedback cycles.
    """
    global _last_coherence, _stagnation_count

    # 🛡 Guard: No resonance history → return zero
    if not engine.resonance_filtered:
        return 0.0

    # 🔍 Compute windowed stats
    window = engine.resonance_filtered[-50:]
    peak = max(window, default=1e-6)
    drift = peak - min(window, default=0.0)

    # 🎼 Normalize coherence (scaled by harmonic gain)
    coherence = (peak / (drift + 1e-6)) * 0.01 * HyperdriveTuningConstants.HARMONIC_GAIN
    coherence = max(0.0, min(1.0, coherence))  # Clamp [0.0, 1.0]

    # 🚦 Stagnation detection: unchanged coherence over N ticks
    if abs(coherence - _last_coherence) < 0.0001:
        _stagnation_count += 1
    else:
        _stagnation_count = 0
    _last_coherence = coherence

    # 🔄 SIM safety: Break loops in virtual/sim mode
    if getattr(engine, "simulation_mode", False) and _stagnation_count > 5:
        print("⚠️ Harmonic stagnation in SIM detected → injecting seed coherence.")
        coherence = 0.15  # Seed minimal value to break flatline

    return coherence


def pre_runtime_autopulse(engine):
    """
    🔧 Pre-runtime Auto-Pulse Ramp
    - Applies mild field tuning and harmonic seeding before runtime.
    - Ensures resonance baseline exists for early SQI operations.
    """
    print("🔧 Pre-runtime Auto-pulse ramp applied.")

    # 🌌 Stabilize core fields
    engine.fields["gravity"] *= 1.01
    engine.fields["magnetism"] *= 1.01
    engine.fields["wave_frequency"] *= 1.005

    # 🛡 Particle safety enforcement
    if hasattr(engine, "particles"):
        HyperdriveTuningConstants.enforce_particle_safety(engine)

    # 🎶 Harmonic burst injection (SQI pre-seed)
    if getattr(engine, "sqi_enabled", False) and hasattr(engine, "_inject_harmonics"):
        print("🎶 Injecting pre-runtime harmonic burst (SQI-aligned).")
        engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)

    # 🌊 Resonance seeding: prevent flat zero coherence
    if hasattr(engine, "resonance_filtered") and not engine.resonance_filtered:
        engine.resonance_filtered.extend([0.01] * 10)  # Seed ripple baseline
        print("⚡ Resonance bootstrap seeded with baseline ripples (10x 0.01).")