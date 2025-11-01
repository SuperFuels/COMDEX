import os
import json
import logging
import asyncio
import random
import time
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import pre_runtime_autopulse

# 🔥 Safety and predictive constants
THERMAL_MAX = HyperdriveTuningConstants.THERMAL_MAX
THERMAL_SLOPE_MAX = HyperdriveTuningConstants.THERMAL_SLOPE_MAX
POWER_MAX = HyperdriveTuningConstants.POWER_MAX
STABILITY_INDEX_MIN = HyperdriveTuningConstants.STABILITY_INDEX_MIN
RESONANCE_DRIFT_THRESHOLD = HyperdriveTuningConstants.RESONANCE_DRIFT_THRESHOLD

# 💾 Runtime Persistence File (used by TickOrchestrator)
PERSISTENCE_FILE = "data/runtime_hyperdrive_constants.json"

logger = logging.getLogger(__name__)


class ECUDriftRegulator:
    """
    Regulates the stability of the HyperdriveEngine by applying drift corrections.
    Can simulate gradual feedback loops and auto-damp instabilities.
    """

    def __init__(self, damping_factor: float = 0.85):
        self.damping_factor = damping_factor
        self.drift_level = 0.0
        self.last_tick_time = time.time()

    def apply_drift_correction(self):
        now = time.time()
        elapsed = now - self.last_tick_time
        self.last_tick_time = now

        drift_input = random.uniform(-1.0, 1.0)
        self.drift_level += drift_input * elapsed
        self.drift_level *= self.damping_factor

        logger.debug(f"[ECUDriftRegulator] Drift corrected to {self.drift_level:.4f} (elapsed: {elapsed:.2f}s)")
        return self.drift_level

    def get_stability_index(self) -> float:
        """
        Returns a normalized index between 0 (unstable) and 1 (stable).
        """
        return max(0.0, 1.0 - abs(self.drift_level))


class HyperdriveInstabilityMonitor:
    """
    Monitors ECU drift values and emits warnings or emergency triggers if instability exceeds threshold.
    """

    def __init__(self, regulator: ECUDriftRegulator, threshold: float = 0.75):
        self.regulator = regulator
        self.threshold = threshold
        self.triggered = False

    async def monitor_loop(self, interval: float = 2.0):
        logger.info("[InstabilityMonitor] Starting monitoring loop")
        while True:
            stability = self.regulator.get_stability_index()

            if stability < self.threshold:
                if not self.triggered:
                    logger.warning(f"[InstabilityMonitor] Stability dropped to {stability:.2f}. Triggering response!")
                    self.trigger_response()
            else:
                if self.triggered:
                    logger.info(f"[InstabilityMonitor] Stability recovered to {stability:.2f}. Resetting trigger.")
                    self.reset_response()

            await asyncio.sleep(interval)

    def trigger_response(self):
        self.triggered = True
        # TODO: Inject emergency glyph or trigger protocol escalation here

    def reset_response(self):
        self.triggered = False

def save_runtime_constants(constants):
    """Save harmonic tuning constants persistently for cross-session use."""
    os.makedirs(os.path.dirname(PERSISTENCE_FILE), exist_ok=True)
    with open(PERSISTENCE_FILE, "w") as f:
        json.dump(constants, f, indent=4)

def load_runtime_constants():
    """Load harmonic tuning constants if they exist (used by TickOrchestrator)."""
    if os.path.exists(PERSISTENCE_FILE):
        with open(PERSISTENCE_FILE, "r") as f:
            return json.load(f)
    return {}

# ==========================
# Pre-ignition harmonic stabilization
# ==========================
def pre_ignition_harmonics(engine):
    """Inject baseline harmonics into engine before runtime loop starts."""
    if hasattr(engine, "_inject_harmonics"):
        engine.log_event("⚡ Pre-ignition harmonic seeding: injecting baseline harmonics.")
        engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)
        engine.fields["wave_frequency"] = max(engine.fields.get("wave_frequency", 0.0), 2.0)
        engine.log_event(f"🎵 Initial harmonic baseline set: {engine.fields['wave_frequency']:.3f} Hz")

# ==========================
# Minimal ECU Runtime Entry
# ==========================
def ecu_runtime_loop(engine_a, engine_b=None):
    """
    ECU Runtime Loop (Trimmed):
    * Performs pre-ignition stabilization.
    * Seeds plasma particles if missing.
    * Leaves all runtime tick orchestration, drift damping, SQI feedback,
      and telemetry to TickOrchestrator.
    """
    print(f"🚦 ECU Runtime Loop Start (TickOrchestrator handles runtime control).")

    # 🔧 Pre-runtime harmonic stabilization
    pre_runtime_autopulse(engine_a)
    if engine_b:
        pre_runtime_autopulse(engine_b)

    # ✅ Particle Seeding (Immediate Pre-Ignition Safety Net)
    if not engine_a.particles:
        engine_a.particles = [{"vx": 0.0, "vy": 0.0, "vz": 0.0} for _ in range(250)]
        print(f"💠 Seeded Engine A with {len(engine_a.particles)} baseline plasma particles.")
    if engine_b and not engine_b.particles:
        engine_b.particles = [{"vx": 0.0, "vy": 0.0, "vz": 0.0} for _ in range(250)]
        print(f"💠 Seeded Engine B with {len(engine_b.particles)} baseline plasma particles.")