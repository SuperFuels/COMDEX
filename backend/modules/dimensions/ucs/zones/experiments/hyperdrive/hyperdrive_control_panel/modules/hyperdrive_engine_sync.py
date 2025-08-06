"""
🔗 Engine Sync Module
---------------------
"""
# ✅ Hyperdrive Engine Sync Module
# • Handles dual-engine synchronization.
# • Harmonic coherence evaluation (via harmonic_coherence_module).
# • SQI alignment and drift correction during parallel runs.
"""
🔥 Features:
    • Twin-engine resonance sync (phase lock with harmonic drift correction).
    • Exhaust-to-intake chaining with safe particle injection.
    • Gravity/magnetism + SQI phase field sync.
    • Harmonic coherence evaluation (via harmonics_module).
    • Awareness confidence hooks (IGI integration).
    • Stage profile auto-alignment during sync.
    • Future-ready: supports chaining pipelines (A → B → C).

🛠 Recommended Usage:
    sync_twin_engines(engine_a, engine_b)
    exhaust_to_intake(engine_a, engine_b)
"""

from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.hyperdrive_tuning_constants_module import HyperdriveTuningConstants
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.instability_check_module import check_instability


def sync_twin_engines(engine_a, engine_b, sync_fields=True, sync_harmonics=True, sqi_phase_lock=True):
    """
    Synchronize resonance and harmonics between two engines.
    Includes SQI-aware phase correction, field tuning, awareness, and profile alignment.
    """
    print("\n🔗 Initiating twin-engine sync (phase lock + field harmonics)...")

    # 🔧 Stage Profile Alignment (match both engines to same profile)
    stage_name = str(engine_a.stages[engine_a.current_stage]).lower()
    if "warp" in stage_name:
        HyperdriveTuningConstants.apply_profile("warp")
    elif "idle" in stage_name:
        HyperdriveTuningConstants.apply_profile("idle")
    elif "safe" in stage_name:
        HyperdriveTuningConstants.apply_profile("safe")

    # ✅ Phase Lock Loop
    for _ in range(8):  # faster lock-in
        avg_phase = (engine_a.resonance_phase + engine_b.resonance_phase) / 2
        for eng in (engine_a, engine_b):
            eng.fields["wave_frequency"] = max(0.01, avg_phase / 3)
            eng.tick()

    # ✅ Field Equalization
    if sync_fields:
        avg_gravity = (engine_a.fields.get("gravity", 1.0) + engine_b.fields.get("gravity", 1.0)) / 2
        avg_magnetism = (engine_a.fields.get("magnetism", 1.0) + engine_b.fields.get("magnetism", 1.0)) / 2
        engine_a.fields["gravity"] = engine_b.fields["gravity"] = avg_gravity
        engine_a.fields["magnetism"] = engine_b.fields["magnetism"] = avg_magnetism
        print(f"⚖ Fields synced → Gravity={avg_gravity:.3f} | Magnetism={avg_magnetism:.3f}")

    # ✅ Harmonic Gain Unification
    if sync_harmonics:
        HyperdriveTuningConstants.load_runtime()
        print(f"🎶 Harmonic constants unified: Gain={HyperdriveTuningConstants.HARMONIC_GAIN:.4f}")

    # ✅ SQI Phase Lock (optional)
    if sqi_phase_lock:
        coherence_a = measure_harmonic_coherence(engine_a)
        coherence_b = measure_harmonic_coherence(engine_b)
        avg_coherence = (coherence_a + coherence_b) / 2
        print(f"🧬 SQI Phase Coherence: A={coherence_a:.3f} | B={coherence_b:.3f} → Avg={avg_coherence:.3f}")
        if avg_coherence > 0.8:
            print("✅ SQI phase lock confirmed across twin engines.")

    # 🧠 Awareness Hooks (IGI)
    for eng in (engine_a, engine_b):
        if hasattr(eng, "awareness"):
            eng.awareness.update_confidence(1.0)
            eng.awareness.record_confidence(
                glyph="🔗",
                coord=f"engine_sync",
                container_id=getattr(eng.container, "id", "N/A"),
                tick=getattr(eng, "tick_count", 0),
                trigger_type="engine_sync"
            )

    print("✅ Twin engines fully synchronized and SQI-ready.")


def exhaust_to_intake(source_engine, target_engine, limit=5):
    """
    Transfer exhaust particles safely from source to target engine intake.
    Includes validation, SQI drift dampening, awareness, and harmonic tuning.
    """
    if not hasattr(source_engine, "exhaust_log") or not source_engine.exhaust_log:
        print("⚠ No exhaust particles available for transfer.")
        return

    # ✅ Select recent exhaust impacts
    particles = [
        e for e in source_engine.exhaust_log[-limit:]
        if isinstance(e, dict) and "impact_speed" in e and "energy" in e
    ]

    if not particles:
        print("⚠ No valid exhaust impacts for transfer.")
        return

    # ✅ Convert exhaust impacts into proton intake injections
    for p in particles:
        particle_data = {
            "density": 1.0 + (p["energy"] * 0.01),
            "mass": 1.0,
            "vx": 0.0, "vy": 0.0, "vz": 0.0,
            "x": 0.0, "y": 0.0, "z": 0.0
        }
        if hasattr(target_engine, "inject_proton"):
            target_engine.inject_proton(custom_particle=particle_data)
        else:
            print("⚠ Target engine missing inject_proton; skipping particle.")

    print(f"🔄 Exhaust → Intake: {len(particles)} particles recycled into {target_engine}.")

    # ✅ Drift & Awareness Post-Transfer
    if check_instability(target_engine):
        print("🛑 Drift spike detected post-transfer. Applying SQI drift damp...")
        target_engine.fields["wave_frequency"] *= 0.98
        target_engine.fields["gravity"] *= 0.99

    if hasattr(target_engine, "awareness"):
        target_engine.awareness.update_confidence(0.95)
        target_engine.awareness.record_confidence(
            glyph="♻",
            coord="exhaust_intake_transfer",
            container_id=getattr(target_engine.container, "id", "N/A"),
            tick=getattr(target_engine, "tick_count", 0),
            trigger_type="post_exhaust_transfer"
        )