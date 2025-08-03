# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/instability_check_module.py

import math
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.drift_damping import apply_drift_damping

def check_instability(engine) -> bool:
    """
    Detects instability spikes in resonance, harmonic coherence, or particle motion.
    Returns True if instability is detected and tick should halt or SQI dampening should engage.

    Integrated with:
    • Drift instability detection
    • Harmonic coherence collapse detection
    • Particle overspeed check
    • Auto drift damping for minor instability (if engine allows)
    """

    # -------------------------
    # 1️⃣ Drift-Based Instability
    # -------------------------
    if len(engine.resonance_filtered) >= 10:
        drift = max(engine.resonance_filtered[-10:]) - min(engine.resonance_filtered[-10:])
        if drift > RESONANCE_DRIFT_THRESHOLD:
            print(f"⚠ Instability detected: Drift={drift:.3f} exceeds threshold ({RESONANCE_DRIFT_THRESHOLD}).")

            # Auto drift damping if SQI enabled
            if getattr(engine, "sqi_enabled", False):
                print("🛠 SQI Inline: Applying drift damping...")
                apply_drift_damping(drift, engine.fields)
            return True

    # -------------------------
    # 2️⃣ Harmonic Coherence Collapse Detection
    # -------------------------
    if hasattr(engine, "resonance_filtered") and len(engine.resonance_filtered) >= 20:
        coherence = measure_harmonic_coherence(engine)
        engine.last_harmonic_coherence = coherence
        if coherence < getattr(HyperdriveTuningConstants, "HARMONIC_COHERENCE_MIN", 0.65):
            print(f"⚠ Harmonic instability: Coherence={coherence:.3f} < Min={HyperdriveTuningConstants.HARMONIC_COHERENCE_MIN}")
            if hasattr(engine, "_inject_harmonics"):
                print("🎵 Injecting corrective harmonics to counter coherence collapse...")
                engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)
            return True

    # -------------------------
    # 3️⃣ Particle Velocity Overspeed
    # -------------------------
    for p in engine.particles[-50:]:  # Sample subset for performance
        speed = math.sqrt(
            p.get("vx", 0) ** 2 +
            p.get("vy", 0) ** 2 +
            p.get("vz", 0) ** 2
        )
        if speed > SPEED_THRESHOLD:
            print(f"⚠ Instability detected: Particle overspeed (speed={speed:.2f}) > {SPEED_THRESHOLD}")
            if getattr(engine, "sqi_enabled", False):
                # Auto SQI damp response: reduce field intensity slightly
                engine.fields["gravity"] = max(engine.fields["gravity"] * 0.95, 0.1)
                engine.fields["magnetism"] = max(engine.fields["magnetism"] * 0.95, 0.1)
                print("🛠 SQI Auto-Response: Gravity & Magnetism damped to counter overspeed.")
            return True

    # -------------------------
    # ✅ Stable
    # -------------------------
    return False