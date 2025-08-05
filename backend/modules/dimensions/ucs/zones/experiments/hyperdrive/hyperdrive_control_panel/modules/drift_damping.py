# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/drift_damping.py

"""
⚠ Drift Damping Module
------------------------
• Detects resonance drift Δ beyond thresholds.
• Applies SQI damping (gravity/magnetism reduction).
• Integrates harmonic coherence scaling and decay feedback.
• Returns drift value for runtime logging and ECU use.
"""

from typing import TYPE_CHECKING
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence

if TYPE_CHECKING:
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.hyperdrive_engine import HyperdriveEngine

def apply_drift_damping(engine: "HyperdriveEngine") -> float:
    """
    Checks engine drift Δ and applies SQI damping if exceeded.
    Dynamically scales damping factor based on harmonic coherence.
    Returns drift value for telemetry logging.
    """
    # Calculate drift window (last 30 ticks)
    drift = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)
    coherence = measure_harmonic_coherence(engine)

    if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
        # Base damping scale (gravity & magnetism)
        damping_scale = 0.98 - (0.02 * (1.0 - coherence))  # Less coherence = stronger damping
        engine.fields["gravity"] *= damping_scale
        engine.fields["magnetism"] *= damping_scale

        # Harmonic decay feedback
        engine.decay_rate *= (1.0 + (drift / HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD) * 0.01)

        # Logging event hook
        engine.log_event(f"⚠ Drift spike: Δ={drift:.4f} | Coherence={coherence:.3f} → Damping={damping_scale:.3f}")
        print(f"⚠ Drift spike detected: Δ={drift:.3f} | Harmonic Coherence={coherence:.3f} → SQI damping applied.")

    return drift