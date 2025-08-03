# backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_control_panel/modules/engine_factory_module.py

from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_engine import HyperdriveEngine
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.tesseract_injector import TesseractInjector, CompressionChamber
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_controller_module import SQIController
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.idle_manager_module import save_idle_state, load_idle_state

def create_engine(name, args):
    """
    🏭 Engine Factory Module
    ------------------------
    Creates and configures a HyperdriveEngine instance:
    • Initializes container, injectors, and compression chambers.
    • Applies CLI/config overrides (gravity, magnetism, harmonics, SQI state).
    • Syncs harmonic constants into HyperdriveTuningConstants.
    • ✅ Auto-attaches SQI Controller with feedback engagement if enabled.
    • ✅ Auto-saves idle snapshot if engine stabilizes during initialization.
    """

    print(f"\n⚙️ [ENGINE FACTORY] Creating engine '{name}'...")

    # =============================
    # Core Engine Initialization
    # =============================
    container = SymbolicExpansionContainer(container_id=name)
    engine = HyperdriveEngine(
        container=container,
        safe_mode=args.safe_mode,
        stage_lock=getattr(args, "stage_lock", 4),
        virtual_absorber=True,
        sqi_enabled=getattr(args, "enable_sqi", False)
    )

    # =============================
    # Injector & Chamber Setup
    # =============================
    injector_count = getattr(args, "injectors", 4)
    engine.injectors = [TesseractInjector(i, phase_offset=i * 2) for i in range(injector_count)]
    engine.chambers = [CompressionChamber(i, compression_factor=1.3) for i in range(4)]
    engine.injector_interval = getattr(args, "injector_interval", 5)

    # =============================
    # Field Configuration
    # =============================
    engine.fields.update({
        "gravity": getattr(args, "gravity", engine.fields["gravity"]),
        "magnetism": getattr(args, "magnetism", engine.fields["magnetism"]),
        "wave_frequency": getattr(args, "wave_frequency", engine.fields["wave_frequency"]),
    })
    engine.intake_rate = getattr(args, "intake_rate", 1.0)

    # =============================
    # SQI Integration
    # =============================
    engine.sqi_enabled = bool(getattr(args, "enable_sqi", False))
    engine.sqi_locked = engine.sqi_enabled
    print(f"{'🧬 SQI ENABLED & LOCKED' if engine.sqi_enabled else '❌ SQI DISABLED'} for {name}")

    # Attach SQI Controller
    engine.sqi_controller = SQIController(engine)
    if engine.sqi_enabled:
        engine.sqi_controller.engage_feedback()
        print(f"🧠 SQI Controller engaged for {name}")

    # =============================
    # Harmonic Overrides
    # =============================
    if getattr(args, "harmonics", None):
        harmonics = [
            int(h) if str(h).isdigit() else float(h)
            for h in getattr(args, "harmonics")
        ]
        HyperdriveTuningConstants.HARMONIC_DEFAULTS = harmonics
        print(f"🎼 Harmonics set for {name}: {HyperdriveTuningConstants.HARMONIC_DEFAULTS}")

    # Gain/Decay Overrides
    if hasattr(args, "harmonic_gain"):
        HyperdriveTuningConstants.HARMONIC_GAIN = args.harmonic_gain
        print(f"🎛 Harmonic Gain overridden: {args.harmonic_gain}")
    if hasattr(args, "harmonic_decay"):
        HyperdriveTuningConstants.DECAY_RATE = args.harmonic_decay
        print(f"🎛 Harmonic Decay overridden: {args.harmonic_decay}")

    # =============================
    # Initial Harmonic Injection
    # =============================
    if hasattr(engine, "_inject_harmonics"):
        engine._inject_harmonics(HyperdriveTuningConstants.HARMONIC_DEFAULTS)
        print(f"🎵 Initial harmonic injection complete for {name}")

    # =============================
    # Idle Snapshot Handling
    # =============================
    try:
        save_idle_state(engine, label=f"{name}_init_idle")
        print(f"💾 Idle snapshot auto-saved for {name}")
    except Exception as e:
        print(f"⚠ Idle snapshot failed: {e}")

    print(f"✅ Engine '{name}' fully initialized and ready.")
    return engine