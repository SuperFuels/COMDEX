"""
🚀 Hyperdrive Main Runtime
--------------------------
* Unified entrypoint: CLI -> Engine Init -> SQI Engage -> ECU Loop -> Terminal/Dashboard.
* Supports dual-engine sync, SQI phase-aware runs, GHX dashboard, and safety recovery.
"""

import sys
import threading
import traceback
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.cli_parser_module import parse_cli_args
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.engine_factory_module import create_engine
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.ecu_runtime_module import ecu_runtime_loop
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.runtime_entrypoint_module import ignition_to_idle, twin_sync_and_gearshift
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import pre_runtime_autopulse, measure_harmonic_coherence
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.instability_check_module import check_instability
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.idle_manager_module import load_idle_state, save_idle_state
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.stage_stability_module import check_stage_stability
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.state_manager_module import export_best_state

ENGINE_REGISTRY = {}

if __name__ == "__main__":
    try:
        # 1️⃣ CLI Parsing
        args = parse_cli_args()

        # 🔧 Sanitize harmonics input: allow "2,3,4" or "2, 3, 4" or "2 3 4"
        if getattr(args, "harmonics", None):
            harmonics_clean = []
            for h in args.harmonics:
                for val in str(h).replace(",", " ").split():
                    harmonics_clean.append(float(val) if "." in val else int(val))
            args.harmonics = harmonics_clean

        print(f"🎛 Parsed CLI Args: {args}")

        # ========================
        # 2️⃣ Engine A Initialization
        # ========================
        print("⚙ Initializing Engine A...")
        engine_a = create_engine("engine-A", args)
        ENGINE_REGISTRY["engine_a"] = engine_a

        if not ignition_to_idle(engine_a, sqi=engine_a.sqi_engine if hasattr(engine_a, "sqi_engine") else None):
            print("⚠ Ignition failed -> Attempting idle state reload for Engine A...")
            load_idle_state(engine_a)
            print("⏳ Retrying ignition after idle load...")
            ignition_to_idle(engine_a, sqi=engine_a.sqi_engine if hasattr(engine_a, "sqi_engine") else None)

        # 💾 Auto-save idle snapshot after ignition success
        save_idle_state(engine_a, label="post_ignition_engine_a")

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
        if args.enable_engine_b:
            print("⚙ Initializing Engine B...")
            engine_b = create_engine("engine-B", args)
            ENGINE_REGISTRY["engine_b"] = engine_b

            # 🔥 Attempt ignition -> fallback to idle recovery if needed
            if not ignition_to_idle(engine_b, sqi=getattr(engine_b, "sqi_engine", None)):
                print("⚠ Ignition failed on Engine B -> Attempting idle state reload...")
                load_idle_state(engine_b)
                print("⏳ Retrying ignition after idle load for Engine B...")
                ignition_to_idle(engine_b, sqi=getattr(engine_b, "sqi_engine", None))

            save_idle_state(engine_b, label="post_ignition_engine_b")

            # 🧬 Optional SQI enablement
            if args.enable_sqi:
                print("🧬 Enabling SQI for Engine B...")
                engine_b.sqi_enabled = True
                if hasattr(engine_b, "sqi_controller"):
                    engine_b.sqi_controller.engage_feedback()
                    engine_b.sqi_controller.auto_optimize(stages=[85, 90, 95, 99, 100])
                print("✅ SQI Feedback loop engaged for Engine B.")

            # ↔️ Sync Engines for Twin Mode
            twin_sync_and_gearshift(engine_a, engine_b, sync_only=True)

            # 🖥 Launch Twin Terminal (background)
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.hyperdrive_terminal import hyperdrive_terminal
            threading.Thread(target=hyperdrive_terminal, args=(engine_a, engine_b), daemon=True).start()

        # ========================
        # 4️⃣ Pre-runtime Harmonic Auto-Pulse
        # ========================
        if getattr(args, "auto_pulse", False):
            print("💠 Performing pre-runtime auto-pulse...")
            pre_runtime_autopulse(engine_a)

        # ========================
        # 5️⃣ Instability Check
        # ========================
        print("🧪 Running instability check...")
        if check_instability(engine_a):
            print("⚠ Engine A flagged unstable pre-runtime.")
        if engine_b and check_instability(engine_b):
            print("⚠ Engine B flagged unstable pre-runtime.")

        # ✅ Pre-runtime harmonic stability gate
        if not check_stage_stability(engine_a, extended=True):
            print("⚠ Engine A failed stability gate. Re-run harmonics or SQI damp before ECU.")
        if engine_b and not check_stage_stability(engine_b, extended=True):
            print("⚠ Engine B failed stability gate. SQI damp required.")

        # ========================
        # 6️⃣ ECU Runtime Loop (TickOrchestrator-aware)
        # ========================
        print("🔄 Entering ECU runtime loop...")
        print(f"🔎 Engine A Status: SQI={engine_a.sqi_enabled}, tick={getattr(engine_a, 'tick_count', 0)}")
        if engine_b:
            print(f"🔎 Engine B Status: SQI={engine_b.sqi_enabled}, tick={getattr(engine_b, 'tick_count', 0)}")

        ecu_runtime_loop(
            engine_a,
            engine_b=engine_b,
            sqi_phase_aware=args.sqi_phase_aware,
            sqi_interval=args.sqi_interval,
            fuel_cycle=args.fuel_cycle,
            manual_stage=args.manual_stage,
            ticks=args.ticks
        )

        # 💾 Export best state snapshot post-loop
        export_best_state(engine_a)
        if engine_b:
            export_best_state(engine_b)

        # ========================
        # 7️⃣ GHX Dashboard (Optional)
        # ========================
        try:
            from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.ghx_dashboard_module import launch_dashboard
            print("🌌 Launching GHX Visualizer Dashboard...")
            launch_dashboard(engine_a)
        except ImportError:
            print("⚠️ GHX Dashboard not found (skipping visualization).")

        # ========================
        # 8️⃣ Final Twin Sync (if dual engines active)
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