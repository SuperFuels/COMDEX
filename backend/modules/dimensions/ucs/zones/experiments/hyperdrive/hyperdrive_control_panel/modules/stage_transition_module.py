from datetime import datetime
from copy import deepcopy
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.dc_io import DCContainerIO
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonics_module import measure_harmonic_coherence
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.logger import TelemetryLogger
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.tesseract_injector import proton_inject_cycle

def transition_stage(engine, new_stage: str, reseed_particles: bool = True):
    """
    Handles stage transition logic, including:
    • Engine reconfiguration
    • Harmonic resync & coherence validation
    • SQI drift reset
    • Optional particle reseeding
    • .dc snapshot auto-export
    • Telemetry log binding
    """
    if new_stage not in engine.stages:
        raise ValueError(f"❌ Invalid stage: {new_stage}")

    # ✅ Switch stage
    engine.current_stage = engine.stages.index(new_stage)
    if hasattr(engine, "_configure_stage"):
        engine._configure_stage()

    # 🎼 Harmonic resync and coherence check
    engine._resync_harmonics()
    coherence = measure_harmonic_coherence(engine)
    engine.last_harmonic_coherence = coherence
    print(f"🎼 Harmonic coherence after transition: {coherence:.3f}")

    # 🔄 Reset SQI drift metrics
    engine.resonance_filtered.clear()
    engine.pending_sqi_ticks = 20
    engine.sqi_locked = False

    # 🌱 Optional particle reseeding on stage switch
    if reseed_particles and hasattr(engine, "injectors"):
        print("🌱 Reseeding particles for new stage...")
        for _ in range(50):  # seed 50 baseline particles
            if hasattr(engine.injectors[0], "multi_compress_and_fire"):
                engine.injectors[0].multi_compress_and_fire(engine)
            else:
                proton_inject_cycle(engine)

    # 📦 Auto-export .dc snapshot for stage
    engine.last_dc_trace = f"data/qwave_logs/{new_stage}_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dc.json"
    DCContainerIO.export({
        "fields": deepcopy(engine.fields),
        "particles": len(engine.particles),
        "coherence": coherence,
        "timestamp": datetime.utcnow().isoformat(),
        "tick_count": engine.tick_count,
    }, engine.last_dc_trace, stage=new_stage, sqi_enabled=engine.sqi_enabled)

    print(f"📦 Auto-exported .dc snapshot for stage '{new_stage}' → {engine.last_dc_trace}")

    # 🖥 Telemetry snapshot logging
    TelemetryLogger(log_dir=engine.LOG_DIR).log({
        "timestamp": datetime.utcnow().isoformat(),
        "stage": new_stage,
        "tick": engine.tick_count,
        "fields": deepcopy(engine.fields),
        "harmonic_coherence": coherence,
        "sqi_enabled": engine.sqi_enabled
    })

    # ✅ Container expansion post-transition
    if hasattr(engine, "container") and engine.container:
        engine.container.expand(avatar_state=engine.safe_mode_avatar if engine.safe_mode else None)
        print("🧩 Container expansion triggered post-transition.")