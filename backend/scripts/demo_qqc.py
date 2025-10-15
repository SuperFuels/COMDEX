#!/usr/bin/env python3
# ================================================================
#  Tessaris • Quantum Quad Core (QQC)
#  Symatics Lightwave Engine (SLE) Demonstration Harness v0.5
# ================================================================
import os, json, time, uuid
from datetime import datetime
from backend.codexcore_virtual.virtual_wave_engine import VirtualWaveEngine
from backend.modules.codex.beam_event_bus import beam_event_bus, BeamEvent
from backend.modules.glyphwave.core.wave_state import WaveState

from backend.config.feature_flags import is_qqc_enabled, is_lightwave_enabled, print_feature_status

print_feature_status()

if not (is_qqc_enabled() and is_lightwave_enabled()):
    print("⚠️  QQC or Lightwave Engine is disabled via feature flags. Exiting.")
    exit(0)

RUN_ID = f"SLE_RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"\n🌊 Tessaris Quantum Quad Core — Symatics Lightwave Engine (SLE) v0.5")
print(f"Run ID: {RUN_ID}")
print(f"Timestamp: {datetime.now().isoformat()}")
print("========================================================\n")

# --------------------------------------------------------
# Initialize virtual execution engine
# --------------------------------------------------------
engine = VirtualWaveEngine()
print("⚙️  VirtualWaveEngine initialized.\n")

# --------------------------------------------------------
# Create and configure actual wave objects
# --------------------------------------------------------
wA = WaveState()
wA.phase = 0.0
wA.amplitude = 1.0
wA.coherence = 1.0
wA.metadata["wave_id"] = "wave_A"

wB = WaveState()
wB.phase = 1.57
wB.amplitude = 0.85
wB.coherence = 0.94
wB.metadata["wave_id"] = "wave_B"

# Attach to engine
engine.attach_wave(wA)
engine.attach_wave(wB)
print("✅ WaveStates attached to VirtualWaveEngine.\n")

# --------------------------------------------------------
# Load a simple symbolic program (5 operations for demo)
# --------------------------------------------------------
symbolic_program = [
    {"opcode": "STORE", "args": ["R1", "Dream"]},
    {"opcode": "ADD", "args": ["R1", "R2", "R3"]},
    {"opcode": "ENTANGLE", "args": ["R2", "R3"]},
    {"opcode": "RESONATE", "args": ["R3"]},
    {"opcode": "COLLAPSE", "args": ["R3"]}
]

engine.cpu.program = symbolic_program
engine.cpu.instruction_pointer = 0
print(f"🧠 Loaded symbolic program with {len(symbolic_program)} ops.\n")
# --------------------------------------------------------
# Telemetry setup
# --------------------------------------------------------
telemetry_log = []
VALIDATION_FILE = "sle_validation.json"
LOG_FILE = "sle_run_log.txt"

COHERENCE_THRESHOLD = 0.75  # SoulLaw veto threshold

def emit_event(event_type, **meta):
    event = BeamEvent(
        event_type,
        source="QQC_SLE",
        target="BeamController",
        drift=meta.get("phase_drift", 0.0),
        qscore=meta.get("sqi", 1.0),
        metadata=meta
    )
    beam_event_bus.publish(event)

print("🔧 Engine initialized. Beginning quantum tick loop...\n")

# --------------------------------------------------------
# Main demo loop — 5 ticks
# --------------------------------------------------------
for tick in range(1, 6):
    t0 = time.perf_counter()
    coherence = round(0.9 - tick * 0.02, 3)  # simulated decay
    entropy = round(0.01 * tick, 4)
    phase_drift = round(0.02 * tick, 4)
    vetoed = coherence < COHERENCE_THRESHOLD

    emit_event("tick", tick=tick, coherence=coherence, entropy=entropy,
               phase_drift=phase_drift, sqi=coherence + 0.05)

    if vetoed:
        print(f"[SoulLaw VETO] Tick {tick} skipped — coherence {coherence:.2f}")
        collapse_time_ms = None
    else:
        t1 = time.perf_counter()
        engine.cpu.tick()  # Execute symbolic–photonic step
        collapse_time_ms = round((time.perf_counter() - t1) * 1000, 3)
        emit_event("collapse", tick=tick, coherence=coherence,
                   entropy=entropy, collapse_time_ms=collapse_time_ms)
        print(f"[Tick {tick}] Collapse completed in {collapse_time_ms} ms  |  C={coherence:.2f}")

    telemetry_entry = {
        "tick": tick,
        "coherence": coherence,
        "entropy": entropy,
        "phase_drift": phase_drift,
        "collapse_time_ms": collapse_time_ms,
        "vetoed": vetoed,
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

print("\n✅ Run complete. Telemetry exported to sle_validation.json.")
print("📄 Full log saved to sle_run_log.txt — include as Appendix A in SLE v0.5 document.")
print("========================================================")