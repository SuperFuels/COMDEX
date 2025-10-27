#!/usr/bin/env python3
"""
🧠 AION Reinforcement Bridge — Phase 46C
────────────────────────────────────────
Unifies semantic, resonant, and harmonic reinforcement.
Ensures every learned association is stored coherently across
LexMemory, ResonantMemoryCache, and HarmonicMemoryProfile.

Functions:
    • reinforce_all() – coherent multi-layer reinforcement
    • schedule_replay() – recall & reinforce selected lemmas
    • decay_and_adapt() – adaptive decay + replay scheduling
    • report_metrics() – emit real-time learning statistics
"""

import time, random, logging
from statistics import mean
from pathlib import Path

from backend.modules.aion_cognition.cee_lex_memory import (
    update_lex_memory,
    recall_from_memory,
    reinforce_field,
    decay_memory,
)
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_language.conversation_memory import MEM

# ────────────────────────────────────────────────────────────────
# Optional Harmonic layer
try:
    from backend.modules.aion_language.harmonic_memory_profile import HarmonicMemoryProfile
    HMP = HarmonicMemoryProfile()
except Exception as e:
    print(f"[Bridge] ⚠ Failed to load HMP: {e}")
    HMP = None

# Logging setup
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Global singletons
RMC = ResonantMemoryCache()

STATE = {
    "replays": 0,
    "reinforced": 0,
    "avg_recall": [],
    "resonance_growth": [],
}

# ────────────────────────────────────────────────────────────────
def reinforce_all(prompt: str, answer: str, resonance: dict):
    """Reinforce all memory layers coherently."""
    try:
        update_lex_memory(prompt, answer, resonance)
    except Exception as e:
        log.warning(f"[Bridge] ⚠ LexMemory update failed: {e}")

    try:
        # Build photon from resonance parameters
        photon = {"λ": prompt, "φ": resonance.get("ρ", 0.0), "μ": resonance.get("SQI", 0.0)}

        # Ensure RMC cache entry is a dict, not a float/int
        if hasattr(RMC, "cache"):
            cid = photon["λ"]
            entry = RMC.cache.get(cid, {})
            if not isinstance(entry, dict):
                entry = {"count": 0, "avg_phase": 0.0, "avg_goal": 0.0, "coherence": 0.0, "last_seen": 0.0}

            entry["count"] = entry.get("count", 0) + 1
            entry["avg_phase"] = round(
                (entry.get("avg_phase", 0.0) * (entry["count"] - 1) + photon["φ"]) / entry["count"], 3
            )
            entry["avg_goal"] = round(
                (entry.get("avg_goal", 0.0) * (entry["count"] - 1) + photon["μ"]) / entry["count"], 3
            )
            entry["coherence"] = round(mean([entry["avg_phase"], 1 - abs(0.5 - entry["avg_goal"])]), 3)
            entry["last_seen"] = time.time()
            RMC.cache[cid] = entry
            RMC.save()
            log.info(f"[Bridge] 🔄 Reinforced RMC entry for '{cid}'")

        elif hasattr(RMC, "update_resonance_link"):
            RMC.update_resonance_link(prompt, answer, resonance.get("SQI", 0.0))

    except Exception as e:
        log.warning(f"[Bridge] ⚠ RMC update failed (safe mode): {e}")

    if HMP:
        try:
            HMP.log_event({
                "target": prompt,
                "gain": resonance.get("ρ", 0.0),
                "drift_mag": abs(resonance.get("I", 0.0) - resonance.get("ρ", 0.0)),
                "time": time.time(),
            })
        except Exception as e:
            log.warning(f"[Bridge] ⚠ HMP log failed: {e}")

    log.info(f"[Bridge] ✅ Reinforced '{prompt}' → {answer} ({resonance})")


# ────────────────────────────────────────────────────────────────
def schedule_replay(batch_size: int = 10):
    """Recall random lemmas and reinforce them."""
    if not hasattr(RMC, "cache"):
        log.warning("[Reinforcement] RMC cache unavailable.")
        return

    keys = [k for k in RMC.cache.keys() if isinstance(k, str) and not k.startswith("links")]
    if not keys:
        log.warning("[Reinforcement] No lexemes found in RMC cache.")
        return

    chosen = random.sample(keys, min(batch_size, len(keys)))
    log.info(f"[Reinforcement] 🔁 Replaying {len(chosen)} lemmas.")

    for lemma in chosen:
        rec = recall_from_memory(lemma)
        sqi = random.uniform(0.6, 0.95)
        resonance = {"ρ": random.uniform(0.5, 0.9), "I": random.uniform(0.7, 1.0), "SQI": sqi}
        reinforce_all(lemma, rec.get("definition", ""), resonance)
        MEM.remember(lemma, rec.get("definition", ""), semantic_field="reinforcement")

        STATE["replays"] += 1
        STATE["reinforced"] += 1
        STATE["avg_recall"].append(sqi)
        STATE["resonance_growth"].append(resonance["ρ"])


# ────────────────────────────────────────────────────────────────
def decay_and_adapt(half_life_hours: float = 24.0):
    """Apply adaptive decay and adjust replay frequency."""
    decay_memory(half_life_hours)
    avg_growth = mean(STATE["resonance_growth"]) if STATE["resonance_growth"] else 0
    replay_delay = max(5, int(30 * (1.0 - avg_growth)))
    log.info(f"[Reinforcement] ⚖ Adaptive decay applied (half_life={half_life_hours}h)")
    log.info(f"[Reinforcement] Next replay window in ≈ {replay_delay}s (growth={avg_growth:.3f})")
    time.sleep(replay_delay)


# ────────────────────────────────────────────────────────────────
def report_metrics() -> dict:
    """Compute and log current reinforcement performance."""
    metrics = {
        "total_replays": STATE["replays"],
        "total_reinforced": STATE["reinforced"],
        "avg_recall": round(mean(STATE["avg_recall"]), 3) if STATE["avg_recall"] else 0,
        "resonance_growth": round(mean(STATE["resonance_growth"]), 3) if STATE["resonance_growth"] else 0,
        "timestamp": time.strftime("%H:%M:%S"),
    }
    log.info(f"[Metrics] {metrics}")
    return metrics


# ────────────────────────────────────────────────────────────────
def run_reinforcement_cycle(iterations: int = 3, batch_size: int = 10):
    """Main control loop for replay–decay–metrics cycles."""
    for i in range(iterations):
        log.info(f"\n🌀 Reinforcement Cycle {i+1}/{iterations}")
        schedule_replay(batch_size=batch_size)
        decay_and_adapt()
        report_metrics()
    log.info("✅ Reinforcement cycles completed.")


# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("🔗 AION Reinforcement Bridge — Phase 46C (Unified Semantic–Resonant–Harmonic)")
    run_reinforcement_cycle(iterations=2, batch_size=8)