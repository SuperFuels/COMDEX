"""
🚀 Warp Checks Module (Enhanced)
--------------------------------
• Evaluates warp readiness (PI output vs threshold) with harmonic & SQI context.
• Provides SQI stability and predictive warp milestone logging.
"""

# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/warp_checks.py

from datetime import datetime
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.idle_manager_module import save_idle_state
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger

def check_warp_pi(engine, window=500, label="warp_milestone_snapshot", threshold=None):
    """
    Calculates PI (Propulsion Index) over exhaust impact speeds, validates harmonic coherence,
    and logs warp milestone readiness with SQI drift checks.
    """
    threshold = threshold if threshold is not None else HyperdriveTuningConstants.WARP_PI_THRESHOLD

    # Compute PI (Propulsion Index)
    pi_val = sum(e.get("impact_speed", 0) for e in engine.exhaust_log[-window:])
    coherence = measure_harmonic_coherence(engine)
    drift = max(engine.resonance_filtered[-30:], default=0) - min(engine.resonance_filtered[-30:], default=0)

    print(f"🔎 PI Check: {pi_val:.0f} PU | Harmonic Coherence={coherence:.3f} | Drift={drift:.4f} | Threshold={threshold}")

    # Telemetry log snapshot
    TelemetryLogger(log_dir="data/qwave_logs").log({
        "timestamp": datetime.utcnow().isoformat(),
        "pi_val": pi_val,
        "harmonic_coherence": coherence,
        "drift": drift,
        "threshold": threshold,
        "sqi_stable": drift <= HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD,
    })

    # Warp milestone decision
    if pi_val >= threshold:
        if coherence < 0.6:
            print(f"⚠ Low Harmonic Coherence ({coherence:.3f}) detected → Auto harmonic injection before warp lock.")
            engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)

        if drift > HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD:
            print(f"⚠ Drift above SQI limit ({drift:.4f}). Warp lock deferred until stabilization.")
            return False

        print(f"🚀 WARP MILESTONE ACHIEVED: PI={pi_val:.0f} PU (≥{threshold}) | Coherence={coherence:.3f}")
        save_idle_state(engine, label=label)
        return True

    return False


def check_sqi_stability(engine, drift_window=30):
    """
    Returns True if SQI resonance drift is stable and coherence is acceptable.
    """
    if not engine.sqi_enabled:
        return False
    drift = max(engine.resonance_filtered[-drift_window:], default=0) - min(engine.resonance_filtered[-drift_window:], default=0)
    coherence = measure_harmonic_coherence(engine)
    stable = drift <= 0.05 and coherence >= 0.5
    print(f"🧠 SQI Stability Check → Drift={drift:.4f} | Coherence={coherence:.3f} | Stable={stable}")
    return stable


# ✅ Alias for legacy import compatibility
check_pi_threshold = check_warp_pi