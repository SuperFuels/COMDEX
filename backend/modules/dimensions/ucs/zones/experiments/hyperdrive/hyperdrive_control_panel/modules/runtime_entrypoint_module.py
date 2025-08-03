from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.idle_manager_module import ignition_to_idle
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_engine_sync import sync_twin_engines, exhaust_to_intake
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.gear_map_loader import GEAR_MAP
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.gear_shift_module import gear_shift
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants as HyperdriveTuning
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonics_module import measure_harmonic_coherence

def twin_sync_and_gearshift(engine_a, engine_b, sync_only=False):
    """
    Sync twin engines, stabilize harmonics, and optionally perform gear-shifting with exhaust chaining.
    """
    # 🔥 Cold-start check and ignition warm-up
    if not engine_a.resonance_filtered or not engine_b.resonance_filtered:
        print("🛠 Engines cold, performing ignition-to-idle warm-up...")
        ignition_to_idle(engine_a)
        ignition_to_idle(engine_b)

    print("🔗 Twin Engine Sync initiated...")
    sync_twin_engines(engine_a, engine_b)

    # 🎼 Harmonic resync and coherence check
    engine_a._resync_harmonics()
    engine_b._resync_harmonics()
    print(f"🎼 Harmonic Coherence A: {measure_harmonic_coherence(engine_a):.3f}")
    print(f"🎼 Harmonic Coherence B: {measure_harmonic_coherence(engine_b):.3f}")

    if not sync_only:
        for g in [1, 2]:
            gear_shift(engine_a, g, HyperdriveTuning.STAGE_CONFIGS)
            gear_shift(engine_b, g, HyperdriveTuning.STAGE_CONFIGS)
            exhaust_to_intake(engine_a, engine_b)
        print("🚀 Twin sync & exhaust chaining complete.")