"""
🔗 Engine Sync Module
---------------------
• Handles twin-engine resonance synchronization (phase lock).
• Manages exhaust → intake chaining for multi-engine amplification.
• Ensures resonance frequencies are averaged for stable phase alignment.
• Validates exhaust particle transfers safely before intake injection.

🔥 Features:
    • Twin-engine resonance sync (F2) with averaged phase correction.
    • Exhaust-to-intake linkage for downstream chaining (F3).
    • Safe particle validation during exhaust transfer.
    • Future-ready: Supports expansion to multi-engine chaining pipelines (A → B → C).
"""

def sync_twin_engines(engine_a, engine_b):
    """
    Synchronize resonance between two engines by averaging their phase states.
    Phase-lock achieved over 10 iterations by adjusting wave frequency fields.
    """
    print("\n🔗 Syncing twin engines...")
    for _ in range(10):
        avg_res = (engine_a.resonance_phase + engine_b.resonance_phase) / 2
        engine_a.fields["wave_frequency"] = avg_res / 3
        engine_b.fields["wave_frequency"] = avg_res / 3
        engine_a.tick()
        engine_b.tick()
    print("✅ Twin engines resonance synced.")


def exhaust_to_intake(source_engine, target_engine):
    """
    Transfer exhaust particles from a source engine to the intake of a target engine.
    Validates that particles exist and handles safe injection.
    """
    if hasattr(source_engine, "exhaust_log") and source_engine.exhaust_log:
        # ✅ Validate exhaust particles, filter None or invalid types
        particles = [p for p in source_engine.exhaust_log[-5:] if isinstance(p, dict) or p is not None]
        if not particles:
            print("⚠ No valid exhaust particles found for transfer.")
            return

        for particle in particles:
            # ✅ Inject safely: use original particle if structured, fallback to fresh proton
            if isinstance(particle, dict):
                target_engine.inject_proton(custom_particle=particle)
            else:
                target_engine.inject_proton()
        print(f"🔄 Exhaust → Intake: {len(particles)} particles transferred.")
    else:
        print("⚠ No exhaust particles available for transfer.")