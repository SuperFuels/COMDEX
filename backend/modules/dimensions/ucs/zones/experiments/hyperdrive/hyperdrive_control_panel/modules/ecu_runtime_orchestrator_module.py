import os, gzip, json, time
from datetime import datetime
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_qwave_tuning import HyperdriveTuning
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.harmonic_coherence_module import measure_harmonic_coherence

def ecu_runtime_orchestrator(engine_a, engine_b=None, args=None):
    """
    ECU Runtime Orchestrator for Hyperdrive Control Panel (wrapping engine runtime features).
    - Runs synchronized tick cycles for engines.
    - Injects harmonics and performs SQI phase-aware tuning.
    - Logs telemetry and warp readiness metrics.
    """
    ticks = args.ticks
    sqi_interval = args.sqi
    fuel_cycle = args.fuel
    sqi_phase_aware = args.sqi_phase_aware

    print(f"🚦 ECU Runtime Orchestrator Start: Target Ticks={ticks}")
    tick_counter = 0

    # Logging setup
    log_dir = "data/qwave_logs"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    main_log_file = os.path.join(log_dir, f"ecu_runtime_log_{timestamp}.jsonl.gz")
    latest_log_file = os.path.join(log_dir, "ecu_runtime_latest.jsonl")

    prev_fields = None

    with gzip.open(main_log_file, "wt", encoding="utf-8") as log_f, open(latest_log_file, "w") as latest_f:
        while tick_counter < ticks:
            # -------------------------
            # 🔄 Engine Tick Execution
            # -------------------------
            engine_a.tick()
            if engine_b:
                engine_b.tick()
            tick_counter += 1

            # Proton intake scaling
            for _ in range(getattr(engine_a, "intake_rate", 1)):
                engine_a.inject_proton()
            if engine_b:
                for _ in range(getattr(engine_b, "intake_rate", 1)):
                    engine_b.inject_proton()

            # -------------------------
            # 🎼 Harmonic Injection (SQI-locked only)
            # -------------------------
            if tick_counter % sqi_interval == 0 and getattr(engine_a, "sqi_locked", False):
                print(f"🎵 SQI Harmonic Injection @ Tick={tick_counter}")
                engine_a._inject_harmonics(HyperdriveTuning.HARMONIC_DEFAULTS)
                if engine_b and getattr(engine_b, "sqi_locked", False):
                    engine_b._inject_harmonics(HyperdriveTuning.HARMONIC_DEFAULTS)

            # -------------------------
            # 🔗 SQI Phase-Aware Sync
            # -------------------------
            if sqi_phase_aware and engine_b:
                drift_diff = abs(engine_a.resonance_phase - engine_b.resonance_phase)
                if drift_diff > 0.01:
                    adj = (engine_a.resonance_phase - engine_b.resonance_phase) * 0.5
                    engine_b.resonance_phase += adj
                    print(f"🔗 SQI Phase Sync: Engine B adjusted by {adj:.5f}")

            # -------------------------
            # 🧠 SQI Drift Auto-Lock (Analysis Hook)
            # -------------------------
            if hasattr(engine_a, "sqi_engine") and getattr(engine_a, "sqi_enabled", False):
                analysis = engine_a.sqi_engine.analyze_trace({
                    "resonance": engine_a.resonance_filtered[-30:],
                    "fields": engine_a.fields,
                    "exhaust": [e.get("impact_speed", 0) for e in engine_a.exhaust_log[-30:]],
                    "stage": engine_a.stages[engine_a.current_stage] if hasattr(engine_a, "stages") else None
                })
                drift = analysis.get("drift", 0.0)
                if drift <= getattr(engine_a, "stability_threshold", 0.05):
                    if hasattr(engine_a, "handle_sqi_lock"):
                        engine_a.handle_sqi_lock(drift)

            # -------------------------
            # 🛸 Warp Readiness Checks
            # -------------------------
            if tick_counter % 500 == 0:
                pi_val = sum(e.get("impact_speed", 0) for e in engine_a.exhaust_log[-500:])
                drift_var = max(engine_a.resonance_filtered[-100:], default=0) - min(engine_a.resonance_filtered[-100:], default=0)
                coherence = measure_harmonic_coherence(engine_a)
                sqi_state = "✅" if getattr(engine_a, "sqi_locked", False) else "❌"
                print(f"🔎 Warp Check → PI={pi_val:.0f} | Drift={drift_var:.4f} | Coherence={coherence:.2f} | SQI={sqi_state}")

            # -------------------------
            # 📡 Telemetry Logging
            # -------------------------
            if tick_counter % 500 == 0:
                telemetry = {
                    "tick": tick_counter,
                    "particles_a": len(engine_a.particles),
                    "resonance_a": engine_a.resonance_phase,
                    "sqi_locked": getattr(engine_a, "sqi_locked", False),
                    "stability": 1.0 - (drift_var * 10 if 'drift_var' in locals() else 0),
                    "timestamp": datetime.utcnow().isoformat()
                }
                json.dump(telemetry, log_f); log_f.write("\n"); log_f.flush()
                latest_f.seek(0); latest_f.truncate()
                json.dump(telemetry, latest_f); latest_f.write("\n"); latest_f.flush()

            # -------------------------
            # ⏱ Tick Interval Delay
            # -------------------------
            time.sleep(0.01)

    print(f"✅ ECU Runtime Orchestrator Complete. Logs stored in: {log_dir}")