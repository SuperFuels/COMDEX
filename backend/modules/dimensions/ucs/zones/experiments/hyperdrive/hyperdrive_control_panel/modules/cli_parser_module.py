import argparse

def parse_cli_args():
    """
    CLI Parser for Hyperdrive Main Runtime.
    Returns: argparse.Namespace with all core runtime flags, SQI tuning, safety, and advanced hyperdrive controls.
    """
    parser = argparse.ArgumentParser(
        description="🛠 Hyperdrive Engine Control Panel Runtime",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # =============================
    # CORE RUNTIME
    # =============================
    parser.add_argument("--ticks", type=int, default=5000,
                        help="Total ECU runtime ticks.")
    parser.add_argument("--sqi-interval", type=int, default=200,
                        help="SQI correction interval (ticks).")
    parser.add_argument("--fuel-cycle", type=int, default=5,
                        help="Fuel cycle frequency (ticks per fuel inject).")

    # =============================
    # ENGINE CONFIGURATION
    # =============================
    parser.add_argument("--harmonics", type=int, nargs="+", default=[2, 3, 4, 5],
                        help="Harmonic frequency ratios for injector phase sync.")
    parser.add_argument("--injector-interval", type=int, default=5,
                        help="Tick interval for proton injection.")
    parser.add_argument("--injectors", type=int, default=6,
                        help="Number of Tesseract injectors (scales intake).")
    parser.add_argument("--intake-rate", type=int, default=1,
                        help="Particles added per tick intake cycle.")
    parser.add_argument("--auto-pulse", action="store_true",
                        help="Enable automated field ramping (wave+gravity pulses).")

    # =============================
    # FIELD TUNING
    # =============================
    parser.add_argument("--gravity", type=float, default=1.0,
                        help="Initial gravity field strength.")
    parser.add_argument("--magnetism", type=float, default=1.0,
                        help="Initial magnetism field strength.")
    parser.add_argument("--wave-frequency", type=float, default=1.0,
                        help="Initial wave frequency.")

    # =============================
    # SQI AND STAGE TUNING
    # =============================
    parser.add_argument("--enable-sqi", action="store_true",
                        help="Enable SQI-driven stage adjustments.")
    parser.add_argument("--sqi-phase-aware", action="store_true",
                        help="Enable SQI phase-aware dynamic stage tuning.")
    parser.add_argument("--manual-stage", action="store_true",
                        help="Force manual stage control (disables SQI auto-adjust).")
    parser.add_argument("--auto-sqi-delay", type=int, default=50,
                        help="Delay (ticks) before auto-enabling SQI for safety.")

    # =============================
    # SAFETY & STABILITY
    # =============================
    parser.add_argument("--enable-engine-b", action="store_true",
                        help="Enable second engine for twin sync tests.")
    parser.add_argument("--safe-mode", action="store_true",
                        help="Enable Safe Mode (reduced particle count & capped fields).")
    parser.add_argument("--stability-guard", action="store_true",
                        help="Enable stability guard for resonance drift & SQI safeguards.")
    parser.add_argument("--thermal-safety", action="store_true",
                        help="Enable thermal throttling to prevent overheating.")

    # =============================
    # ADVANCED CONTROL
    # =============================
    parser.add_argument("--use-new-phase-sync", action="store_true",
                        help="Use updated Phase Sync module for twin-engine harmonics.")
    parser.add_argument("--persist-runtime", action="store_true",
                        help="Persist runtime tuning constants (harmonics/decay) between sessions.")
    parser.add_argument("--export-snapshots", action="store_true",
                        help="Auto-export .dc snapshots on stage transitions.")

    # =============================
    # DEBUGGING / EXPERIMENTAL
    # =============================
    parser.add_argument("--verbose-telemetry", action="store_true",
                        help="Enable detailed telemetry logs per tick.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run without state mutation (simulation mode only).")
    parser.add_argument("--glyph-trace", action="store_true",
                        help="Enable glyph trace during execution.")
    parser.add_argument("--collapse-interval", type=int, default=250,
                        help="Collapse interval for symbolic collapse sync.")

    return parser.parse_args()