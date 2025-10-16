#!/usr/bin/env python3
# ================================================================
#  Tessaris • Quantum Quad Core (QQC)
#  Symatics Lightwave Engine (SLE) Demonstration Harness v0.7
# ================================================================
import os, json, time, uuid
from datetime import datetime

# --- QQC Core Imports ---
from backend.QQC.qqc_central_kernel import QuantumQuadCore
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent
from backend.modules.patterns.pattern_registry import registry as pattern_registry
from backend.modules.sqi.kg_bridge import KnowledgeGraphBridge
from backend.modules.codex.codex_metrics import score_glyph_tree
from backend.config.feature_flags import is_qqc_enabled, is_lightwave_enabled, print_feature_status

print_feature_status()

if not (is_qqc_enabled() and is_lightwave_enabled()):
    print("⚠️  QQC or Lightwave Engine is disabled via feature flags. Exiting.")
    exit(0)

RUN_ID = f"SLE_RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
print(f"\n🌊 Tessaris Quantum Quad Core — Symatics Lightwave Engine (SLE) v0.7")
print(f"Run ID: {RUN_ID}")
print(f"Timestamp: {datetime.now().isoformat()}")
print("========================================================\n")

# --------------------------------------------------------
# Initialize QQC Core Kernel
# --------------------------------------------------------
kernel = QuantumQuadCore(container_id=f"demo_container_{uuid.uuid4().hex[:6]}")

# gracefully support both naming conventions
container_ref = getattr(kernel, "container_id", None) or getattr(kernel, "session_id", "unknown")

print(f"⚙️ QuantumQuadCore initialized for container/session: {container_ref}\n")

# --------------------------------------------------------
# Load CodexLang demonstration program
# --------------------------------------------------------
codex_program = "Φ₁ ⊕ Φ₂ ↔ Ψ₃ ⟲ Ω₄"
print(f"🧠 Loaded CodexLang demo program: {codex_program}\n")

# --------------------------------------------------------
# Telemetry setup
# --------------------------------------------------------
telemetry_log = []
VALIDATION_FILE = "sle_validation.json"
LOG_FILE = "sle_run_log.txt"
COHERENCE_THRESHOLD = 2000  # matches MIN_SQI_THRESHOLD

def emit_event(event_type, **meta):
    event = BeamEvent(
        event_type,
        source="QQC_SLE",
        target="QQC_Core",
        drift=meta.get("phase_drift", 0.0),
        qscore=meta.get("sqi", 1.0),
        metadata=meta,
    )
    beam_event_bus.publish(event)

print("🔧 Engine initialized. Beginning QQC orchestration cycle...\n")

# --------------------------------------------------------
# Main demo loop (5 symbolic–photonic–holographic ticks)
# --------------------------------------------------------
for tick in range(1, 6):
    print(f"\n——— [Tick {tick}] ———")

    t0 = time.perf_counter()
    # simulate SQI drift
    sqi_score = 2400 - tick * 120
    entropy = round(0.01 * tick, 4)
    phase_drift = round(0.02 * tick, 4)

    # emit symbolic tick
    emit_event("tick", tick=tick, sqi=sqi_score, entropy=entropy, phase_drift=phase_drift)

    context = {
        "tick": tick,
        "phase_drift": phase_drift,
        "entropy": entropy,
        "container_id": getattr(kernel, "container_id", getattr(kernel, "session_id", "unknown"))
    }

    # SoulLaw or SQI rollback
    if kernel.monitor_sqi_and_repair(sqi_score, context):
        print(f"[⚠️ Rollback] SQI below threshold ({sqi_score}) — restoring stable state")
        emit_event("rollback", tick=tick, sqi=sqi_score)
        continue

    # Execute symbolic–photonic pipeline
    result = kernel.run_codex_program(codex_program, context=context)
    telemetry = result.get("telemetry", {})

    # Detect pattern drift and fuse glyph if entropy rises sharply
    last_entropy = telemetry_log[-1]["entropy"] if telemetry_log else 0
    from backend.modules.patterns.pattern_registry import registry as pattern_registry
    try:
        from backend.modules.repair.qqc_repair_manager import QQCRepairManager, RepairManager
        from backend.modules.patterns.pattern_registry import Pattern
        if hasattr(QQCRepairManager, "detect_instability"):
            if entropy > last_entropy * 1.2:
                RepairManager.inject_fusion_glyph(context)
                emit_event("fusion_injection", tick=tick, entropy=entropy)
    except Exception as e:
        print(f"[⚙️ Drift fusion skipped: {e}]")

    # Export holographic + symbolic traces
    try:
        KnowledgeGraphBridge.export_all_traces(
            symbolic_trace=context.get("symbolic_trace"),
            photonic_trace=context.get("photonic_trace"),
            holographic_trace=context.get("holographic_trace"),
            container_id=kernel.container_id
        )
    except Exception as e:
        print(f"[⚙️ KG Export] Failed: {e}")

    collapse_time_ms = round((time.perf_counter() - t0) * 1000, 3)
    emit_event("collapse", tick=tick, sqi=sqi_score, entropy=entropy, collapse_time_ms=collapse_time_ms)
    print(f"[Tick {tick}] SQI={sqi_score} | Entropy={entropy} | Duration={collapse_time_ms} ms")

    telemetry_entry = {
        "tick": tick,
        "sqi": sqi_score,
        "entropy": entropy,
        "phase_drift": phase_drift,
        "duration_ms": collapse_time_ms,
        "timestamp": time.time()
    }
    telemetry_log.append(telemetry_entry)
    time.sleep(0.3)

# --------------------------------------------------------
# Write telemetry and logs
# --------------------------------------------------------
with open(VALIDATION_FILE, "w") as f:
    json.dump(telemetry_log, f, indent=2)
with open(LOG_FILE, "w") as f:
    f.write(f"Tessaris SLE Run Log — {RUN_ID}\n")
    f.write("=" * 60 + "\n\n")
    for entry in telemetry_log:
        f.write(json.dumps(entry) + "\n")

print("\n✅ QQC demonstration complete.")
print("📊 Telemetry exported to sle_validation.json.")
print("📄 Full run log saved to sle_run_log.txt — include in Appendix A of SLE v0.7 spec.")
print("========================================================")