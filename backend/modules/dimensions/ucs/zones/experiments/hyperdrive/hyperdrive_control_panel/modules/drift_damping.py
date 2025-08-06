# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/drift_damping.py

"""
⚠ Drift Damping Module (Enhanced with Multi-Seed Harmonic Fallback)
--------------------------------------------------------------------
• Detects resonance drift Δ beyond thresholds.
• Applies SQI damping (gravity/magnetism reduction).
• Monitors coherence stability over time.
• If coherence remains critically low, dynamically injects a fallback harmonic seed
  selected from the best of N prior stable states.
"""

from typing import TYPE_CHECKING, List, Dict
from collections import deque
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence

if TYPE_CHECKING:
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.hyperdrive_engine import HyperdriveEngine

# --- Persistent state ---
_low_coherence_counter = 0

# Store up to 5 past good seeds (gain, decay, damping, gravity, base_freq, coherence)
_seed_history: deque[Dict] = deque(maxlen=5)


def apply_drift_damping(engine: "HyperdriveEngine") -> float:
    """
    Checks engine drift Δ and applies SQI damping if exceeded.
    Dynamically scales damping factor based on harmonic coherence.
    If coherence remains critically low with high drift, injects the best fallback harmonic seed.
    Returns drift value for telemetry logging.
    """
    global _low_coherence_counter, _seed_history

    # Calculate drift window
    drift = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)
    coherence = measure_harmonic_coherence(engine)

    # --- SQI Damping ---
    if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
        damping_scale = 0.98 - (0.02 * (1.0 - coherence))  # Less coherence = stronger damping
        engine.fields["gravity"] *= damping_scale
        engine.fields["magnetism"] *= damping_scale
        engine.decay_rate *= (1.0 + (drift / HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD) * 0.01)

        engine.log_event(f"⚠ Drift spike: Δ={drift:.4f} | Coherence={coherence:.3f} → Damping={damping_scale:.3f}")
        print(f"⚠ Drift spike detected: Δ={drift:.3f} | Harmonic Coherence={coherence:.3f} → SQI damping applied.")

    # --- Seed Capture: store stable states ---
    if coherence > 0.08:  # threshold for "good stability"
        _seed_history.append({
            "gain": engine.gain,
            "decay": engine.decay_rate,
            "damping": getattr(engine, "damping_factor", 0.981),
            "gravity": engine.fields.get("gravity", 1.94),
            "base_freq": getattr(engine.injector_controller, "last_freq", 0.541),
            "coherence": coherence,
        })

    # --- Low-Coherence Watchdog ---
    if coherence < 0.012:
        _low_coherence_counter += 1
    else:
        _low_coherence_counter = 0

    # --- Trigger Multi-Seed Fallback ---
    if _low_coherence_counter > 20 and drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD * 0.8:
        if _seed_history:
            # Select seed with highest coherence
            best_seed = max(_seed_history, key=lambda s: s["coherence"])
            print(f"[⚠️ SQI] Low coherence ({coherence:.3f}) + drift Δ={drift:.3f} → Injecting best fallback seed (coherence={best_seed['coherence']:.3f}).")

            # Apply selected seed parameters
            engine.gain = best_seed["gain"]
            engine.decay_rate = best_seed["decay"]
            engine.damping_factor = best_seed["damping"]
            engine.fields["gravity"] = best_seed["gravity"]

            base_frequency = best_seed["base_freq"]
            if hasattr(engine, "injector_controller") and hasattr(engine, "chamber_controller"):
                engine.injector_controller.set_all(base_frequency)
                engine.chamber_controller.set_all(base_frequency)

            engine.log_event(f"[✅ Fallback] Seed restored → Base={base_frequency:.3f}Hz | Gain={best_seed['gain']:.3f}")
            print(f"[✅ Fallback] Harmonic seed injection → Base={base_frequency:.3f}, Gain={best_seed['gain']:.3f}, Gravity={best_seed['gravity']:.3f}")
        else:
            print("[⚠️ SQI] Low coherence detected but no seeds in memory → fallback skipped.")

        _low_coherence_counter = 0  # reset counter

    return drift