"""
⚙️ Gear Shift Manager Module
----------------------------
* Handles gear shifting logic for QWave engines.
* Implements pulse-gated field ramping with drift dampening.
* Supports slow clutch ramping to stabilize resonance during transitions.

🔥 Features:
    * Pulse-gated gear ramping (only shift during stable resonance pulses).
    * Drift dampener to auto-correct instability during gear shifts.
    * Slow clutch ramp duration (20-30s) to prevent collapse.
    * Inline harmonic injection during plasma/wave stages.
"""

import time
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.supercontainer_engine import QWaveTuning

def gear_shift(engine, gear_idx, GEAR_MAP, clutch_duration=25):
    """
    Perform a pulse-gated gear shift on the given engine.

    Args:
        engine: QWave engine instance.
        gear_idx: Target gear index (from GEAR_MAP).
        GEAR_MAP: List of gear field configs (gravity, magnetism, wave_frequency).
        clutch_duration: Time (seconds) to complete the shift.
    """
    target_fields = GEAR_MAP[gear_idx]
    print(f"\n⚙ Gear Shift -> {gear_idx} | Clutch engaged.")
    engine.stability_threshold *= 2  # Relax stability during ramp

    start = time.time()
    while time.time() - start < clutch_duration:
        # Calculate resonance drift
        drift = max(engine.resonance_filtered[-20:], default=0) - min(engine.resonance_filtered[-20:], default=0)

        # Pulse-gated ramping: only adjust fields during low drift pulses
        if drift < 0.05:
            for field in target_fields:
                step = (target_fields[field] - engine.fields[field]) * 0.05
                engine.fields[field] += step
        else:
            print(f"⏸ Paused shift: Drift spike detected ({drift:.3f})")

        # Drift dampener: counter instability by boosting gravity
        if drift > 0.1:
            engine.fields["gravity"] *= 1.01
            print(f"🛠 Drift dampener applied: gravity={engine.fields['gravity']:.3f}")

        # Tick engine and inject harmonics if in plasma/wave stages
        engine.tick()
        if engine.stages[engine.current_stage] in ["plasma_excitation", "wave_focus"]:
            engine._inject_harmonics(QWaveTuning.HARMONICS)

    # Reset stability threshold to default
    engine.stability_threshold = QWaveTuning.RESONANCE_DRIFT_THRESHOLD / 2
    print(f"✅ Gear {gear_idx} stabilized.")