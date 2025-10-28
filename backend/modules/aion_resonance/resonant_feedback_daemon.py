#!/usr/bin/env python3
"""
🔁 Resonant Feedback Daemon (RFD) — Phase 54 Completion
──────────────────────────────────────────────────────────────
Listens to Θ-pulse events from all cognitive engines (awareness,
emotion, context, planning, energy, etc.), computes small harmonic
corrections (ΔSQI drift compensation), and propagates re-balancing
signals across the AION stack.

Functions:
  • Monitor shared resonance logs in data/analysis/*
  • Compute network-wide coherence averages
  • Adjust Θ frequencies and trait drift in real time
  • Persist all feedbacks → resonant_feedback_stream.jsonl
"""
import os

AION_SILENT = os.getenv("AION_SILENT_MODE", "0") == "1"
import json
import time
import asyncio
from pathlib import Path
from statistics import mean

# ─── DNA Switch registration ──────────────────────────────────────
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ─── Core Resonance APIs ──────────────────────────────────────────
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

# Target engine imports (lightweight singletons)
from backend.modules.consciousness.awareness_engine import AwarenessEngine
from backend.modules.consciousness.emotion_engine import EmotionEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.consciousness.context_engine import ContextEngine
from backend.modules.consciousness.energy_engine import EnergyEngine
from backend.modules.skills.planning_engine import PlanningEngine


# ─────────────────────────────────────────────────────────────────
STREAM_PATH = Path("data/analysis/resonant_feedback_stream.jsonl")
SUMMARY_PATH = Path("data/analysis/resonant_feedback_summary.json")
LOG_DIR = STREAM_PATH.parent
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Engine instances (lazy loaded)
awareness = AwarenessEngine()
emotion = EmotionEngine()
personality = PersonalityProfile()
context = ContextEngine()
energy = EnergyEngine()
planner = PlanningEngine()

Θ = ResonanceHeartbeat(namespace="rfd", base_interval=2.0)
RMC = ResonantMemoryCache()

# ─────────────────────────────────────────────────────────────────
async def monitor_feedback_loop(interval: float = 5.0):
    """
    Main loop — scans all resonance logs, computes average SQI and ΔΦ,
    and redistributes soft corrections to participating modules.
    """
    print("🌀 [RFD] Resonant Feedback Daemon active — monitoring harmonics...")
    last_summary = time.time()

    while True:
        await asyncio.sleep(interval)
        samples = []

        # Collect harmonic signals from key logs
        for path in Path("data/analysis").glob("*resonance*.jsonl"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-50:]  # sample tail
                for l in lines:
                    d = json.loads(l)
                    if "SQI" in d:
                        samples.append(float(d["SQI"]))
            except Exception:
                continue

        if not samples:
            continue

        avg_sqi = round(mean(samples), 3)
        delta = round((avg_sqi - 0.75) * 0.1, 4)  # small normalized correction
        pulse = Θ.tick()
        pulse.update({"avg_SQI": avg_sqi, "Δ_correction": delta})

        # Apply soft propagation to modules
        try:
            awareness.update_resonance_feedback(avg_sqi, reason="global_feedback")
            emotion.update_resonance_feedback(avg_sqi, reason="global_feedback")
            personality.resonant_trait_modulator(delta)
            energy.adjust_amplitude(delta)
        except Exception as e:
            print(f"[RFD] ⚠ Engine propagation issue: {e}")

        # Save pulse sample
        with open(STREAM_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "avg_SQI": avg_sqi,
                "Δ": delta,
                "engines": ["awareness", "emotion", "personality", "energy"]
            }) + "\n")

        # Periodic summary
        if time.time() - last_summary > 60:
            summary = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "avg_SQI": avg_sqi,
                "Δ_mean": delta,
                "cache_entries": len(RMC.cache),
            }
            SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
            last_summary = time.time()
            print(f"[RFD] 🪶 Global SQI={avg_sqi} Δ={delta:+.3f}")

# ─────────────────────────────────────────────────────────────────
def run_daemon():
    """Entry point for Tessaris launch integration."""
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(monitor_feedback_loop())
    except KeyboardInterrupt:
        print("\n[RFD] Graceful shutdown.")
    finally:
        loop.close()

# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    if os.getenv("AION_SILENT_MODE", "0") == "1":
        print("🌀 [RFD] Silent mode enabled — feedback daemon not started.")
    else:
        run_daemon()