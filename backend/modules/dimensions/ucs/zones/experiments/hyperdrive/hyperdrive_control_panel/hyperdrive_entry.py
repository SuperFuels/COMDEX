"""
🚀 Hyperdrive Main Runtime
--------------------------
• Unified entrypoint: CLI → Engine Init → SQI Engage → ECU Loop → Terminal/Dashboard.
• Supports dual-engine sync, SQI phase-aware runs, GHX dashboard, and safety recovery.
"""

import sys
import threading
import traceback
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.cli_parser_module import parse_cli_args
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.engine_factory_module import create_engine
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.ecu_runtime_module import ecu_runtime_loop
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.runtime_entrypoint_module import ignition_to_idle, twin_sync_and_gearshift
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import pre_runtime_autopulse
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.instability_check_module import check_instability
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.idle_manager_module import load_idle_state

ENGINE_REGISTRY = {}

if __name__ == "__main__":
    try:
        # 1️⃣ CLI Parsing
        args = parse_cli_args()
        print(f"🎛 Parsed CLI Args: {args}")

        # ========================
        # 2️⃣ Engine A Initialization
        # ========================
        print("⚙ Initializing Engine A...")
        engine_a = create_engine("engine-A", args)
        ENGINE_REGISTRY["engine_a"] = engine_a

        if not ignition_to_idle(engine_a, sqi=engine_a.sqi_engine if hasattr(engine_a, "sqi_engine") else None):
            print("⚠ Ignition failed → Attempting idle state reload...")
            load_idle_state(engine_a)

        # ✅ SQI Activation
        if args.enable_sqi:
            print("🧬 Enabling SQI for Engine A...")
            engine_a.sqi_enabled = True
            if hasattr(engine_a, "sqi_controller"):
                engine_a.sqi_controller.engage_feedback()
                engine_a.sqi_controller.auto_optimize(stages=[85, 90, 95, 99, 100])
            print("✅ SQI Feedback loop engaged for Engine A.")

            # Launch Terminal Thread
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.hyperdrive_terminal import hyperdrive_terminal
            threading.Thread(target=hyperdrive_terminal, args=(engine_a, None), daemon=True).start()

        # ========================
        # 3️⃣ Optional Engine B (Twin Mode)
        # ========================
        engine_b = None
        if getattr(args, "enable_engine_b", False):
            print("⚙ Initializing Engine B...")
            engine_b = create_engine("engine-B", args)
            ENGINE_REGISTRY["engine_b"] = engine_b

            if not ignition_to_idle(engine_b, sqi=engine_b.sqi_engine if hasattr(engine_b, "sqi_engine") else None):
                print("⚠ Ignition failed on Engine B → Attempting idle state reload...")
                load_idle_state(engine_b)

            if args.enable_sqi and hasattr(engine_b, "sqi_controller"):
                engine_b.sqi_enabled = True
                engine_b.sqi_controller.engage_feedback()

            twin_sync_and_gearshift(engine_a, engine_b, sync_only=True)

            # Launch Twin Terminal Thread
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.hyperdrive_terminal import hyperdrive_terminal
            threading.Thread(target=hyperdrive_terminal, args=(engine_a, engine_b), daemon=True).start()

        # ========================
        # 4️⃣ Pre-runtime Harmonic Auto-Pulse
        # ========================
        if getattr(args, "auto_pulse", False):
            pre_runtime_autopulse(engine_a)

        # ========================
        # 5️⃣ ECU Runtime Loop (SQI Phase-Aware)
        # ========================
        print("🔄 Entering ECU runtime loop...")
        ecu_runtime_loop(
            engine_a,
            engine_b=engine_b,
            sqi_phase_aware=args.sqi_phase_aware,
            sqi_interval=args.sqi_interval,
            fuel_cycle=args.fuel_cycle,
            manual_stage=args.manual_stage,
            ticks=args.ticks
        )

        # ========================
        # 6️⃣ GHX Dashboard (Optional)
        # ========================
        try:
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.ghx_dashboard_module import launch_dashboard
            print("🌌 Launching GHX Visualizer Dashboard...")
            launch_dashboard(engine_a)
        except ImportError:
            print("⚠️ GHX Dashboard not found (skipping visualization).")

        # ========================
        # 7️⃣ Final Twin Sync (if dual engines active)
        # ========================
        if engine_b:
            print("🔗 Final twin-engine sync...")
            twin_sync_and_gearshift(engine_a, engine_b)

        print("✅ Hyperdrive Runtime Complete.")

    except KeyboardInterrupt:
        print("\n🛑 Hyperdrive runtime interrupted by user. Shutting down cleanly...")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Fatal error in Hyperdrive Runtime: {e}")
        traceback.print_exc()
        sys.exit(1)