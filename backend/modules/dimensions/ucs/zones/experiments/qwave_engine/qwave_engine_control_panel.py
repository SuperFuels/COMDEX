"""-----------------------------------------
⚙️ QWave Engine Control Panel (Orchestrator)
--------------------------------------------
• Coordinates ignition, ECU runtime tuning, gear shifting, SQI, and multi-engine sync.
• Imports modular subsystems:
    - 🧩 Tesseract Injector: Multi-stage compression injectors + compression chambers.
    - 🧩 Gear Shift Manager: Pulse-gated gear shifting with drift dampener.
    - 🧩 Engine Sync: Twin-engine resonance lock + exhaust → intake chaining.
    - 🧩 Idle Manager: Ignition sequence, idle detection, and auto-recovery.
• SQI Integration: Inline drift auto-corrections and resonance feedback.
• ECU Runtime Loop: Harmonics-fuel-injector orchestration with velocity clamps.

🔥 Features Included:
    • Full ignition → idle stabilization with SQI drift feedback.
    • Tesseract injector with staged density amplification.
    • ECU runtime driver (harmonics ↔ injectors ↔ SQI tuning).
    • Pulse-gated gear shifting with sub-step gears (1.2, 1.5 before Gear 2).
    • Twin-engine resonance synchronization (F2).
    • Exhaust → intake chaining for multi-engine amplification (F3).
    • Auto-recovery: Reload idle state post-collapse.
"""

import os
import time
import json
import argparse
from datetime import datetime

# -------------------------
# CLI Argument Parser
# -------------------------
parser = argparse.ArgumentParser(description="QWave Engine Control Panel Runtime")
parser.add_argument("--ticks", type=int, default=5000, help="Total ECU runtime ticks (default: 5000)")
parser.add_argument("--sqi", type=int, default=200, help="SQI correction interval in ticks (default: 200)")
parser.add_argument("--fuel", type=int, default=5, help="Fuel cycle frequency (ticks per fuel inject) (default: 5)")
parser.add_argument("--harmonics", type=int, nargs="+", default=[2, 3], help="Harmonic frequencies list (e.g., 2 3 4)")
parser.add_argument("--injector-interval", type=int, default=5, help="Tick interval for proton injection (default: 5)")
parser.add_argument("--gravity", type=float, default=1.0, help="Initial gravity field strength")
parser.add_argument("--magnetism", type=float, default=1.0, help="Initial magnetism field strength")
parser.add_argument("--wave-frequency", type=float, default=1.0, help="Initial wave frequency")
parser.add_argument("--enable-sqi", action="store_true", help="Enable SQI-driven stage adjustments.")
parser.add_argument("--sqi-phase-aware", action="store_true", help="Enable SQI phase-aware dynamic stage tuning.")
parser.add_argument("--manual-stage", action="store_true", help="Force manual stage levers (disable SQI control).")
parser.add_argument("--enable-engine-b", action="store_true", help="Enable second engine for twin sync tests.")
parser.add_argument("--safe-mode", action="store_true", help="Enable Safe Mode (reduced particle count & capped fields).")
args = parser.parse_args()

# -------------------------
# Imports
# -------------------------
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.supercontainer_engine import SupercontainerEngine
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.tesseract_injector import TesseractInjector, CompressionChamber
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.gear_shift_manager import gear_shift
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.engine_sync import sync_twin_engines, exhaust_to_intake
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.idle_manager import ignition_to_idle, save_idle_state, load_idle_state

# -------------------------
# ECU Runtime Loop (SQI Sync Integrated)
# -------------------------
def ecu_runtime_loop(engine_a, engine_b=None, sqi_phase_aware=False, sqi_interval=200, fuel_cycle=5, manual_stage=False, ticks=5000):
    """
    ECU runtime loop with optional SQI drift-phase sync between Engine A and Engine B.
    """
    tick_counter = 0
    print("🚦 Starting ECU Runtime Loop...")

    while tick_counter < ticks:
        engine_a.tick()
        if engine_b:
            engine_b.tick()

        tick_counter += 1

        # SQI Phase-Aware Sync
        if sqi_phase_aware and engine_b:
            drift_diff = abs(engine_a.resonance_phase - engine_b.resonance_phase)
            if drift_diff > 0.01:
                adjustment = (engine_a.resonance_phase - engine_b.resonance_phase) * 0.5
                engine_b.resonance_phase += adjustment
                print(f"🔗 SQI Phase Sync: Engine B adjusted by {adjustment:.5f} (Δ={drift_diff:.5f})")

            # Field Sync every SQI interval
            if tick_counter % sqi_interval == 0:
                engine_b.fields = engine_a.fields.copy()
                print(f"🔄 SQI Field Sync @tick {tick_counter}: Engine B fields updated to match Engine A.")

        # Fuel injection cycle
        if tick_counter % fuel_cycle == 0:
            engine_a.inject_proton()
            if engine_b:
                engine_b.inject_proton()

        drift_a = max(engine_a.resonance_filtered[-30:], default=0) - min(engine_a.resonance_filtered[-30:], default=0)
        drift_b = (max(engine_b.resonance_filtered[-30:], default=0) - min(engine_b.resonance_filtered[-30:], default=0)) if engine_b else None
        print(f"📊 ECU Tick={tick_counter} | Drift A={drift_a:.4f} | Drift B={drift_b if engine_b else 'N/A'}")

        time.sleep(0.01)  # Stabilize loop timing

# -------------------------
# Engine Init
# -------------------------
def create_engine(name="engine"):
    container = SymbolicExpansionContainer(container_id=name)
    engine = SupercontainerEngine(
        container=container,
        safe_mode=args.safe_mode,
        stage_lock=4,
        virtual_absorber=True
    )
    engine.injectors = [TesseractInjector(i, phase_offset=i * 3) for i in range(4)]
    engine.chambers = [CompressionChamber(i, compression_factor=1.3) for i in range(4)]

    # Apply runtime overrides
    engine.injector_interval = args.injector_interval
    engine.fields["gravity"] = args.gravity
    engine.fields["magnetism"] = args.magnetism
    engine.fields["wave_frequency"] = args.wave_frequency

    engine.sqi_enabled = args.enable_sqi
    mode = "Phase-Aware" if args.sqi_phase_aware else "Fixed-Interval"
    print(f"{'✅ SQI Enabled:' if engine.sqi_enabled else '🛑 SQI Disabled:'} {mode if engine.sqi_enabled else 'Manual stage control active.'}")

    print(f"🛠 Engine '{name}' initialized: Injectors={len(engine.injectors)}, Chambers={len(engine.chambers)}")
    return engine

# -------------------------
# CLI Entry Point
# -------------------------
if __name__ == "__main__":
    print("⚙ Initializing Engine A...")
    engine_a = create_engine("engine-A")
    ignition_to_idle(engine_a)

    engine_b = None
    if args.enable_engine_b:
        print("⚙ Initializing Engine B...")
        engine_b = create_engine("engine-B")
        ignition_to_idle(engine_b)

        print("🔗 Pre-syncing Engine A ↔ Engine B...")
        sync_twin_engines(engine_a, engine_b)

    print("🚦 Starting ECU Runtime Loop...")
    ecu_runtime_loop(
    engine_a,
    engine_b=engine_b,
    sqi_phase_aware=args.sqi_phase_aware,
    sqi_interval=args.sqi,
    fuel_cycle=args.fuel,
    manual_stage=args.manual_stage,
    ticks=args.ticks
)

    # Gear shift sequencing if Engine B is active
    if engine_b:
        for g in [1, 2]:
            print(f"🔧 Gear Shift: Engine A → Gear {g}")
            gear_shift(engine_a, g, [
                {"gravity": 0.8, "magnetism": 0.5, "wave_frequency": 0.5},
                {"gravity": 1.0, "magnetism": 1.2, "wave_frequency": 1.0},
                {"gravity": 1.1, "magnetism": 1.35, "wave_frequency": 1.25},
                {"gravity": 1.15, "magnetism": 1.4, "wave_frequency": 1.35},
                {"gravity": 1.2, "magnetism": 1.5, "wave_frequency": 1.5},
                {"gravity": 1.5, "magnetism": 1.8, "wave_frequency": 2.0},
            ])

            print(f"🔧 Gear Shift: Engine B → Gear {g}")
            gear_shift(engine_b, g, [
                {"gravity": 0.8, "magnetism": 0.5, "wave_frequency": 0.5},
                {"gravity": 1.0, "magnetism": 1.2, "wave_frequency": 1.0},
                {"gravity": 1.1, "magnetism": 1.35, "wave_frequency": 1.25},
                {"gravity": 1.15, "magnetism": 1.4, "wave_frequency": 1.35},
                {"gravity": 1.2, "magnetism": 1.5, "wave_frequency": 1.5},
                {"gravity": 1.5, "magnetism": 1.8, "wave_frequency": 2.0},
            ])

            exhaust_to_intake(engine_a, engine_b)

        print("🚀 Engine A ↔ B twin sync + chaining complete.")